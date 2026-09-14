import json
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.core.cache import cache
from django.db import IntegrityError
from django.test import TestCase, override_settings

from estoque.models import Ingrediente
from estoque.services.fechamentos import criar_rascunho


class SegurancaApiTests(TestCase):
    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    @patch("estoque.api.throttles.LeituraRateThrottle.rate", "2/min", create=True)
    def test_limita_requisicoes_repetidas_por_ip(self):
        self.assertEqual(self.client.get("/api/dashboard/").status_code, 200)
        self.assertEqual(self.client.get("/api/dashboard/").status_code, 200)

        resposta = self.client.get("/api/dashboard/")

        self.assertEqual(resposta.status_code, 429)
        self.assertIn("detail", resposta.json())
        self.assertIn("Retry-After", resposta.headers)

    @override_settings(DATA_UPLOAD_MAX_MEMORY_SIZE=100)
    def test_recusa_payload_excessivo_com_resposta_json(self):
        resposta = self.client.post(
            "/api/ingredientes/",
            data=json.dumps({"nome": "A" * 500}),
            content_type="application/json",
        )

        self.assertEqual(resposta.status_code, 413)
        self.assertEqual(
            resposta.json()["detail"],
            "A requisição excede o tamanho máximo permitido.",
        )

    def test_respostas_possuem_headers_de_seguranca(self):
        resposta = self.client.get("/", secure=True)

        self.assertEqual(resposta.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(resposta.headers["Referrer-Policy"], "same-origin")
        self.assertEqual(resposta.headers["Cross-Origin-Opener-Policy"], "same-origin")
        self.assertEqual(resposta.headers["X-Frame-Options"], "DENY")

    @patch(
        "estoque.api.views.criar_rascunho",
        side_effect=IntegrityError("concorrência simulada"),
    )
    def test_concorrencia_de_fechamentos_retorna_conflito(self, criar):
        resposta = self.client.post(
            "/api/fechamentos/",
            {"referencia": "2026-09-01"},
            content_type="application/json",
        )

        self.assertEqual(resposta.status_code, 409)
        self.assertEqual(
            resposta.json()["detail"],
            "Já existe um fechamento ativo para este mês.",
        )
        criar.assert_called_once()

    def test_campos_historicos_do_item_nao_podem_ser_alterados_pela_api(self):
        ingrediente = Ingrediente.objects.create(
            nome="Farinha",
            unidade="KG",
            meta_atual=Decimal("20"),
            estoque_atual=Decimal("5"),
            data_validade=date(2027, 1, 1),
        )
        fechamento = criar_rascunho(date(2026, 9, 1))
        item = fechamento.itens.get()

        resposta = self.client.patch(
            f"/api/fechamentos/{fechamento.pk}/itens/",
            {"itens": [{
                "id": item.pk,
                "ingrediente": 999,
                "nome_registrado": "Nome adulterado",
                "unidade_registrada": "UN",
                "meta_anterior": "999.000",
                "consumo_mensal": "10.000",
            }]},
            content_type="application/json",
        )

        self.assertEqual(resposta.status_code, 200, resposta.content)
        item.refresh_from_db()
        self.assertEqual(item.ingrediente, ingrediente)
        self.assertEqual(item.nome_registrado, "Farinha")
        self.assertEqual(item.unidade_registrada, "KG")
        self.assertEqual(item.meta_anterior, Decimal("20"))
        self.assertEqual(item.consumo_mensal, Decimal("10"))
