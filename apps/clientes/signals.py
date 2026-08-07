import logging

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.integracion.tasks import enviar_evento_crm

from .models import Cliente

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Cliente)
def publicar_cliente_al_crm(sender, instance, created, **kwargs):
    if not settings.CRM_WEBHOOK_URL:
        logger.debug("CRM_WEBHOOK_URL no configurado, skipping CRM task")
        return
    try:
        enviar_evento_crm.delay(
            evento="cliente.creado" if created else "cliente.actualizado",
            payload={
                "cliente_id": str(instance.id),
                "empresa": instance.empresa,
                "nombre": instance.nombre,
                "email": instance.email,
                "telefono": instance.telefono,
                "rfc": instance.rfc,
                "activo": instance.activo,
                "created_at": instance.created_at.isoformat(),
                "updated_at": instance.updated_at.isoformat(),
            },
        )
    except Exception as e:
        logger.warning("No se pudo encolar tarea CRM de cliente: %s", e)
