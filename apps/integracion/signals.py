import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.auditoria.models import AuditLog
from apps.inventario.models import Movimiento

from .models import ClaveCRM
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


@receiver(post_save, sender=ClaveCRM)
def registrar_rotacion_clave_crm(sender, instance, created, **kwargs):
    if not created:
        return
    from apps.shared.middleware import get_current_request_ip
    AuditLog.objects.create(
        evento=AuditLog.Evento.SYNC_CRM,
        usuario=None,
        ip_address=get_current_request_ip(),
        datos={
            "accion": "ROTACION_CLAVE_CRM",
            "clave_publica": instance.clave_publica,
            "expira_en": str(instance.expira_en),
            "activa": instance.activa,
        },
    )
