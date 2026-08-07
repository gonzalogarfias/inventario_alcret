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
        unidad = instance.unidad_interes
        enviar_evento_crm.delay(
            evento="cotizacion.creada",
            payload={
                "cotizacion_id": str(instance.id),
                "folio": instance.folio,
                "cliente_id": str(instance.cliente.id),
                "cliente_email": instance.cliente.email,
                "cliente_nombre": instance.cliente.nombre,
                "cliente_empresa": instance.cliente.empresa,
                "monto": f"{instance.monto:.2f}",
                "esquema": instance.esquema,
                "estado": instance.estado,
                "observaciones": instance.observaciones,
                "unidad_interes_id": str(unidad.id),
                "unidad_interes_sku": unidad.sku,
                "unidad_interes_vin": unidad.vin or None,
                "unidad_interes": unidad.vin or unidad.sku,
                "unidad_interes_nombre": unidad.nombre,
                "vendedor_id": str(instance.vendedor_id),
                "vendedor_email": instance.vendedor.email,
                "vendedor_nombre": instance.vendedor.nombre,
                "created_at": instance.created_at.isoformat(),
                "updated_at": instance.updated_at.isoformat(),
            },
        )
    except Exception as e:
        logger.warning("No se pudo encolar tarea CRM de cotización: %s", e)
