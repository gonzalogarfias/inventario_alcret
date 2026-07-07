from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.shared.middleware import get_current_request_ip

from .models import Movimiento


@receiver(post_save, sender=Movimiento)
def auditar_movimiento(sender, instance, created, **kwargs):
    if not created:
        return
    from apps.auditoria.models import AuditLog
    from apps.inventario.models import Stock

    producto = instance.producto
    almacen = instance.almacen
    cantidad = instance.cantidad
    evento = instance.tipo

    stock, _ = Stock.objects.get_or_create(producto=producto, almacen=almacen)

    with transaction.atomic():
        if instance.tipo == Movimiento.Tipo.ENTRADA:
            stock.cantidad += cantidad
        elif instance.tipo == Movimiento.Tipo.SALIDA:
            stock.cantidad -= cantidad
        elif instance.tipo == Movimiento.Tipo.AJUSTE:
            stock.cantidad = cantidad
        stock.save()

        AuditLog.objects.create(
            evento=AuditLog.Evento(evento),
            usuario=instance.realizada_por,
            ip_address=get_current_request_ip(),
            datos={
                "movimiento_id": str(instance.id),
                "producto_id": str(producto.id),
                "producto_sku": producto.sku,
                "almacen_id": str(almacen.id),
                "cantidad": str(cantidad),
                "costo_unitario": str(instance.costo_unitario) if instance.costo_unitario else None,
                "motivo": instance.motivo,
            },
            hash_previo="",
        )
