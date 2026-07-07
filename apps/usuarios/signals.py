from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.shared.middleware import get_current_request_ip

from .models import Usuario


@receiver(post_save, sender=Usuario)
def auditar_creacion_usuario(sender, instance, created, **kwargs):
    if created:
        from apps.auditoria.models import AuditLog
        AuditLog.objects.create(
            evento=AuditLog.Evento.USUARIO_CREADO,
            usuario=instance,
            ip_address=get_current_request_ip(),
            datos={"usuario_id": str(instance.id), "email": instance.email, "rol": instance.rol},
            hash_previo="",
        )
