from django.test import TestCase


class BackendStatusTests(TestCase):
    def test_raiz_informa_status_e_caminhos_principais(self):
        resposta = self.client.get("/")

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()["status"], "online")
        self.assertEqual(resposta.json()["api"], "/api/")
        self.assertEqual(resposta.json()["admin"], "/admin/")
