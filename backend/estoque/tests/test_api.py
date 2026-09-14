from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from estoque.models import FechamentoMensal, Ingrediente, StatusFechamento


class ApiTests(TestCase):
    def criar_ingrediente(self, nome="Farinha", unidade="KG"):
        return Ingrediente.objects.create(
            nome=nome,
            unidade=unidade,
            meta_atual=Decimal("20"),
            estoque_atual=Decimal("6"),
            data_validade=date(2026, 10, 20),
        )

    def test_dashboard_retorna_resumo_em_json(self):
        self.criar_ingrediente()
        Ingrediente.objects.create(
            nome="Leite condensado",
            unidade="UN",
            meta_atual=10,
            estoque_atual=2,
            data_validade=timezone.localdate() + timedelta(days=3),
        )

        resposta = self.client.get("/api/dashboard/")

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()["totais"]["ingredientes"], 2)
        self.assertEqual(resposta.json()["totais"]["proximos_do_vencimento"], 1)

    def test_cria_lista_edita_e_desativa_ingrediente(self):
        resposta = self.client.post(
            "/api/ingredientes/",
            {
                "nome": "Açúcar",
                "unidade": "KG",
                "meta_atual": "12.500",
                "estoque_atual": "3.000",
                "data_validade": "2027-01-10",
            },
            content_type="application/json",
        )
        self.assertEqual(resposta.status_code, 201, resposta.content)
        ingrediente_id = resposta.json()["id"]

        resposta = self.client.patch(
            f"/api/ingredientes/{ingrediente_id}/",
            {"meta_atual": "15.000"},
            content_type="application/json",
        )
        self.assertEqual(resposta.status_code, 200, resposta.content)
        self.assertEqual(resposta.json()["meta_atual"], "15.000")

        resposta = self.client.post(f"/api/ingredientes/{ingrediente_id}/desativar/")
        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(resposta.json()["ativo"])
        self.assertEqual(self.client.get("/api/ingredientes/").json(), [])
        self.assertEqual(len(self.client.get("/api/ingredientes/?situacao=todos").json()), 1)

        resposta = self.client.post(f"/api/ingredientes/{ingrediente_id}/reativar/")
        self.assertEqual(resposta.status_code, 200)
        self.assertTrue(resposta.json()["ativo"])

    def test_recusa_nome_duplicado_e_unidade_fracionada(self):
        self.criar_ingrediente("Ovos", "UN")
        duplicado = self.client.post(
            "/api/ingredientes/",
            {
                "nome": " ovos ", "unidade": "UN", "meta_atual": 10,
                "estoque_atual": 2, "data_validade": "2027-01-10",
            },
            content_type="application/json",
        )
        fracionado = self.client.post(
            "/api/ingredientes/",
            {
                "nome": "Leite", "unidade": "UN", "meta_atual": "10.5",
                "estoque_atual": 2, "data_validade": "2027-01-10",
            },
            content_type="application/json",
        )

        self.assertEqual(duplicado.status_code, 400)
        self.assertEqual(fracionado.status_code, 400)

    def test_fluxo_completo_de_fechamento_e_downloads(self):
        self.criar_ingrediente()
        resposta = self.client.post(
            "/api/fechamentos/",
            {"referencia": "2026-09-18"},
            content_type="application/json",
        )
        self.assertEqual(resposta.status_code, 201, resposta.content)
        fechamento_id = resposta.json()["id"]
        item_id = resposta.json()["itens"][0]["id"]
        self.assertEqual(resposta.json()["referencia"], "2026-09-01")

        resposta = self.client.patch(
            f"/api/fechamentos/{fechamento_id}/itens/",
            {"itens": [{
                "id": item_id,
                "consumo_mensal": "20.000",
                "estoque_restante": "6.000",
                "validade_registrada": "2026-10-20",
                "houve_falta": False,
            }]},
            content_type="application/json",
        )
        self.assertEqual(resposta.status_code, 200, resposta.content)

        revisao = self.client.get(
            f"/api/fechamentos/{fechamento_id}/revisao/?data_apuracao=2026-09-30"
        )
        self.assertEqual(revisao.status_code, 200, revisao.content)
        self.assertEqual(
            revisao.json()["itens"][0]["linha_compra"],
            "Comprar: 14 Kg de Farinha",
        )
        self.assertEqual(revisao.json()["itens"][0]["unidade_exibicao"], "Kg")
        self.assertEqual(revisao.json()["itens"][0]["meta_anterior"], 20.0)

        finalizacao = self.client.post(
            f"/api/fechamentos/{fechamento_id}/finalizar/?data_apuracao=2026-09-30"
        )
        self.assertEqual(finalizacao.status_code, 200, finalizacao.content)
        self.assertEqual(finalizacao.json()["status"], StatusFechamento.FINALIZADO)
        self.assertEqual(
            finalizacao.json()["itens"][0]["linha_compra"],
            "Comprar: 14 Kg de Farinha",
        )

        historico = self.client.get("/api/fechamentos/")
        self.assertEqual(historico.json()[0]["total_itens"], 1)
        self.assertEqual(historico.json()[0]["total_compras"], 1)

        txt = self.client.get(f"/api/fechamentos/{fechamento_id}/lista.txt")
        csv = self.client.get(f"/api/fechamentos/{fechamento_id}/lista.csv")
        self.assertEqual(txt.status_code, 200)
        self.assertEqual(csv.status_code, 200)
        self.assertIn(b"Comprar: 14 Kg de Farinha", txt.content)
        self.assertIn(b"Farinha,14,Kg", csv.content)

    def test_recusa_fechamento_duplicado_incompleto_e_dupla_finalizacao(self):
        self.criar_ingrediente()
        primeira = self.client.post(
            "/api/fechamentos/",
            {"referencia": "2026-09-01"},
            content_type="application/json",
        )
        fechamento_id = primeira.json()["id"]

        duplicado = self.client.post(
            "/api/fechamentos/",
            {"referencia": "2026-09-20"},
            content_type="application/json",
        )
        revisao = self.client.get(f"/api/fechamentos/{fechamento_id}/revisao/")
        download = self.client.get(f"/api/fechamentos/{fechamento_id}/lista.txt")

        self.assertEqual(duplicado.status_code, 400)
        self.assertEqual(revisao.status_code, 400)
        self.assertEqual(download.status_code, 409)

        item = FechamentoMensal.objects.get(pk=fechamento_id).itens.get()
        item.consumo_mensal = Decimal("20")
        item.estoque_restante = Decimal("6")
        item.save()
        self.client.post(f"/api/fechamentos/{fechamento_id}/finalizar/")
        repetida = self.client.post(f"/api/fechamentos/{fechamento_id}/finalizar/")
        edicao = self.client.patch(
            f"/api/fechamentos/{fechamento_id}/itens/",
            {"itens": [{"id": item.pk, "consumo_mensal": 5}]},
            content_type="application/json",
        )
        self.assertEqual(repetida.status_code, 409)
        self.assertEqual(edicao.status_code, 409)

    def test_falta_exige_estoque_zero(self):
        self.criar_ingrediente()
        fechamento = self.client.post(
            "/api/fechamentos/",
            {"referencia": "2026-09-01"},
            content_type="application/json",
        ).json()
        resposta = self.client.patch(
            f"/api/fechamentos/{fechamento['id']}/itens/",
            {"itens": [{
                "id": fechamento["itens"][0]["id"],
                "estoque_restante": "1.000",
                "houve_falta": True,
            }]},
            content_type="application/json",
        )
        self.assertEqual(resposta.status_code, 400)

    def test_cancela_rascunho_mantem_historico_e_libera_o_mes(self):
        self.criar_ingrediente()
        criado = self.client.post(
            "/api/fechamentos/",
            {"referencia": "2026-09-01"},
            content_type="application/json",
        ).json()

        cancelado = self.client.post(
            f"/api/fechamentos/{criado['id']}/cancelar/"
        )

        self.assertEqual(cancelado.status_code, 200, cancelado.content)
        self.assertEqual(cancelado.json()["status"], StatusFechamento.CANCELADO)
        self.assertIsNotNone(cancelado.json()["cancelado_em"])
        self.assertEqual(len(cancelado.json()["itens"]), 1)

        edicao = self.client.patch(
            f"/api/fechamentos/{criado['id']}/itens/",
            {"itens": [{"id": criado["itens"][0]["id"], "consumo_mensal": 5}]},
            content_type="application/json",
        )
        segundo_cancelamento = self.client.post(
            f"/api/fechamentos/{criado['id']}/cancelar/"
        )
        novo = self.client.post(
            "/api/fechamentos/",
            {"referencia": "2026-09-20"},
            content_type="application/json",
        )

        self.assertEqual(edicao.status_code, 409)
        self.assertEqual(segundo_cancelamento.status_code, 409)
        self.assertEqual(novo.status_code, 201, novo.content)
        self.assertEqual(
            FechamentoMensal.objects.filter(
                referencia=date(2026, 9, 1),
                status=StatusFechamento.CANCELADO,
            ).count(),
            1,
        )
