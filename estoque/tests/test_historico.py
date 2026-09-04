from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from estoque.models import Ingrediente, UnidadeMedida
from estoque.services.fechamentos import criar_rascunho, finalizar_fechamento


class HistoricoViewTests(TestCase):
    def setUp(self):
        Ingrediente.objects.create(
            nome="Farinha",
            unidade=UnidadeMedida.QUILOGRAMA,
            meta_atual=Decimal("20"),
            estoque_atual=Decimal("6"),
            data_validade=date(2026, 10, 20),
        )
        self.fechamento = criar_rascunho(date(2026, 9, 1))
        self.item = self.fechamento.itens.get()
        self.item.consumo_mensal = Decimal("14")
        self.item.estoque_restante = Decimal("6")
        self.item.validade_registrada = date(2026, 10, 20)
        self.item.save()

    def test_historico_lista_rascunho(self):
        resposta = self.client.get(reverse("estoque:fechamento_historico"))

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "09/2026")
        self.assertContains(resposta, "Continuar")

    def test_detalhe_finalizado_exibe_lista_e_downloads(self):
        finalizar_fechamento(self.fechamento.pk)

        resposta = self.client.get(
            reverse("estoque:fechamento_detalhe", args=(self.fechamento.pk,))
        )

        self.assertContains(resposta, "Comprar: 14 Kg de Farinha")
        self.assertContains(resposta, "Baixar TXT")
        self.assertContains(resposta, "Baixar CSV")

    def test_download_txt_finalizado(self):
        finalizar_fechamento(self.fechamento.pk)

        resposta = self.client.get(
            reverse("estoque:fechamento_download_txt", args=(self.fechamento.pk,))
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta["Content-Type"], "text/plain; charset=utf-8")
        self.assertIn("lista-compras-2026-09.txt", resposta["Content-Disposition"])
        self.assertIn("Comprar: 14 Kg de Farinha", resposta.content.decode())

    def test_download_csv_finalizado_com_bom_utf8(self):
        finalizar_fechamento(self.fechamento.pk)

        resposta = self.client.get(
            reverse("estoque:fechamento_download_csv", args=(self.fechamento.pk,))
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertTrue(resposta.content.startswith(b"\xef\xbb\xbf"))
        self.assertIn(
            "ingrediente,quantidade,unidade",
            resposta.content.decode("utf-8-sig"),
        )

    def test_download_de_rascunho_e_bloqueado(self):
        resposta = self.client.get(
            reverse("estoque:fechamento_download_txt", args=(self.fechamento.pk,))
        )

        self.assertEqual(resposta.status_code, 403)
        self.assertContains(
            resposta,
            "Revise e finalize o fechamento",
            status_code=403,
        )
