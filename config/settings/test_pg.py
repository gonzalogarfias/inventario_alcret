# ruff: noqa: F405
"""Settings para correr la suite de tests contra PostgreSQL.

Los tests por defecto corren contra SQLite (development). Este settings
permite validar la suite completa contra PostgreSQL, donde se ejercitan
de verdad los advisory locks, select_for_update y el retry por IntegrityError.

Uso:
    docker compose up -d postgres
    pytest --ds=config.settings.test_pg -q --no-header

La base y el usuario salen de variables de entorno (ver docker-compose.yml).
pytest-django crea la base de tests automáticamente; el usuario debe tener
privilegios de superusuario (el POSTGRES_USER de la imagen es superusuario).
"""

from decouple import config

from .development import *  # noqa: F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME", default="inventario"),
        "USER": config("DB_USER", default="inventario"),
        "PASSWORD": config("DB_PASSWORD", default="inventario"),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="5432"),
    }
}
