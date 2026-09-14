from pathlib import Path

from django.test import SimpleTestCase

from config.database import configurar_banco


class ConfiguracaoBancoTests(SimpleTestCase):
    def test_sem_url_usa_sqlite_local(self):
        base_dir = Path("/projeto")

        configuracao = configurar_banco(
            base_dir=base_dir,
            database_url=None,
        )

        self.assertEqual(configuracao["ENGINE"], "django.db.backends.sqlite3")
        self.assertEqual(configuracao["NAME"], base_dir / "db.sqlite3")

    def test_url_postgresql_configura_conexao_serverless_segura(self):
        configuracao = configurar_banco(
            base_dir=Path("/projeto"),
            database_url=(
                "postgresql://usuario:senha@pooler.example.com:6543/postgres"
            ),
        )

        self.assertEqual(configuracao["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(configuracao["HOST"], "pooler.example.com")
        self.assertEqual(configuracao["PORT"], 6543)
        self.assertEqual(configuracao["CONN_MAX_AGE"], 0)
        self.assertFalse(configuracao["CONN_HEALTH_CHECKS"])
        self.assertEqual(configuracao["OPTIONS"]["sslmode"], "require")
        self.assertIsNone(configuracao["OPTIONS"]["prepare_threshold"])
