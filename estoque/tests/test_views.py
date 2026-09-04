from django.test import TestCase
from django.urls import reverse


class DashboardViewTests(TestCase):
    def test_dashboard_responde_com_sucesso(self):
        response = self.client.get(reverse("estoque:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Controle de Estoque")
