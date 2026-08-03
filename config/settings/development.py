# ruff: noqa: F405
"""Settings para entorno de desarrollo local.

Seguridad relajada para facilitar desarrollo. NUNCA usar en producción.
"""

from .base import *  # noqa: F403

DEBUG = True

# Hosts permitidos en desarrollo (relajado para conveniencia)
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]

# Cookies sin HTTPS en desarrollo local
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Sin HSTS en desarrollo
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False

# Sin redirección forzada a HTTPS
SECURE_SSL_REDIRECT = False

# Base de datos SQLite para desarrollo rápido
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Caché local en memoria para desarrollo (no requiere Redis)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# Apps de desarrollo
INSTALLED_APPS += ["django_extensions"]  # noqa: F405

# Celery en modo eager (síncrono) para tests y desarrollo
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Logging más verboso en desarrollo
LOGGING["root"]["level"] = "DEBUG"
LOGGING["loggers"]["apps"]["level"] = "DEBUG"
