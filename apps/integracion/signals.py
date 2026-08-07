import logging
from decimal import Decimal

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.auditoria.models import AuditLog
from apps.inventario.models import Movimiento

from .models import ClaveCRM
from .tasks import enviar_evento_crm

logger = logging.getLogger(__name__)


def _fmt_decimal(valor):
    if valor is None:
        return None
    d = Decimal(str(valor))
    return f"{d.normalize():f}" if d else "0"


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
        cantidad_disponible = stock.cantidad if stock else None
        realizada_por = instance.realizada_por
        enviar_evento_crm.delay(
            evento="stock.actualizado",
            payload={
                "movimiento_id": str(instance.id),
                "almacen_id": str(instance.almacen_id),
                "almacen_codigo": instance.almacen.nombre,
                "almacen_nombre": instance.almacen.nombre,
                "almacen_ubicacion": instance.almacen.ubicacion,
                "producto_id": str(producto.id),
                "producto_sku": producto.sku,
                "producto_vin": producto.vin or None,
                "sku_o_vin": producto.vin or producto.sku,
                "nombre_unidad": producto.nombre,
                "cantidad_disponible": _fmt_decimal(cantidad_disponible),
                "cantidad_movimiento": _fmt_decimal(instance.cantidad),
                "tipo_movimiento": instance.tipo,
                "motivo": instance.motivo,
                "costo_unitario": _fmt_decimal(instance.costo_unitario),
                "realizada_por_email": realizada_por.email if realizada_por else None,
                "realizada_por_nombre": realizada_por.nombre if realizada_por else None,
                "fecha_movimiento": instance.created_at.isoformat(),
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
