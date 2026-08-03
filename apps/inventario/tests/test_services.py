"""Tests de servicios de inventario.

Incluye tests originales + tests de validación Fase 2.
"""

from decimal import Decimal

import pytest

from apps.inventario.models import Movimiento, Stock
from apps.inventario.services import registrar_movimiento, stock_bajo_minimo
from apps.shared.value_objects import ValidationError


@pytest.mark.django_db
class TestRegistrarMovimiento:
    def test_registra_entrada(self, producto, almacen, usuario_admin):
        mov = registrar_movimiento(
            tipo=Movimiento.Tipo.ENTRADA,
            producto=producto,
            almacen=almacen,
            cantidad=10,
            realizada_por=usuario_admin,
        )
        assert mov.pk is not None
        assert mov.tipo == Movimiento.Tipo.ENTRADA
        assert mov.cantidad == 10

    def test_registra_salida_convierte_a_negativo(self, producto, almacen, usuario_admin):
        Stock.objects.create(producto=producto, almacen=almacen, cantidad=100)
        mov = registrar_movimiento(
            tipo=Movimiento.Tipo.SALIDA,
            producto=producto,
            almacen=almacen,
            cantidad=5,
            realizada_por=usuario_admin,
        )
        assert mov.cantidad == -5

    def test_registra_ajuste_mantiene_signo(self, producto, almacen, usuario_admin):
        mov = registrar_movimiento(
            tipo=Movimiento.Tipo.AJUSTE,
            producto=producto,
            almacen=almacen,
            cantidad=3,
            realizada_por=usuario_admin,
        )
        assert mov.cantidad == 3

    def test_cantidad_cero_lanza_error(self, producto, almacen, usuario_admin):
        with pytest.raises(ValidationError, match="positivo"):
            registrar_movimiento(
                tipo=Movimiento.Tipo.ENTRADA,
                producto=producto,
                almacen=almacen,
                cantidad=0,
                realizada_por=usuario_admin,
            )

    def test_cantidad_negativa_lanza_error(self, producto, almacen, usuario_admin):
        with pytest.raises(ValidationError, match="positivo"):
            registrar_movimiento(
                tipo=Movimiento.Tipo.ENTRADA,
                producto=producto,
                almacen=almacen,
                cantidad=-5,
                realizada_por=usuario_admin,
            )

    def test_salida_sin_stock_lanza_error(self, producto, almacen, usuario_admin):
        """SALIDA sin stock debe lanzar ValidationError."""
        with pytest.raises(ValidationError, match="insuficiente"):
            registrar_movimiento(
                tipo=Movimiento.Tipo.SALIDA,
                producto=producto,
                almacen=almacen,
                cantidad=10,
                realizada_por=usuario_admin,
            )

    def test_salida_stock_insuficiente_lanza_error(self, producto, almacen, usuario_admin):
        """SALIDA con stock insuficiente debe lanzar ValidationError."""
        Stock.objects.create(producto=producto, almacen=almacen, cantidad=5)
        with pytest.raises(ValidationError, match="insuficiente"):
            registrar_movimiento(
                tipo=Movimiento.Tipo.SALIDA,
                producto=producto,
                almacen=almacen,
                cantidad=10,
                realizada_por=usuario_admin,
            )

    def test_salida_con_stock_suficiente_ok(self, producto, almacen, usuario_admin):
        """SALIDA con stock suficiente debe funcionar."""
        Stock.objects.create(producto=producto, almacen=almacen, cantidad=100)
        mov = registrar_movimiento(
            tipo=Movimiento.Tipo.SALIDA,
            producto=producto,
            almacen=almacen,
            cantidad=25,
            realizada_por=usuario_admin,
        )
        assert mov.cantidad == -25
        stock = Stock.objects.get(producto=producto, almacen=almacen)
        assert stock.cantidad == Decimal("75")

    def test_entrada_actualiza_stock(self, producto, almacen, usuario_admin):
        """ENTRADA incrementa el stock."""
        Stock.objects.create(producto=producto, almacen=almacen, cantidad=50)
        registrar_movimiento(
            tipo=Movimiento.Tipo.ENTRADA,
            producto=producto,
            almacen=almacen,
            cantidad=30,
            realizada_por=usuario_admin,
        )
        stock = Stock.objects.get(producto=producto, almacen=almacen)
        assert stock.cantidad == Decimal("80")

    def test_ajuste_establece_stock(self, producto, almacen, usuario_admin):
        """AJUSTE establece el stock al valor exacto."""
        Stock.objects.create(producto=producto, almacen=almacen, cantidad=999)
        registrar_movimiento(
            tipo=Movimiento.Tipo.AJUSTE,
            producto=producto,
            almacen=almacen,
            cantidad=200,
            realizada_por=usuario_admin,
        )
        stock = Stock.objects.get(producto=producto, almacen=almacen)
        assert stock.cantidad == Decimal("200")


@pytest.mark.django_db
class TestStockBajoMinimo:
    def test_stock_bajo_minimo_true(self, producto, almacen):
        producto.stock_minimo = Decimal("10")
        producto.save()
        Stock.objects.create(producto=producto, almacen=almacen, cantidad=Decimal("5"))
        assert stock_bajo_minimo(producto) is True

    def test_stock_bajo_minimo_false(self, producto, almacen):
        producto.stock_minimo = Decimal("10")
        producto.save()
        Stock.objects.create(producto=producto, almacen=almacen, cantidad=Decimal("20"))
        assert stock_bajo_minimo(producto) is False

    def test_stock_minimo_cero_no_alerta(self, producto, almacen):
        producto.stock_minimo = Decimal("0")
        producto.save()
        Stock.objects.create(producto=producto, almacen=almacen, cantidad=Decimal("0"))
        assert stock_bajo_minimo(producto) is False
