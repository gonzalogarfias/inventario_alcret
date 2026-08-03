"""Señales de auditoría para eventos de autenticación.

Correcciones Fase 4:
  1. Usa get_current_request_ip() para obtener IP real (incluye X-Forwarded-For)
  2. Logging estructurado
  3. Manejo de errores silencioso (no falla el login si auditoría falla)
"""

import logging

from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.dispatch import receiver

from apps.shared.middleware import get_current_request_ip
from apps.shared.services import registrar_audit_log

logger = logging.getLogger(__name__)


@receiver(user_logged_in)
def registrar_login_exitoso(sender, request, user, **kwargs):
    """Registra login exitoso en auditoría."""
    try:
        registrar_audit_log(
            evento="LOGIN_OK",
            usuario=user,
            ip_address=get_current_request_ip(),
            datos={"email": user.email, "metodo": "password"},
        )
        logger.info("Login exitoso registrado: %s", user.email)
    except Exception as e:
        logger.critical("FALLO al registrar login exitoso: %s", e, exc_info=True)


@receiver(user_login_failed)
def registrar_login_fallido(sender, credentials, request, **kwargs):
    """Registra intento de login fallido en auditoría."""
    try:
        email = credentials.get("email", "desconocido") if credentials else "desconocido"
        registrar_audit_log(
            evento="LOGIN_FAIL",
            usuario=None,
            ip_address=get_current_request_ip(),
            datos={"email": email, "motivo": "credenciales_invalidas"},
        )
        logger.warning("Login fallido registrado: %s", email)
    except Exception as e:
        logger.critical("FALLO al registrar login fallido: %s", e, exc_info=True)
