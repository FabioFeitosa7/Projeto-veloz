from config.settings import *  # noqa: F403


DATABASES = {  # noqa: F405
    "default": configurar_banco(  # noqa: F405
        base_dir=BASE_DIR,  # noqa: F405
        database_url=None,
    )
}
