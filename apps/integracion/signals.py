import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.inventario.models import Movimiento
from .tasks import enviar_evento_crm

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Movimiento)
def publicar_movimiento_al_crm(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        enviar_evento_crm.delay(
            evento="stock.actualizado",
            payload={
                "producto_id": str(instance.producto_id),
                "cantidad": str(instance.cantidad),
                "tipo": instance.tipo,
                "almacen_id": str(instance.almacen_id),
            },
        )
    except Exception as e:
        logger.warning("No se pudo encolar tarea CRM: %s", e)
