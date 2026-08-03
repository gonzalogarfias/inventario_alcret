"""Vistas de autenticación con auditoría integrada.

Correcciones Fase 4:
  1. Usa registrar_audit_log() en lugar de crear directamente
  2. Manejo de errores con logging
  3. IP real via get_current_request_ip()
"""

import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.views import PasswordResetConfirmView, PasswordResetView

from apps.shared.middleware import get_current_request_ip, invalidar_sesiones_usuario
from apps.shared.services import registrar_audit_log

Usuario = get_user_model()
logger = logging.getLogger(__name__)


class AuditPasswordResetForm(PasswordResetForm):
    """Formulario de reset de contraseña que solo permite usuarios activos."""

    def get_users(self, email):
        active_users = Usuario._default_manager.filter(
            email__iexact=email, activo=True,
        )
        return (u for u in active_users if u.has_usable_password())


class AuditPasswordResetView(PasswordResetView):
    """Vista de solicitud de reset de contraseña con auditoría."""

    form_class = AuditPasswordResetForm

    def form_valid(self, form):
        email = form.cleaned_data["email"]
        try:
            registrar_audit_log(
                evento="PASSWORD_RESET",
                usuario=None,
                ip_address=get_current_request_ip(),
                datos={"email": email, "accion": "PASSWORD_RESET_REQUESTED"},
            )
            logger.info("Solicitud de reset de contraseña: %s", email)
        except Exception as e:
            logger.critical(
                "FALLO al registrar solicitud de reset: %s", e, exc_info=True
            )
        return super().form_valid(form)


class AuditPasswordResetConfirmView(PasswordResetConfirmView):
    """Vista de confirmación de reset de contraseña con auditoría."""

    def form_valid(self, form):
        # Invalidar sesiones activas del usuario (NIST AC-12)
        try:
            invalidar_sesiones_usuario(self.user.id)
            logger.info("Sesiones invalidadas para usuario %s", self.user.email)
        except Exception as e:
            logger.error(
                "Error al invalidar sesiones de %s: %s", self.user.email, e
            )

        response = super().form_valid(form)

        try:
            registrar_audit_log(
                evento="PASSWORD_RESET",
                usuario=self.user,
                ip_address=get_current_request_ip(),
                datos={
                    "email": self.user.email,
                    "accion": "PASSWORD_RESET_COMPLETED",
                },
            )
            logger.info("Reset de contraseña completado: %s", self.user.email)
        except Exception as e:
            logger.critical(
                "FALLO al registrar reset completado: %s", e, exc_info=True
            )

        return response
