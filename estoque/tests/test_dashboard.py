from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from estoque.models import Ingrediente, UnidadeMedida


class DashboardTests(TestCase):
    def criar_ingrediente(self, nome, dias_validade, ativo=True):
        return Ingrediente.objects.create(
            nome=nome,
            unidade=UnidadeMedida.QUILOGRAMA,
            meta_atual=Decimal("20"),
            estoque_atual=Decimal("6"),
            data_validade=timezone.localdate() + timedelta(days=dias_validade),
            ativo=ativo,
        )

    def test_dashboard_sem_ingredientes_apresenta_orientacao(self):
        resposta = self.client.get(reverse("estoque:dashboard"))

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Cadastre o primeiro ingrediente")
        self.assertEqual(resposta.context["total_ingredientes"], 0)

    def test_dashboard_resume_validades_de_ingredientes_ativos(self):
        self.criar_ingrediente("Farinha", 8)
        self.criar_ingrediente("Leite", 7)
        self.criar_ingrediente("Ovo", 0)
        self.criar_ingrediente("Queijo", -1)
        self.criar_ingrediente("Inativo", -1, ativo=False)

        resposta = self.client.get(reverse("estoque:dashboard"))

        self.assertEqual(resposta.context["total_ingredientes"], 4)
        self.assertEqual(resposta.context["total_proximos"], 2)
        self.assertEqual(resposta.context["total_vencidos"], 1)
        self.assertContains(resposta, "Vence em 7 dias")
        self.assertContains(resposta, "Vence hoje")
        self.assertContains(resposta, "Vencido há 1 dia")
        self.assertNotContains(resposta, "Inativo")

    def test_dashboard_nao_coloca_validade_segura_nos_alertas(self):
        self.criar_ingrediente("Farinha", 8)

        resposta = self.client.get(reverse("estoque:dashboard"))

        self.assertEqual(resposta.context["alertas"], [])
        self.assertContains(
            resposta,
            "Nenhum ingrediente próximo do vencimento ou vencido.",
        )
