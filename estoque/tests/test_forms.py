from datetime import date
from decimal import Decimal

from django.test import TestCase

from estoque.forms import (
    FechamentoMensalForm,
    IngredienteForm,
    ItemFechamentoForm,
    ItemFechamentoFormSet,
)
from estoque.models import (
    FechamentoMensal,
    Ingrediente,
    ItemFechamento,
    UnidadeMedida,
)


class IngredienteFormTests(TestCase):
    def dados_validos(self, **alteracoes):
        dados = {
            "nome": "Farinha",
            "unidade": UnidadeMedida.QUILOGRAMA,
            "meta_atual": "20,5",
            "estoque_atual": "6,25",
            "data_validade": "2026-10-20",
        }
        dados.update(alteracoes)
        return dados

    def test_formulario_valido_aceita_decimal_com_virgula(self):
        formulario = IngredienteForm(data=self.dados_validos())

        self.assertTrue(formulario.is_valid(), formulario.errors)
        self.assertEqual(formulario.cleaned_data["meta_atual"], Decimal("20.5"))

    def test_ct14_meta_negativa_e_recusada(self):
        formulario = IngredienteForm(
            data=self.dados_validos(meta_atual="-5")
        )

        self.assertFalse(formulario.is_valid())
        self.assertIn(
            "A meta deve ser maior que zero.",
            formulario.errors["meta_atual"],
        )

    def test_ct15_estoque_negativo_e_recusado(self):
        formulario = IngredienteForm(
            data=self.dados_validos(estoque_atual="-1")
        )

        self.assertFalse(formulario.is_valid())
        self.assertIn(
            "O estoque não pode ser negativo.",
            formulario.errors["estoque_atual"],
        )

    def test_ct17_unidade_indivisivel_recusa_fracao(self):
        formulario = IngredienteForm(
            data=self.dados_validos(
                unidade=UnidadeMedida.UNIDADE,
                meta_atual="10,5",
                estoque_atual="2",
            )
        )

        self.assertFalse(formulario.is_valid())
        self.assertIn("meta_atual", formulario.errors)

    def test_ct18_campos_obrigatorios_ausentes(self):
        formulario = IngredienteForm(data={})

        self.assertFalse(formulario.is_valid())
        self.assertIn("nome", formulario.errors)
        self.assertIn("unidade", formulario.errors)
        self.assertIn("meta_atual", formulario.errors)
        self.assertIn("estoque_atual", formulario.errors)
        self.assertIn("data_validade", formulario.errors)

    def test_nome_duplicado_recebe_mensagem_amigavel(self):
        Ingrediente.objects.create(
            nome="Farinha",
            unidade=UnidadeMedida.QUILOGRAMA,
            meta_atual=Decimal("20"),
            estoque_atual=Decimal("6"),
            data_validade=date(2026, 10, 20),
        )
        formulario = IngredienteForm(
            data=self.dados_validos(nome="  FARINHA  ")
        )

        self.assertFalse(formulario.is_valid())
        self.assertIn(
            "Já existe um ingrediente com este nome.",
            formulario.errors["nome"],
        )


class FechamentoMensalFormTests(TestCase):
    def test_mes_e_convertido_para_primeiro_dia(self):
        formulario = FechamentoMensalForm(data={"referencia": "2026-09"})

        self.assertTrue(formulario.is_valid(), formulario.errors)
        self.assertEqual(
            formulario.cleaned_data["referencia"],
            date(2026, 9, 1),
        )

    def test_mes_duplicado_recebe_mensagem_amigavel(self):
        FechamentoMensal.objects.create(referencia=date(2026, 9, 1))
        formulario = FechamentoMensalForm(data={"referencia": "2026-09"})

        self.assertFalse(formulario.is_valid())
        self.assertIn(
            "Já existe um fechamento para este mês.",
            formulario.errors["referencia"],
        )


class ItemFechamentoFormTests(TestCase):
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
        self.item = ItemFechamento.objects.create(
            fechamento=self.fechamento,
            ingrediente=self.ingrediente,
            nome_registrado=self.ingrediente.nome,
            unidade_registrada=self.ingrediente.unidade,
            meta_anterior=self.ingrediente.meta_atual,
        )

    def dados_validos(self, **alteracoes):
        dados = {
            "consumo_mensal": "43",
            "estoque_restante": "0",
            "validade_registrada": "2026-10-10",
            "houve_falta": "on",
        }
        dados.update(alteracoes)
        return dados

    def test_item_valido(self):
        formulario = ItemFechamentoForm(
            data=self.dados_validos(),
            instance=self.item,
        )

        self.assertTrue(formulario.is_valid(), formulario.errors)

    def test_ct16_consumo_negativo_e_recusado(self):
        formulario = ItemFechamentoForm(
            data=self.dados_validos(consumo_mensal="-10"),
            instance=self.item,
        )

        self.assertFalse(formulario.is_valid())
        self.assertIn(
            "O consumo não pode ser negativo.",
            formulario.errors["consumo_mensal"],
        )

    def test_falta_com_estoque_positivo_e_recusada(self):
        formulario = ItemFechamentoForm(
            data=self.dados_validos(estoque_restante="2"),
            instance=self.item,
        )

        self.assertFalse(formulario.is_valid())
        self.assertIn("estoque_restante", formulario.errors)

    def test_unidade_indivisivel_recusa_consumo_fracionario(self):
        formulario = ItemFechamentoForm(
            data=self.dados_validos(consumo_mensal="42,5"),
            instance=self.item,
        )

        self.assertFalse(formulario.is_valid())
        self.assertIn("consumo_mensal", formulario.errors)

    def test_campos_mensais_sao_obrigatorios(self):
        formulario = ItemFechamentoForm(data={}, instance=self.item)

        self.assertFalse(formulario.is_valid())
        self.assertIn("consumo_mensal", formulario.errors)
        self.assertIn("estoque_restante", formulario.errors)
        self.assertIn("validade_registrada", formulario.errors)

    def test_formset_valido_com_item_existente(self):
        dados = {
            "form-TOTAL_FORMS": "1",
            "form-INITIAL_FORMS": "1",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
            "form-0-id": str(self.item.pk),
            "form-0-consumo_mensal": "43",
            "form-0-estoque_restante": "0",
            "form-0-validade_registrada": "2026-10-10",
            "form-0-houve_falta": "on",
        }
        formulario = ItemFechamentoFormSet(
            data=dados,
            queryset=ItemFechamento.objects.filter(pk=self.item.pk),
        )

        self.assertTrue(formulario.is_valid(), formulario.errors)
