from pathlib import Path

import dj_database_url


def configurar_banco(
    *,
    base_dir: Path,
    database_url: str | None,
) -> dict:
    """Seleciona SQLite local ou PostgreSQL configurado por ambiente."""
    if not database_url:
        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": base_dir / "db.sqlite3",
        }

    configuracao = dj_database_url.parse(
        database_url,
        conn_max_age=0,
        conn_health_checks=False,
    )
    if configuracao["ENGINE"] == "django.db.backends.postgresql":
        opcoes = configuracao.setdefault("OPTIONS", {})
        opcoes["sslmode"] = "require"
        opcoes["prepare_threshold"] = None
    return configuracao
