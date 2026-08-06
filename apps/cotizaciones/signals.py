import logging

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.integracion.tasks import enviar_evento_crm

from .models import Cotizacion

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Cotizacion)
def publicar_cotizacion_al_crm(sender, instance, created, **kwargs):
    if not settings.CRM_WEBHOOK_URL:
        logger.debug("CRM_WEBHOOK_URL no configurado, skipping CRM task")
        return
    try:
        enviar_evento_crm.delay(
            evento="cotizacion.creada",
            payload={
                "cliente_email": instance.cliente.email,
                "monto": f"{instance.monto:.2f}",
                "esquema": instance.esquema,
                "unidad_interes": instance.unidad_interes.vin or instance.unidad_interes.sku,
                "vendedor_email": instance.vendedor.email,
            },
        )
    except Exception as e:
        logger.warning("No se pudo encolar tarea CRM de cotización: %s", e)
