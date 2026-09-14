from datetime import date
from decimal import Decimal

from django.test import TestCase

from estoque.models import FechamentoMensal, Ingrediente, UnidadeMedida
from estoque.services.fechamentos import ErroFechamento, criar_rascunho


class CriarRascunhoServiceTests(TestCase):
    def criar_ingrediente(self, nome="Farinha", ativo=True):
        return Ingrediente.objects.create(
            nome=nome,
            unidade=UnidadeMedida.QUILOGRAMA,
            meta_atual=Decimal("20"),
            estoque_atual=Decimal("6"),
            data_validade=date(2026, 10, 20),
            ativo=ativo,
        )

    def test_cria_retrato_apenas_dos_ingredientes_ativos(self):
        ativo = self.criar_ingrediente()
        self.criar_ingrediente(nome="Inativo", ativo=False)

        fechamento = criar_rascunho(date(2026, 9, 1))

        self.assertEqual(fechamento.itens.count(), 1)
        item = fechamento.itens.get()
        self.assertEqual(item.ingrediente, ativo)
        self.assertEqual(item.nome_registrado, "Farinha")
        self.assertEqual(item.meta_anterior, Decimal("20"))
        self.assertEqual(item.validade_registrada, date(2026, 10, 20))

    def test_sem_ingrediente_ativo_nao_cria_fechamento(self):
        with self.assertRaisesMessage(
            ErroFechamento,
            "Cadastre pelo menos um ingrediente ativo antes do fechamento.",
        ):
            criar_rascunho(date(2026, 9, 1))

        self.assertFalse(FechamentoMensal.objects.exists())
