from datetime import date, timedelta
from decimal import Decimal

from django.test import SimpleTestCase

from estoque.services.calculos import (
    ErroRegraNegocio,
    MotivoReposicao,
    SituacaoValidade,
    calcular_reposicao,
    classificar_validade,
    formatar_item_compra,
    resumir_validade,
)


DATA_APURACAO = date(2026, 9, 30)
VALIDADE_FUTURA = date(2026, 10, 20)


class CalculoReposicaoTests(SimpleTestCase):
    def test_ct01_reposicao_normal(self):
        resultado = calcular_reposicao(
            meta_atual="20",
            consumo_mensal="14",
            estoque_restante="6",
            unidade="KG",
            data_validade=VALIDADE_FUTURA,
            data_apuracao=DATA_APURACAO,
            houve_falta=False,
        )

        self.assertEqual(resultado.quantidade_compra, Decimal("14"))
        self.assertEqual(resultado.motivo, MotivoReposicao.NORMAL)
        self.assertEqual(
            formatar_item_compra(
                ingrediente="Farinha",
                quantidade=resultado.quantidade_compra,
                unidade="KG",
            ),
            "Comprar: 14 Kg de Farinha",
        )

    def test_ct02_estoque_igual_a_meta_nao_entra_na_lista(self):
        resultado = calcular_reposicao(
            meta_atual="30",
            consumo_mensal="0",
            estoque_restante="30",
            unidade="KG",
            data_validade=VALIDADE_FUTURA,
            data_apuracao=DATA_APURACAO,
            houve_falta=False,
        )

        self.assertEqual(resultado.quantidade_calculada, Decimal("0"))
        self.assertIsNone(
            formatar_item_compra(
                ingrediente="Arroz",
                quantidade=resultado.quantidade_compra,
                unidade="KG",
            )
        )

    def test_ct03_estoque_superior_a_meta_nao_entra_na_lista(self):
        resultado = calcular_reposicao(
            meta_atual="15",
            consumo_mensal="0",
            estoque_restante="18",
            unidade="KG",
            data_validade=VALIDADE_FUTURA,
            data_apuracao=DATA_APURACAO,
            houve_falta=False,
        )

        self.assertEqual(resultado.quantidade_calculada, Decimal("-3"))
        self.assertEqual(resultado.quantidade_compra, Decimal("0"))
        self.assertIsNone(
            formatar_item_compra(
                ingrediente="Açúcar",
                quantidade=resultado.quantidade_compra,
                unidade="KG",
            )
        )

    def test_ct04_vencido_desconsidera_estoque_restante(self):
        resultado = calcular_reposicao(
            meta_atual="20",
            consumo_mensal="15",
            estoque_restante="5",
            unidade="L",
            data_validade=DATA_APURACAO - timedelta(days=1),
            data_apuracao=DATA_APURACAO,
            houve_falta=False,
        )

        self.assertEqual(resultado.estoque_aproveitavel, Decimal("0"))
        self.assertEqual(resultado.quantidade_compra, Decimal("20"))
        self.assertEqual(resultado.motivo, MotivoReposicao.VENCIMENTO)

    def test_ct05_falta_reajusta_meta_em_vinte_por_cento(self):
        resultado = calcular_reposicao(
            meta_atual="50",
            consumo_mensal="50",
            estoque_restante="0",
            unidade="KG",
            data_validade=VALIDADE_FUTURA,
            data_apuracao=DATA_APURACAO,
            houve_falta=True,
        )

        self.assertEqual(resultado.meta_resultante, Decimal("60.00"))
        self.assertEqual(resultado.quantidade_compra, Decimal("60.00"))
        self.assertEqual(resultado.motivo, MotivoReposicao.FALTA)

    def test_ct06_falta_com_estoque_positivo_e_recusada(self):
        with self.assertRaisesMessage(
            ErroRegraNegocio,
            "Estoque restante deve ser zero quando houve falta antecipada.",
        ):
            calcular_reposicao(
                meta_atual="50",
                consumo_mensal="48",
                estoque_restante="2",
                unidade="KG",
                data_validade=VALIDADE_FUTURA,
                data_apuracao=DATA_APURACAO,
                houve_falta=True,
            )

    def test_ct07_falta_e_vencimento_sao_aplicados_juntos(self):
        resultado = calcular_reposicao(
            meta_atual="10",
            consumo_mensal="10",
            estoque_restante="0",
            unidade="KG",
            data_validade=DATA_APURACAO - timedelta(days=1),
            data_apuracao=DATA_APURACAO,
            houve_falta=True,
        )

        self.assertEqual(resultado.meta_resultante, Decimal("12.00"))
        self.assertEqual(resultado.estoque_aproveitavel, Decimal("0"))
        self.assertEqual(resultado.quantidade_compra, Decimal("12.00"))
        self.assertEqual(resultado.motivo, MotivoReposicao.FALTA_E_VENCIMENTO)

    def test_ct08_unidade_indivisivel_e_arredondada_para_cima(self):
        resultado = calcular_reposicao(
            meta_atual="43",
            consumo_mensal="43",
            estoque_restante="0",
            unidade="UN",
            data_validade=VALIDADE_FUTURA,
            data_apuracao=DATA_APURACAO,
            houve_falta=True,
        )

        self.assertEqual(resultado.meta_resultante, Decimal("52"))
        self.assertEqual(resultado.quantidade_compra, Decimal("52"))
        self.assertEqual(
            formatar_item_compra(
                ingrediente="Ovo",
                quantidade=resultado.quantidade_compra,
                unidade="UN",
            ),
            "Comprar: 52 Unidades de Ovo",
        )

    def test_ct09_peso_mantem_casas_decimais(self):
        resultado = calcular_reposicao(
            meta_atual="15.5",
            consumo_mensal="10.5",
            estoque_restante="5",
            unidade="KG",
            data_validade=VALIDADE_FUTURA,
            data_apuracao=DATA_APURACAO,
            houve_falta=False,
        )

        self.assertEqual(resultado.quantidade_compra, Decimal("10.5"))
        self.assertEqual(
            formatar_item_compra(
                ingrediente="Farinha",
                quantidade=resultado.quantidade_compra,
                unidade="KG",
            ),
            "Comprar: 10,5 Kg de Farinha",
        )


class ClassificacaoValidadeTests(SimpleTestCase):
    def test_ct10_sete_dias_e_proximo_do_vencimento(self):
        situacao = classificar_validade(
            DATA_APURACAO + timedelta(days=7),
            DATA_APURACAO,
        )

        self.assertEqual(situacao, SituacaoValidade.PROXIMO_DO_VENCIMENTO)

    def test_ct11_oito_dias_esta_dentro_da_validade(self):
        situacao = classificar_validade(
            DATA_APURACAO + timedelta(days=8),
            DATA_APURACAO,
        )

        self.assertEqual(situacao, SituacaoValidade.DENTRO_DA_VALIDADE)

    def test_ct12_validade_igual_a_data_atual_vence_hoje(self):
        situacao = classificar_validade(DATA_APURACAO, DATA_APURACAO)

        self.assertEqual(situacao, SituacaoValidade.VENCE_HOJE)

    def test_ct13_validade_anterior_esta_vencida(self):
        situacao = classificar_validade(
            DATA_APURACAO - timedelta(days=1),
            DATA_APURACAO,
        )

        self.assertEqual(situacao, SituacaoValidade.VENCIDO)

    def test_resumo_usa_singular_para_um_dia(self):
        futuro = resumir_validade(
            DATA_APURACAO + timedelta(days=1),
            DATA_APURACAO,
        )
        passado = resumir_validade(
            DATA_APURACAO - timedelta(days=1),
            DATA_APURACAO,
        )

        self.assertEqual(futuro.descricao, "Vence em 1 dia")
        self.assertEqual(passado.descricao, "Vencido há 1 dia")
