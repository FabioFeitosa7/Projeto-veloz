from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from estoque.models import Ingrediente, UnidadeMedida


class IngredienteViewTests(TestCase):
    def setUp(self):
        self.ingrediente = Ingrediente.objects.create(
            nome="Farinha",
            unidade=UnidadeMedida.QUILOGRAMA,
            meta_atual=Decimal("20"),
            estoque_atual=Decimal("6"),
            data_validade=date(2026, 10, 20),
        )

    def dados_validos(self, **alteracoes):
        dados = {
            "nome": "Leite",
            "unidade": UnidadeMedida.LITRO,
            "meta_atual": "20",
            "estoque_atual": "5",
            "data_validade": "2026-10-10",
        }
        dados.update(alteracoes)
        return dados

    def test_lista_exibe_ingrediente_ativo(self):
        resposta = self.client.get(reverse("estoque:ingrediente_lista"))

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Farinha")
        self.assertContains(resposta, "Último estoque")

    def test_lista_filtra_por_busca(self):
        Ingrediente.objects.create(
            nome="Açúcar",
            unidade=UnidadeMedida.QUILOGRAMA,
            meta_atual=Decimal("10"),
            estoque_atual=Decimal("2"),
            data_validade=date(2026, 11, 1),
        )

        resposta = self.client.get(
            reverse("estoque:ingrediente_lista"),
            {"q": "far"},
        )

        self.assertContains(resposta, "Farinha")
        self.assertNotContains(resposta, "Açúcar")

    def test_lista_oculta_inativos_por_padrao(self):
        self.ingrediente.ativo = False
        self.ingrediente.save()

        resposta = self.client.get(reverse("estoque:ingrediente_lista"))

        self.assertNotContains(resposta, "Farinha")

    def test_filtro_exibe_inativos(self):
        self.ingrediente.ativo = False
        self.ingrediente.save()

        resposta = self.client.get(
            reverse("estoque:ingrediente_lista"),
            {"situacao": "inativos"},
        )

        self.assertContains(resposta, "Farinha")
        self.assertContains(resposta, "Inativo")

    def test_detalhe_exibe_dados(self):
        resposta = self.client.get(
            reverse(
                "estoque:ingrediente_detalhe",
                args=(self.ingrediente.pk,),
            )
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Farinha")
        self.assertContains(resposta, "Meta mensal")
        self.assertContains(resposta, "data-confirm")

    def test_detalhe_inexistente_retorna_404(self):
        resposta = self.client.get(
            reverse("estoque:ingrediente_detalhe", args=(9999,))
        )

        self.assertEqual(resposta.status_code, 404)

    def test_cadastro_valido_cria_ingrediente(self):
        resposta = self.client.post(
            reverse("estoque:ingrediente_novo"),
            self.dados_validos(),
        )

        ingrediente = Ingrediente.objects.get(nome="Leite")
        self.assertRedirects(
            resposta,
            reverse("estoque:ingrediente_detalhe", args=(ingrediente.pk,)),
        )

    def test_cadastro_invalido_reexibe_erros(self):
        resposta = self.client.post(
            reverse("estoque:ingrediente_novo"),
            self.dados_validos(meta_atual="-1"),
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "A meta deve ser maior que zero.")
        self.assertFalse(Ingrediente.objects.filter(nome="Leite").exists())

    def test_edicao_atualiza_ingrediente(self):
        resposta = self.client.post(
            reverse(
                "estoque:ingrediente_editar",
                args=(self.ingrediente.pk,),
            ),
            self.dados_validos(nome="Farinha integral"),
        )

        self.ingrediente.refresh_from_db()
        self.assertEqual(self.ingrediente.nome, "Farinha integral")
        self.assertRedirects(
            resposta,
            reverse(
                "estoque:ingrediente_detalhe",
                args=(self.ingrediente.pk,),
            ),
        )

    def test_desativacao_exige_post(self):
        resposta = self.client.get(
            reverse(
                "estoque:ingrediente_desativar",
                args=(self.ingrediente.pk,),
            )
        )

        self.assertEqual(resposta.status_code, 405)
        self.ingrediente.refresh_from_db()
        self.assertTrue(self.ingrediente.ativo)

    def test_desativacao_por_post(self):
        resposta = self.client.post(
            reverse(
                "estoque:ingrediente_desativar",
                args=(self.ingrediente.pk,),
            )
        )

        self.ingrediente.refresh_from_db()
        self.assertFalse(self.ingrediente.ativo)
        self.assertRedirects(
            resposta,
            reverse(
                "estoque:ingrediente_detalhe",
                args=(self.ingrediente.pk,),
            ),
        )

    def test_reativacao_por_post(self):
        self.ingrediente.ativo = False
        self.ingrediente.save()

        resposta = self.client.post(
            reverse(
                "estoque:ingrediente_reativar",
                args=(self.ingrediente.pk,),
            )
        )

        self.ingrediente.refresh_from_db()
        self.assertTrue(self.ingrediente.ativo)
        self.assertRedirects(
            resposta,
            reverse(
                "estoque:ingrediente_detalhe",
                args=(self.ingrediente.pk,),
            ),
        )
