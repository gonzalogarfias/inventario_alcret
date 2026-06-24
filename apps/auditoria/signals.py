from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.dispatch import receiver
from .models import AuditLog


@receiver(user_logged_in)
def registrar_login_exitoso(sender, request, user, **kwargs):
    AuditLog.objects.create(
        evento=AuditLog.Evento.LOGIN_OK,
        usuario=user,
        ip_address=request.META.get("REMOTE_ADDR", "0.0.0.0"),
        datos={"email": user.email},
        hash_previo="",
    )


@receiver(user_login_failed)
def registrar_login_fallido(sender, credentials, request, **kwargs):
    AuditLog.objects.create(
        evento=AuditLog.Evento.LOGIN_FAIL,
        usuario=None,
        ip_address=request.META.get("REMOTE_ADDR", "0.0.0.0") if request else "0.0.0.0",
        datos={"email": credentials.get("email", "desconocido")},
        hash_previo="",
    )
