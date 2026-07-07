import logging

from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.inventario.models import Movimiento, Stock

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Movimiento)
def verificar_stock_bajo(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        producto = instance.producto
        stock_total = (
            Stock.objects.filter(producto=producto).aggregate(
                total=models.Sum("cantidad")
            )["total"]
            or 0
        )
        if producto.stock_minimo > 0 and stock_total <= producto.stock_minimo:
            from .models import Alerta
            Alerta.objects.create(
                producto=producto,
                mensaje=(
                    f"Stock bajo: {producto.nombre} ({producto.sku}) — "
                    f"{stock_total} unidades (mínimo: {producto.stock_minimo})"
                ),
            )
            logger.info("Alerta creada para %s (stock: %d, mínimo: %d)", producto.sku, stock_total, producto.stock_minimo)
    except Exception as e:
        logger.warning("Error al verificar stock bajo: %s", e)
