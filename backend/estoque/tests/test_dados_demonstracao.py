from decimal import Decimal
from io import StringIO

from django.core.management import CommandError, call_command
from django.test import TestCase

from estoque.models import FechamentoMensal, Ingrediente, StatusFechamento


class CarregarDadosDemonstracaoTests(TestCase):
    def test_cria_cenarios_ficticios_e_fechamento_finalizado(self):
        saida = StringIO()

        call_command("carregar_dados_demonstracao", stdout=saida)

        self.assertEqual(Ingrediente.objects.count(), 4)
        fechamento = FechamentoMensal.objects.get()
        self.assertEqual(fechamento.status, StatusFechamento.FINALIZADO)
        self.assertEqual(fechamento.itens.count(), 4)
        self.assertEqual(
            fechamento.itens.get(nome_registrado="Farinha").quantidade_compra,
            Decimal("14"),
        )
        self.assertEqual(
            fechamento.itens.get(nome_registrado="Ovos").quantidade_compra,
            Decimal("52"),
        )
        self.assertIn("Dados fictícios criados", saida.getvalue())

    def test_recusa_banco_que_ja_possui_dados(self):
        call_command("carregar_dados_demonstracao", stdout=StringIO())

        with self.assertRaisesMessage(CommandError, "banco vazio"):
            call_command("carregar_dados_demonstracao", stdout=StringIO())

        self.assertEqual(Ingrediente.objects.count(), 4)
        self.assertEqual(FechamentoMensal.objects.count(), 1)
