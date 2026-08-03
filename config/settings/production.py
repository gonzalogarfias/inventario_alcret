# ruff: noqa: F405
"""Settings para entorno de producción.

Seguridad máxima. Requiere variables de entorno configuradas.
"""

from .base import *  # noqa: F403

DEBUG = False

# ALLOWED_HOSTS obligatorio en producción (no permitir '*')
allowed_hosts_env = config("ALLOWED_HOSTS", default="")
ALLOWED_HOSTS = [h.strip() for h in allowed_hosts_env.split(",") if h.strip()]
if not ALLOWED_HOSTS:
    raise ValueError(
        "ALLOWED_HOSTS no puede estar vacío en producción. "
        "Configura la variable de entorno ALLOWED_HOSTS."
    )

# CSRF trusted origins para protección contra CSRF cross-origin
csrf_origins_env = config("CSRF_TRUSTED_ORIGINS", default="")
CSRF_TRUSTED_ORIGINS = [o.strip() for o in csrf_origins_env.split(",") if o.strip()]

# ============================================================================
# Seguridad HTTPS (NIST SC-8)
# ============================================================================

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Redirección forzada HTTP → HTTPS
SECURE_SSL_REDIRECT = True

# HSTS (HTTP Strict Transport Security)
SECURE_HSTS_SECONDS = 31536000  # 1 año
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Header para detectar HTTPS detrás de proxy reverso (Nginx, ALB, etc.)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ============================================================================
# Logging en producción
# ============================================================================

LOGGING["root"]["level"] = "WARNING"
LOGGING["loggers"]["apps"]["level"] = "INFO"

# ============================================================================
# Archivos estáticos
# ============================================================================

STATIC_ROOT = BASE_DIR / "staticfiles"
