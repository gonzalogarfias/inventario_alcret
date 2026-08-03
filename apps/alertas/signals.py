import logging

from django.dispatch import receiver

from apps.inventario.signals import stock_actualizado

logger = logging.getLogger(__name__)


@receiver(stock_actualizado)
def verificar_stock_bajo(sender, stock, movimiento, **kwargs):
    """Crea una alerta si el stock quedó igual o por debajo del mínimo.

    Escucha la señal custom `stock_actualizado` de inventario (emitida
    después de confirmar la actualización), por lo que lee el valor final
    de `stock.cantidad` sin re-agregar y sin depender del orden de carga
    de INSTALLED_APPS.
    """
    try:
        producto = stock.producto
        stock_total = stock.cantidad
        if producto.stock_minimo > 0 and stock_total <= producto.stock_minimo:
            from .models import Alerta

            Alerta.objects.create(
                producto=producto,
                mensaje=(
                    f"Stock bajo: {producto.nombre} ({producto.sku}) — "
                    f"{stock_total} unidades (mínimo: {producto.stock_minimo})"
                ),
            )
            logger.info(
                "Alerta creada para %s (stock: %d, mínimo: %d)",
                producto.sku,
                stock_total,
                producto.stock_minimo,
            )
    except Exception as e:
        logger.warning("Error al verificar stock bajo: %s", e)
