import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.shared.middleware import get_current_request_ip

from .models import Usuario

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Usuario)
def auditar_creacion_usuario(sender, instance, created, **kwargs):
    if not created:
        return

    from apps.auditoria.models import AuditLog

    ip = get_current_request_ip() or "0.0.0.0"
    try:
        AuditLog.objects.create(
            evento=AuditLog.Evento.USUARIO_CREADO,
            usuario=instance,
            ip_address=ip,
            datos={
                "usuario_id": str(instance.id),
                "email": instance.email,
                "rol": instance.rol,
            },
            hash_previo="",
        )
    except Exception as exc:
        logger.exception("Error al auditar creación de usuario %s: %s", instance.email, exc)
