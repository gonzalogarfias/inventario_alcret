from django.db import transaction

from apps.auditoria.models import AuditLog
from apps.shared.middleware import get_current_request_ip


def ejecutar_en_transaccion(func, *args, **kwargs):
    with transaction.atomic():
        return func(*args, **kwargs)


def registrar_audit_log(evento, usuario, ip_address=None, datos=None):
    return AuditLog.objects.create(
        evento=evento,
        usuario=usuario,
        ip_address=ip_address or get_current_request_ip(),
        datos=datos or {},
    )
