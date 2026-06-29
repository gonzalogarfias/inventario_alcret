from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView
from apps.shared.middleware import get_current_request_ip
from .models import AuditLog


class AuditPasswordResetView(PasswordResetView):
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
