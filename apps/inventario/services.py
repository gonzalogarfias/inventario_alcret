"""Servicios de negocio del módulo de inventario.

Correcciones aplicadas (Fase 2):
  1. Transacciones atómicas con select_for_update
  2. Validación de stock suficiente antes de SALIDA
  3. Uso de Value Objects
  4. Logging estructurado
"""

import logging
from decimal import Decimal

from django.db import IntegrityError, transaction

from apps.shared.value_objects import CantidadStock, ValidationError

from .models import Movimiento, Stock

logger = logging.getLogger(__name__)


def get_o_crear_stock_bloqueado(producto, almacen):
    """Obtiene (con lock) o crea la fila de stock para producto+almacén.

    Usa select_for_update y reintenta ante IntegrityError: en Postgres,
    dos transacciones concurrentes pueden intentar INSERTAR la misma fila
    nueva (producto+almacén no existente); el patrón oficial de Django es
    reintentar el get_or_create tras la excepción de integridad.
    """
    for _ in range(2):
        try:
            return Stock.objects.select_for_update().get_or_create(
                producto=producto,
                almacen=almacen,
            )
        except IntegrityError:
            continue
    raise IntegrityError(
        f"No se pudo obtener/crear el stock para producto={producto.pk} almacen={almacen.pk}"
    )


def registrar_movimiento(
    tipo,
    producto,
    almacen,
    cantidad,
    realizada_por,
    costo_unitario=None,
    motivo="",
):
    """Registra un movimiento de inventario con transacción atómica.

    Args:
        tipo: Movimiento.Tipo.ENTRADA, SALIDA o AJUSTE
        producto: Instancia de Producto
        almacen: Instancia de Almacen
        cantidad: Cantidad positiva (Decimal o compatible)
        realizada_por: Instancia de Usuario
        costo_unitario: Decimal opcional
        motivo: String opcional

    Returns:
        Instancia de Movimiento creada

    Raises:
        ValidationError: Si cantidad <= 0 o stock insuficiente para SALIDA
        Stock.DoesNotExist: Si no hay stock y se intenta SALIDA
    """
    try:
        cantidad_vo = CantidadStock.de_string(str(cantidad))
    except ValidationError as e:
        msg = str(e)
        if ">=" in msg:
            raise ValidationError("La cantidad debe ser un valor positivo.")
        raise ValidationError(f"Cantidad inválida: {e}")

    cantidad_abs = abs(cantidad_vo.valor)

    if cantidad_abs == 0:
        raise ValidationError("La cantidad debe ser un valor positivo.")

    with transaction.atomic():
        stock, _ = get_o_crear_stock_bloqueado(producto, almacen)

        if tipo == Movimiento.Tipo.SALIDA and stock.cantidad < cantidad_abs:
            raise ValidationError(
                    f"Stock insuficiente. Disponible: {stock.cantidad}, Solicitado: {cantidad_abs}"
                )

        cantidad_movimiento = -cantidad_abs if tipo == Movimiento.Tipo.SALIDA else cantidad_abs
        movimiento = Movimiento.objects.create(
            tipo=tipo,
            producto=producto,
            almacen=almacen,
            cantidad=cantidad_movimiento,
            costo_unitario=costo_unitario,
            motivo=motivo,
            realizada_por=realizada_por,
        )

        logger.info(
            "Movimiento registrado via servicio: tipo=%s producto=%s cantidad=%s por %s",
            tipo,
            producto.sku,
            cantidad_movimiento,
            realizada_por.email,
        )

        return movimiento


def actualizar_costo_promedio(producto, cantidad, costo_unitario):
    """Actualiza el costo promedio ponderado de un producto tras una ENTRADA.

    Fórmula: (costo_anterior * stock_anterior + costo_nuevo * cantidad) / stock_nuevo

    Si no había stock previo, el nuevo costo pasa a ser el costo_unitario
    de la entrada (no se puede promediar contra stock inexistente).

    Args:
        producto: Instancia de Producto cuyo costo_promedio se actualiza.
        cantidad: Cantidad entrante (positiva, unidades).
        costo_unitario: Costo unitario de la entrada (Decimal).

    Returns:
        Decimal con el nuevo costo promedio (redondeado a 2 decimales).
    """
    from django.db.models import Sum

    stock_total = (
        Stock.objects.filter(producto=producto).aggregate(total=Sum("cantidad"))["total"]
        or 0
    )
    stock_anterior = stock_total - cantidad
    anterior = producto.costo_promedio or 0

    if stock_anterior <= 0:
        nuevo = costo_unitario
    else:
        nuevo = (anterior * stock_anterior + costo_unitario * cantidad) / stock_total

    nuevo = Decimal(nuevo).quantize(Decimal("0.01"))
    producto.costo_promedio = nuevo
    producto.save(update_fields=["costo_promedio"])
    logger.info(
        "Costo promedio actualizado: producto=%s nuevo=%s", producto.sku, nuevo
    )
    return nuevo


def stock_bajo_minimo(producto):
    """Verifica si el stock total de un producto está por debajo del mínimo.

    Args:
        producto: Instancia de Producto

    Returns:
        True si stock_total <= stock_minimo y stock_minimo > 0
    """
    from django.db.models import Sum
    total = (
        Stock.objects.filter(producto=producto)
        .aggregate(total=Sum("cantidad"))["total"]
        or 0
    )
    return producto.stock_minimo > 0 and total <= producto.stock_minimo
