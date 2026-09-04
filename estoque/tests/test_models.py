from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.utils import timezone

from estoque.models import (
    FechamentoMensal,
    Ingrediente,
    ItemFechamento,
    StatusFechamento,
    UnidadeMedida,
)


class IngredienteModelTests(TestCase):
    def criar_ingrediente(self, **alteracoes):
        dados = {
            "nome": "Farinha",
            "unidade": UnidadeMedida.QUILOGRAMA,
            "meta_atual": Decimal("20"),
            "estoque_atual": Decimal("6"),
            "data_validade": date(2026, 10, 20),
        }
        dados.update(alteracoes)
        return Ingrediente.objects.create(**dados)

    def test_cria_ingrediente_e_normaliza_nome(self):
        ingrediente = self.criar_ingrediente(nome="  Farinha   de trigo ")

        self.assertEqual(ingrediente.nome, "Farinha de trigo")
        self.assertEqual(str(ingrediente), "Farinha de trigo")
        self.assertTrue(ingrediente.ativo)

    def test_nome_nao_pode_ser_duplicado_sem_diferenciar_maiusculas(self):
        self.criar_ingrediente(nome="Farinha")

        with self.assertRaises(IntegrityError), transaction.atomic():
            self.criar_ingrediente(nome="FARINHA")

    def test_meta_deve_ser_positiva_no_banco(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.criar_ingrediente(meta_atual=Decimal("0"))

    def test_estoque_nao_pode_ser_negativo_no_banco(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.criar_ingrediente(estoque_atual=Decimal("-1"))

    def test_unidade_nao_aceita_quantidade_fracionaria(self):
        ingrediente = self.criar_ingrediente(
            unidade=UnidadeMedida.UNIDADE,
            meta_atual=Decimal("10.5"),
            estoque_atual=Decimal("2"),
        )

        with self.assertRaises(ValidationError) as contexto:
            ingrediente.full_clean()

        self.assertIn("meta_atual", contexto.exception.message_dict)


class FechamentoMensalModelTests(TestCase):
    def test_referencia_e_normalizada_para_primeiro_dia(self):
        fechamento = FechamentoMensal.objects.create(
            referencia=date(2026, 9, 30)
        )

        self.assertEqual(fechamento.referencia, date(2026, 9, 1))
        self.assertEqual(str(fechamento), "09/2026")
        self.assertEqual(fechamento.status, StatusFechamento.RASCUNHO)

    def test_nao_permite_dois_fechamentos_no_mes(self):
        FechamentoMensal.objects.create(referencia=date(2026, 9, 1))

        with self.assertRaises(IntegrityError), transaction.atomic():
            FechamentoMensal.objects.create(referencia=date(2026, 9, 20))

    def test_finalizado_exige_data_de_finalizacao(self):
        fechamento = FechamentoMensal(
            referencia=date(2026, 9, 1),
            status=StatusFechamento.FINALIZADO,
        )

        with self.assertRaises(ValidationError) as contexto:
            fechamento.full_clean()

        self.assertIn("finalizado_em", contexto.exception.message_dict)

    def test_finalizado_com_data_e_valido(self):
        fechamento = FechamentoMensal(
            referencia=date(2026, 9, 1),
            status=StatusFechamento.FINALIZADO,
            finalizado_em=timezone.now(),
        )

        fechamento.full_clean()


class ItemFechamentoModelTests(TestCase):
    def setUp(self):
        self.ingrediente = Ingrediente.objects.create(
            nome="Ovo",
            unidade=UnidadeMedida.UNIDADE,
            meta_atual=Decimal("43"),
            estoque_atual=Decimal("0"),
            data_validade=date(2026, 10, 10),
        )
        self.fechamento = FechamentoMensal.objects.create(
            referencia=date(2026, 9, 1)
        )

    def montar_item(self, **alteracoes):
        dados = {
            "fechamento": self.fechamento,
            "ingrediente": self.ingrediente,
            "nome_registrado": "Ovo",
            "unidade_registrada": UnidadeMedida.UNIDADE,
            "meta_anterior": Decimal("43"),
        }
        dados.update(alteracoes)
        return ItemFechamento(**dados)

    def criar_item(self, **alteracoes):
        item = self.montar_item(**alteracoes)
        item.save()
        return item

    def test_item_preserva_retrato_do_ingrediente(self):
        item = self.criar_item()
        self.ingrediente.nome = "Ovos caipiras"
        self.ingrediente.save()

        item.refresh_from_db()
        self.assertEqual(item.nome_registrado, "Ovo")
        self.assertEqual(item.meta_anterior, Decimal("43"))

    def test_ingrediente_aparece_uma_vez_por_fechamento(self):
        self.criar_item()

        with self.assertRaises(IntegrityError), transaction.atomic():
            self.criar_item()

    def test_falta_exige_estoque_zero(self):
        item = self.montar_item(
            houve_falta=True,
            estoque_restante=Decimal("2"),
        )

        with self.assertRaises(ValidationError) as contexto:
            item.full_clean()

        self.assertIn("estoque_restante", contexto.exception.message_dict)

    def test_banco_recusa_falta_com_estoque_positivo(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.criar_item(
                houve_falta=True,
                estoque_restante=Decimal("2"),
            )

    def test_item_vencido_exige_estoque_aproveitavel_zero(self):
        item = self.criar_item(
            estava_vencido=True,
            estoque_aproveitavel=Decimal("1"),
        )

        with self.assertRaises(ValidationError) as contexto:
            item.full_clean()

        self.assertIn("estoque_aproveitavel", contexto.exception.message_dict)

    def test_nao_permite_excluir_ingrediente_com_historico(self):
        self.criar_item()

        with self.assertRaises(ProtectedError):
            self.ingrediente.delete()
