from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.views import PasswordResetConfirmView, PasswordResetView

from apps.shared.middleware import get_current_request_ip, invalidar_sesiones_usuario

from .models import AuditLog

Usuario = get_user_model()


class AuditPasswordResetForm(PasswordResetForm):
    def get_users(self, email):
        active_users = Usuario._default_manager.filter(
            email__iexact=email, activo=True,
        )
        return (u for u in active_users if u.has_usable_password())


class AuditPasswordResetView(PasswordResetView):
    form_class = AuditPasswordResetForm

    def form_valid(self, form):
        email = form.cleaned_data["email"]
        AuditLog.objects.create(
            evento=AuditLog.Evento.PASSWORD_RESET,
            usuario=None,
            ip_address=get_current_request_ip(),
            datos={"email": email, "accion": "PASSWORD_RESET_REQUESTED"},
            hash_previo="",
        )
        return super().form_valid(form)


class AuditPasswordResetConfirmView(PasswordResetConfirmView):
    def form_valid(self, form):
        invalidar_sesiones_usuario(self.user.id)
        response = super().form_valid(form)
        user = self.user
        AuditLog.objects.create(
            evento=AuditLog.Evento.PASSWORD_RESET,
            usuario=user,
            ip_address=get_current_request_ip(),
            datos={"email": user.email, "accion": "PASSWORD_RESET_COMPLETED"},
            hash_previo="",
        )
        return response
