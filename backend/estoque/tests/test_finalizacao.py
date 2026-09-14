from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from estoque.models import Ingrediente, StatusFechamento, UnidadeMedida
from estoque.services.fechamentos import (
    ErroFechamento,
    cancelar_fechamento,
    calcular_revisao,
    criar_rascunho,
    finalizar_fechamento,
)


class FinalizacaoBase(TestCase):
    def criar_item(
        self,
        *,
        nome="Farinha",
        unidade=UnidadeMedida.QUILOGRAMA,
        meta=Decimal("20"),
        consumo=Decimal("14"),
        estoque=Decimal("6"),
        validade=date(2026, 10, 20),
        houve_falta=False,
    ):
        ingrediente = Ingrediente.objects.create(
            nome=nome,
            unidade=unidade,
            meta_atual=meta,
            estoque_atual=Decimal("9"),
            data_validade=date(2026, 11, 20),
        )
        fechamento = criar_rascunho(date(2026, 9, 1))
        item = fechamento.itens.get(ingrediente=ingrediente)
        item.consumo_mensal = consumo
        item.estoque_restante = estoque
        item.validade_registrada = validade
        item.houve_falta = houve_falta
        item.save()
        return ingrediente, fechamento, item


class RevisaoServiceTests(FinalizacaoBase):
    def test_revisao_calcula_sem_persistir_ou_atualizar_ingrediente(self):
        ingrediente, fechamento, item = self.criar_item()

        revisao = calcular_revisao(
            fechamento,
            data_apuracao=date(2026, 9, 30),
        )

        item.refresh_from_db()
        ingrediente.refresh_from_db()
        self.assertEqual(revisao[0].resultado.quantidade_compra, Decimal("14"))
        self.assertEqual(
            revisao[0].linha_compra,
            "Comprar: 14 Kg de Farinha",
        )
        self.assertIsNone(item.quantidade_compra)
        self.assertEqual(ingrediente.estoque_atual, Decimal("9"))

    def test_revisao_recusa_item_incompleto(self):
        _, fechamento, item = self.criar_item()
        item.consumo_mensal = None
        item.save()

        with self.assertRaisesMessage(
            ErroFechamento,
            "Preencha todos os dados de Farinha antes de revisar.",
        ):
            calcular_revisao(fechamento)


class CancelarServiceTests(FinalizacaoBase):
    def test_cancela_rascunho_sem_apagar_itens(self):
        _, fechamento, item = self.criar_item()
        cancelar_fechamento(fechamento.pk)

        fechamento.refresh_from_db()
        self.assertEqual(fechamento.status, StatusFechamento.CANCELADO)
        self.assertIsNotNone(fechamento.cancelado_em)
        self.assertTrue(fechamento.itens.filter(pk=item.pk).exists())

    def test_nao_permite_cancelar_fechamento_finalizado(self):
        _, fechamento, _ = self.criar_item()
        finalizar_fechamento(fechamento.pk, data_apuracao=date(2026, 9, 30))

        with self.assertRaises(ErroFechamento):
            cancelar_fechamento(fechamento.pk)

    def test_nao_permite_cancelar_duas_vezes(self):
        _, fechamento, _ = self.criar_item()
        cancelar_fechamento(fechamento.pk)

        with self.assertRaises(ErroFechamento):
            cancelar_fechamento(fechamento.pk)


class FinalizarServiceTests(FinalizacaoBase):
    def test_falta_atualiza_meta_e_resultados_historicos(self):
        ingrediente, fechamento, item = self.criar_item(
            unidade=UnidadeMedida.UNIDADE,
            meta=Decimal("10"),
            consumo=Decimal("11"),
            estoque=Decimal("0"),
            houve_falta=True,
        )

        finalizar_fechamento(
            fechamento.pk,
            data_apuracao=date(2026, 9, 30),
        )

        fechamento.refresh_from_db()
        ingrediente.refresh_from_db()
        item.refresh_from_db()
        self.assertEqual(fechamento.status, StatusFechamento.FINALIZADO)
        self.assertIsNotNone(fechamento.finalizado_em)
        self.assertEqual(ingrediente.meta_atual, Decimal("14"))
        self.assertEqual(item.meta_resultante, Decimal("14"))
        self.assertEqual(item.quantidade_compra, Decimal("14"))

    def test_vencido_descarta_estoque_restante(self):
        ingrediente, fechamento, item = self.criar_item(
            estoque=Decimal("6"),
            validade=date(2026, 9, 29),
        )

        finalizar_fechamento(
            fechamento.pk,
            data_apuracao=date(2026, 9, 30),
        )

        ingrediente.refresh_from_db()
        item.refresh_from_db()
        self.assertTrue(item.estava_vencido)
        self.assertEqual(item.estoque_aproveitavel, Decimal("0"))
        self.assertEqual(item.quantidade_compra, Decimal("20"))
        self.assertEqual(ingrediente.estoque_atual, Decimal("0"))

    def test_segunda_finalizacao_e_bloqueada(self):
        _, fechamento, _ = self.criar_item()
        finalizar_fechamento(fechamento.pk, data_apuracao=date(2026, 9, 30))

        with self.assertRaisesMessage(
            ErroFechamento,
            "Este fechamento já foi finalizado.",
        ):
            finalizar_fechamento(fechamento.pk)

    def test_falha_intermediaria_desfaz_todas_as_alteracoes(self):
        ingrediente, fechamento, item = self.criar_item()

        with patch.object(Ingrediente, "save", side_effect=RuntimeError("falha")):
            with self.assertRaises(RuntimeError):
                finalizar_fechamento(
                    fechamento.pk,
                    data_apuracao=date(2026, 9, 30),
                )

        fechamento.refresh_from_db()
        ingrediente.refresh_from_db()
        item.refresh_from_db()
        self.assertEqual(fechamento.status, StatusFechamento.RASCUNHO)
        self.assertIsNone(item.quantidade_compra)
        self.assertEqual(ingrediente.estoque_atual, Decimal("9"))
