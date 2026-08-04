# ruff: noqa: F405
"""Settings para despliegue en AWS EC2 con Nginx.

Hereda de producción con ajustes específicos para EC2:
  - DATABASE_URL para RDS/Aurora
  - SECURE_SSL_REDIRECT deshabilitado (Nginx maneja SSL termination)
  - CSRF_COOKIE_SECURE/SESSION_COOKIE_SECURE deshabilitados
    (si Nginx no envía headers correctos o se usa HTTP interno)

IMPORTANTE: Si Nginx está configurado con proxy_pass a HTTP,
asegurar que pase el header X-Forwarded-Proto: https.
"""

import dj_database_url

from .production import *  # noqa: F403

DEBUG = False

# Hosts desde variable de entorno
allowed_hosts_env = config("ALLOWED_HOSTS", default="")
ALLOWED_HOSTS = [h.strip() for h in allowed_hosts_env.split(",") if h.strip()]

# CSRF trusted origins
csrf_origins_env = config("CSRF_TRUSTED_ORIGINS", default="")
CSRF_TRUSTED_ORIGINS = [o.strip() for o in csrf_origins_env.split(",") if o.strip()]

# ============================================================================
# SSL / HTTPS
# ============================================================================

# Deshabilitado temporalmente: despliegue HTTP-only en la capa gratuita de EC2.
# Rehabilitar (True) cuando se active HTTPS con dominio y certificados.
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# ============================================================================
# Base de datos (RDS/Aurora via DATABASE_URL)
# ============================================================================

db_url = config("DATABASE_URL", default=None)
if db_url:
    DATABASES = {"default": dj_database_url.parse(db_url, conn_max_age=600)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": config("DB_NAME"),
            "USER": config("DB_USER"),
            "PASSWORD": config("DB_PASSWORD"),
            "HOST": config("DB_HOST"),
            "PORT": config("DB_PORT", default="5432"),
            "CONN_MAX_AGE": 600,
        }
    }

# ============================================================================
# Archivos estáticos
# ============================================================================

STATIC_ROOT = BASE_DIR / "staticfiles"
