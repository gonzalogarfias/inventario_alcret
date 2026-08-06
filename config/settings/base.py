"""Settings base del proyecto Inventario Alcret.

Configuración compartida entre todos los entornos.
Los valores sensibles se leen desde variables de entorno via python-decouple.

Controles NIST implementados:
  - AC-7: django-axes (rate limiting login)
  - AC-12: SESSION_EXPIRE_AT_BROWSER_CLOSE
  - IA-5(1): Argon2PasswordHasher
  - SC-8: SESSION_COOKIE_SECURE, CSRF_COOKIE_SECURE
  - SC-23(1): CSP headers via middleware
  - SI-10: AUTH_PASSWORD_VALIDATORS
"""

from pathlib import Path

from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ============================================================================
# Seguridad básica
# ============================================================================

SECRET_KEY = config("DJANGO_SECRET_KEY")
DEBUG = config("DJANGO_DEBUG", default=False, cast=bool)

# ALLOWED_HOSTS se configura por entorno (base vacío, producción desde env)
ALLOWED_HOSTS = []

# ============================================================================
# Apps
# ============================================================================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "whitenoise.runserver_nostatic",
    # Third party
    "axes",
    "guardian",
    "rest_framework",
    # Apps propias
    "apps.usuarios",
    "apps.inventario",
    "apps.auditoria",
    "apps.metricas",
    "apps.integracion",
    "apps.alertas",
    "apps.finanzas",
    "apps.shared",
    "apps.clientes",
    "apps.cotizaciones",
]

# ============================================================================
# Middleware
# ============================================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "axes.middleware.AxesMiddleware",
    "apps.shared.middleware.SecurityHeadersMiddleware",
    "apps.shared.middleware.CurrentRequestMiddleware",
]

# ============================================================================
# URLs y Templates
# ============================================================================

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ============================================================================
# Base de datos (default: PostgreSQL, sobreescribible por entorno)
# ============================================================================

DATABASES = {
    "default": {
        "ENGINE": config("DB_ENGINE", default="django.db.backends.postgresql"),
        "NAME": config("DB_NAME", default="inventario_db"),
        "USER": config("DB_USER", default="postgres"),
        "PASSWORD": config("DB_PASSWORD", default="postgres"),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="5432"),
    }
}

# ============================================================================
# Caché (Redis)
# ============================================================================

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": config("REDIS_URL", default="redis://localhost:6379/0"),
    }
}

# ============================================================================
# Autenticación y autorización
# ============================================================================

AUTH_USER_MODEL = "usuarios.Usuario"
LOGIN_REDIRECT_URL = "dashboard"
LOGIN_URL = "login"
LOGOUT_REDIRECT_URL = "login"

# Validadores de contraseña (NIST IA-5(1))
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {"NAME": "apps.shared.validators.PwnedPasswordValidator"},
]

# Tiempo de expiración para reset de contraseña (15 minutos)
PASSWORD_RESET_TIMEOUT = 900

# Backends de autenticación
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesBackend",
    "django.contrib.auth.backends.ModelBackend",
    "guardian.backends.ObjectPermissionBackend",
]

# ============================================================================
# Internacionalización
# ============================================================================

LANGUAGE_CODE = "es"
TIME_ZONE = "America/Argentina/Buenos_Aires"  # confirmed
USE_I18N = True
USE_TZ = True

# ============================================================================
# Archivos estáticos y media
# ============================================================================

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ============================================================================
# Hashing de contraseñas (NIST IA-5(1) — Argon2)
# ============================================================================

PASSWORD_HASHERS = ["django.contrib.auth.hashers.Argon2PasswordHasher"]

# ============================================================================
# Cookies de sesión (NIST SC-8)
# ============================================================================

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = "Strict"
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

CSRF_COOKIE_HTTPONLY = True  # Frontend must use {% csrf_token %} or meta tag, not document.cookie
CSRF_COOKIE_SECURE = True

# ============================================================================
# Headers de seguridad HTTP (NIST SC-23, SC-8)
# ============================================================================

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True

# SECURE_SSL_REDIRECT y SECURE_HSTS_PRELOAD se configuran por entorno
# (producción: True, desarrollo: False)

# ============================================================================
# django-axes — Rate limiting login (NIST AC-7)
# ============================================================================

AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1  # hora
AXES_LOCKOUT_PARAMETERS = ["ip_address", "username"]
AXES_RESET_ON_SUCCESS = True

# ============================================================================
# Django REST Framework
# ============================================================================

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.AnonRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {"user": "1000/day", "anon": "100/day"},
}

# ============================================================================
# Integración CRM
# ============================================================================

CRM_WEBHOOK_URL = config("CRM_WEBHOOK_URL", default="")
CRM_HMAC_SECRET = config("CRM_HMAC_SECRET", default="")

# ============================================================================
# Celery — Tareas asíncronas
# ============================================================================

CELERY_BROKER_URL = config("CELERY_BROKER_URL", default="redis://localhost:6379/1")
CELERY_RESULT_BACKEND = config("CELERY_BROKER_URL", default="redis://localhost:6379/1")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "America/Argentina/Buenos_Aires"
CELERY_BEAT_SCHEDULE = {
    "verificar-expiracion-claves-crm": {
        "task": "apps.integracion.tasks.verificar_expiracion_claves",
        "schedule": 86400,  # cada 24 horas
    },
}

# ============================================================================
# Logging
# ============================================================================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "{levelname} {asctime} {module} {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "root": {"handlers": ["console"], "level": "WARNING"},
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "apps": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
