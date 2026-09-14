import csv
import io
from datetime import date
from decimal import Decimal

from django.test import TestCase

from estoque.models import Ingrediente, UnidadeMedida
from estoque.services.exportacoes import (
    ErroExportacao,
    gerar_csv,
    gerar_txt,
    obter_itens_compra,
)
from estoque.services.fechamentos import criar_rascunho, finalizar_fechamento


class ExportacoesTests(TestCase):
    def setUp(self):
        Ingrediente.objects.create(
            nome="Ovos",
            unidade=UnidadeMedida.UNIDADE,
            meta_atual=Decimal("12"),
            estoque_atual=Decimal("0"),
            data_validade=date(2026, 10, 20),
        )
        Ingrediente.objects.create(
            nome="Farinha",
            unidade=UnidadeMedida.QUILOGRAMA,
            meta_atual=Decimal("20"),
            estoque_atual=Decimal("6"),
            data_validade=date(2026, 10, 20),
        )
        self.fechamento = criar_rascunho(date(2026, 9, 1))
        for item in self.fechamento.itens.all():
            item.consumo_mensal = item.meta_anterior
            item.estoque_restante = (
                Decimal("6")
                if item.nome_registrado == "Farinha"
                else Decimal("12")
            )
            item.validade_registrada = date(2026, 10, 20)
            item.save()

    def test_lista_positiva_e_ordenada(self):
        finalizar_fechamento(
            self.fechamento.pk,
            data_apuracao=date(2026, 9, 30),
        )

        itens = obter_itens_compra(self.fechamento)

        self.assertEqual([item.ingrediente for item in itens], ["Farinha"])
        self.assertEqual(itens[0].linha, "Comprar: 14 Kg de Farinha")

    def test_txt_contem_periodo_e_formato_obrigatorio(self):
        finalizar_fechamento(self.fechamento.pk)

        conteudo = gerar_txt(self.fechamento)

        self.assertTrue(conteudo.startswith("Lista de compras — 09/2026\n"))
        self.assertIn("Comprar: 14 Kg de Farinha\n", conteudo)
        self.assertNotIn("Ovos", conteudo)

    def test_csv_possui_cabecalhos_e_mesmos_valores(self):
        finalizar_fechamento(self.fechamento.pk)

        linhas = list(csv.reader(io.StringIO(gerar_csv(self.fechamento))))

        self.assertEqual(linhas[0], ["ingrediente", "quantidade", "unidade"])
        self.assertEqual(linhas[1], ["Farinha", "14", "Kg"])

    def test_rascunho_nao_pode_ser_exportado(self):
        with self.assertRaises(ErroExportacao):
            obter_itens_compra(self.fechamento)

    def test_lista_vazia_tem_mensagem_no_txt_e_csv(self):
        for item in self.fechamento.itens.all():
            item.estoque_restante = item.meta_anterior
            item.save()
        finalizar_fechamento(self.fechamento.pk)

        self.assertIn(
            "Nenhum item precisa ser comprado",
            gerar_txt(self.fechamento),
        )
        self.assertIn(
            "Nenhum item precisa ser comprado",
            gerar_csv(self.fechamento),
        )
