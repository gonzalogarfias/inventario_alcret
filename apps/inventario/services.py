from django.db import models

from .models import Movimiento, Stock


def registrar_movimiento(tipo, producto, almacen, cantidad, realizada_por, costo_unitario=None, motivo=""):
    if cantidad <= 0:
        raise ValueError("La cantidad debe ser un valor positivo.")

    cantidad_movimiento = -cantidad if tipo == Movimiento.Tipo.SALIDA else cantidad

    movimiento = Movimiento.objects.create(
        tipo=tipo,
        producto=producto,
        almacen=almacen,
        cantidad=cantidad_movimiento,
        costo_unitario=costo_unitario,
        motivo=motivo,
        realizada_por=realizada_por,
    )
    return movimiento


def stock_bajo_minimo(producto):
    total = (
        Stock.objects.filter(producto=producto).aggregate(total=models.Sum("cantidad"))["total"]
        or 0
    )
    return producto.stock_minimo > 0 and total <= producto.stock_minimo
