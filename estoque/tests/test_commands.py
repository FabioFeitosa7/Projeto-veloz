from datetime import date
from decimal import Decimal
from io import StringIO

from django.core.management import CommandError, call_command
from django.test import TestCase

from estoque.models import Ingrediente, UnidadeMedida
from estoque.services.fechamentos import criar_rascunho, finalizar_fechamento


class GerarListaComprasCommandTests(TestCase):
    def criar_fechamento(self, finalizar=True):
        Ingrediente.objects.create(
            nome="Farinha",
            unidade=UnidadeMedida.QUILOGRAMA,
            meta_atual=Decimal("20"),
            estoque_atual=Decimal("6"),
            data_validade=date(2026, 10, 20),
        )
        fechamento = criar_rascunho(date(2026, 9, 1))
        item = fechamento.itens.get()
        item.consumo_mensal = Decimal("14")
        item.estoque_restante = Decimal("6")
        item.validade_registrada = date(2026, 10, 20)
        item.save()
        if finalizar:
            finalizar_fechamento(fechamento.pk)
        return fechamento

    def test_imprime_formato_obrigatorio(self):
        self.criar_fechamento()
        saida = StringIO()

        call_command("gerar_lista_compras", mes="2026-09", stdout=saida)

        self.assertEqual(saida.getvalue(), "Comprar: 14 Kg de Farinha\n")

    def test_mes_invalido_apresenta_erro(self):
        with self.assertRaisesMessage(CommandError, "formato AAAA-MM"):
            call_command("gerar_lista_compras", mes="09-2026")

    def test_mes_inexistente_apresenta_erro(self):
        with self.assertRaisesMessage(CommandError, "Não existe fechamento"):
            call_command("gerar_lista_compras", mes="2026-09")

    def test_rascunho_apresenta_erro(self):
        self.criar_fechamento(finalizar=False)

        with self.assertRaisesMessage(CommandError, "ainda não foi finalizado"):
            call_command("gerar_lista_compras", mes="2026-09")
