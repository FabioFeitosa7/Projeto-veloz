from django.test import TestCase, override_settings


class CorsTests(TestCase):
    @override_settings(CORS_ALLOWED_ORIGINS=["http://localhost:5173"])
    def test_origem_do_react_local_e_autorizada(self):
        resposta = self.client.get(
            "/api/dashboard/",
            headers={"origin": "http://localhost:5173"},
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(
            resposta.headers["Access-Control-Allow-Origin"],
            "http://localhost:5173",
        )
        self.assertNotIn("Access-Control-Allow-Credentials", resposta.headers)

    @override_settings(CORS_ALLOWED_ORIGINS=["http://localhost:5173"])
    def test_origem_desconhecida_nao_e_autorizada(self):
        resposta = self.client.get(
            "/api/dashboard/",
            headers={"origin": "https://site-desconhecido.example"},
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertNotIn("Access-Control-Allow-Origin", resposta.headers)

    @override_settings(CORS_ALLOWED_ORIGINS=["http://localhost:5173"])
    def test_preflight_autoriza_patch_e_content_type(self):
        resposta = self.client.options(
            "/api/ingredientes/1/",
            headers={
                "origin": "http://localhost:5173",
                "access-control-request-method": "PATCH",
                "access-control-request-headers": "content-type",
            },
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(
            resposta.headers["Access-Control-Allow-Origin"],
            "http://localhost:5173",
        )
        self.assertIn("PATCH", resposta.headers["Access-Control-Allow-Methods"])
        self.assertIn(
            "content-type",
            resposta.headers["Access-Control-Allow-Headers"].lower(),
        )
