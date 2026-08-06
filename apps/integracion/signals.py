import logging

from django.conf import settings
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
    if not settings.CRM_WEBHOOK_URL:
        logger.debug("CRM_WEBHOOK_URL no configurado, skipping CRM task")
        return
    try:
        producto = instance.producto
        stock = (
            producto.stocks.filter(almacen=instance.almacen).first()
        )
        cantidad_disponible = stock.cantidad if stock else 0
        cantidad_str = f"{cantidad_disponible.normalize():f}" if cantidad_disponible else "0"
        enviar_evento_crm.delay(
            evento="stock.actualizado",
            payload={
                "almacen_id": str(instance.almacen_id),
                "producto_id": str(producto.id),
                "sku_o_vin": producto.vin or producto.sku,
                "nombre_unidad": producto.nombre,
                "cantidad_disponible": cantidad_str,
                "tipo_movimiento": instance.tipo,
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
