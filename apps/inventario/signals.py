"""Señales del módulo de inventario.

Correcciones aplicadas (Fase 2):
  1. Transacción atómica con select_for_update (evita race conditions)
  2. AuditLog.hash_previo calculado correctamente
  3. Uso de F() expressions para updates atómicos
  4. Logging estructurado

Contrato de eventos:
  - stock_actualizado: señal custom emitida DESPUÉS de que el stock fue
    actualizado y confirmado. Otros módulos (ej. alertas) la escuchan en
    lugar de re-agregar stock sobre post_save de Movimiento, lo que evita
    depender del orden de carga de INSTALLED_APPS y lee el valor final.
"""

import logging

from django.db import transaction
from django.db.models import F
from django.db.models.signals import post_save
from django.dispatch import Signal, receiver

from apps.shared.services import registrar_audit_log

from .models import Movimiento
from .services import actualizar_costo_promedio, get_o_crear_stock_bloqueado

logger = logging.getLogger(__name__)

# Señal custom que se dispara tras confirmar la actualización de stock.
# sender = Movimiento; kwargs: stock (Stock), movimiento (Movimiento).
stock_actualizado = Signal()


@receiver(post_save, sender=Movimiento)
def auditar_movimiento(sender, instance, created, **kwargs):
    """Signal que actualiza stock y registra auditoría tras crear un movimiento.

    Ejecuta dentro de transacción atómica con select_for_update para evitar
    race conditions cuando múltiples usuarios operan el mismo producto/almacén.
    """
    if not created:
        return

    producto = instance.producto
    almacen = instance.almacen
    cantidad = instance.cantidad
    tipo = instance.tipo

    with transaction.atomic():
        # Bloquear fila de stock para evitar race conditions
        stock, _ = get_o_crear_stock_bloqueado(producto, almacen)

        if tipo == Movimiento.Tipo.ENTRADA:
            stock.cantidad = F("cantidad") + abs(cantidad)
        elif tipo == Movimiento.Tipo.SALIDA:
            stock.cantidad = F("cantidad") - abs(cantidad)
        elif tipo == Movimiento.Tipo.AJUSTE:
            stock.cantidad = abs(cantidad)

        stock.save()
        stock.refresh_from_db()  # Necesario para leer el valor actualizado por F()

        # Costo promedio ponderado: recalcular en cada ENTRADA con costo_unitario
        if tipo == Movimiento.Tipo.ENTRADA and instance.costo_unitario:
            actualizar_costo_promedio(producto, abs(cantidad), instance.costo_unitario)

        logger.info(
            "Stock actualizado: producto=%s almacen=%s cantidad_nueva=%s tipo=%s",
            producto.sku,
            almacen.nombre,
            stock.cantidad,
            tipo,
        )

    # Avisar a otros módulos (alertas) de que el stock ya está actualizado,
    # para que lean el valor final y no dependan del orden de los receivers.
    stock_actualizado.send(sender=Movimiento, stock=stock, movimiento=instance)

    # Registrar auditoría FUERA de la transacción del stock
    # para no bloquear la tabla de auditoría en caso de error
    try:
        registrar_audit_log(
            evento=tipo,
            usuario=instance.realizada_por,
            datos={
                "movimiento_id": str(instance.id),
                "producto_id": str(producto.id),
                "producto_sku": producto.sku,
                "almacen_id": str(almacen.id),
                "cantidad": str(cantidad),
                "costo_unitario": str(instance.costo_unitario) if instance.costo_unitario else None,
                "motivo": instance.motivo,
                "stock_resultante": str(stock.cantidad),
            },
        )
    except Exception as e:
        logger.critical(
            "FALLO CRÍTICO al registrar auditoría para movimiento %s: %s",
            instance.id,
            e,
            exc_info=True,
        )
        raise
