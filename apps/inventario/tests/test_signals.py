"""Tests de signals de inventario.

Incluye tests originales + tests de concurrencia y transacciones Fase 2.
"""

from decimal import Decimal

import pytest

from apps.auditoria.models import AuditLog
from apps.inventario.models import Movimiento, Stock


@pytest.mark.django_db
class TestMovimientoSignals:
    def test_entrada_incrementa_stock(self, producto, almacen, usuario_admin):
        Stock.objects.create(producto=producto, almacen=almacen, cantidad=Decimal("50"))
        Movimiento.objects.create(
            tipo=Movimiento.Tipo.ENTRADA,
            producto=producto,
            almacen=almacen,
            cantidad=Decimal("30"),
            realizada_por=usuario_admin,
        )
        stock = Stock.objects.get(producto=producto, almacen=almacen)
        assert stock.cantidad == Decimal("80")

    def test_salida_decrementa_stock(self, producto, almacen, usuario_admin):
        Stock.objects.create(producto=producto, almacen=almacen, cantidad=Decimal("100"))
        Movimiento.objects.create(
            tipo=Movimiento.Tipo.SALIDA,
            producto=producto,
            almacen=almacen,
            cantidad=Decimal("25"),
            realizada_por=usuario_admin,
        )
        stock = Stock.objects.get(producto=producto, almacen=almacen)
        assert stock.cantidad == Decimal("75")

    def test_ajuste_establece_stock(self, producto, almacen, usuario_admin):
        Stock.objects.create(producto=producto, almacen=almacen, cantidad=Decimal("999"))
        Movimiento.objects.create(
            tipo=Movimiento.Tipo.AJUSTE,
            producto=producto,
            almacen=almacen,
            cantidad=Decimal("200"),
            realizada_por=usuario_admin,
        )
        stock = Stock.objects.get(producto=producto, almacen=almacen)
        assert stock.cantidad == Decimal("200")

    def test_stock_se_crea_si_no_existe(self, producto, almacen, usuario_admin):
        assert not Stock.objects.filter(producto=producto, almacen=almacen).exists()
        Movimiento.objects.create(
            tipo=Movimiento.Tipo.ENTRADA,
            producto=producto,
            almacen=almacen,
            cantidad=Decimal("15"),
            realizada_por=usuario_admin,
        )
        stock = Stock.objects.get(producto=producto, almacen=almacen)
        assert stock.cantidad == Decimal("15")

    def test_movimiento_crea_auditlog(self, producto, almacen, usuario_admin):
        mov = Movimiento.objects.create(
            tipo=Movimiento.Tipo.ENTRADA,
            producto=producto,
            almacen=almacen,
            cantidad=Decimal("10"),
            costo_unitario=Decimal("50"),
            motivo="Test entrada",
            realizada_por=usuario_admin,
        )
        logs = AuditLog.objects.filter(evento=AuditLog.Evento.ENTRADA)
        assert logs.count() == 1
        log = logs.first()
        assert log.datos["movimiento_id"] == str(mov.id)
        assert log.datos["producto_sku"] == producto.sku
        assert log.datos["cantidad"] == "10"
        assert log.datos["costo_unitario"] == "50"
        assert log.datos["motivo"] == "Test entrada"
        assert log.usuario == usuario_admin
        # Fase 2: stock_resultante debe estar presente
        assert "stock_resultante" in log.datos

    def test_auditlog_evento_coincide_con_tipo(self, producto, almacen, usuario_admin):
        Stock.objects.create(producto=producto, almacen=almacen, cantidad=Decimal("100"))
        Movimiento.objects.create(
            tipo=Movimiento.Tipo.SALIDA, producto=producto, almacen=almacen,
            cantidad=1, realizada_por=usuario_admin
        )
        assert AuditLog.objects.filter(evento=AuditLog.Evento.SALIDA).count() == 1
        Movimiento.objects.create(
            tipo=Movimiento.Tipo.AJUSTE, producto=producto, almacen=almacen,
            cantidad=5, realizada_por=usuario_admin
        )
        assert AuditLog.objects.filter(evento=AuditLog.Evento.AJUSTE).count() == 1

    def test_salida_negativa_guarda_cantidad_negativa(self, producto, almacen, usuario_admin):
        """La cantidad de SALIDA se guarda como negativa."""
        Stock.objects.create(producto=producto, almacen=almacen, cantidad=100)
        mov = Movimiento.objects.create(
            tipo=Movimiento.Tipo.SALIDA,
            producto=producto,
            almacen=almacen,
            cantidad=Decimal("25"),
            realizada_por=usuario_admin,
        )
        assert mov.cantidad < 0
        stock = Stock.objects.get(producto=producto, almacen=almacen)
        assert stock.cantidad == Decimal("75")

    def test_entrada_cantidad_positiva(self, producto, almacen, usuario_admin):
        """La cantidad de ENTRADA se guarda como positiva."""
        mov = Movimiento.objects.create(
            tipo=Movimiento.Tipo.ENTRADA,
            producto=producto,
            almacen=almacen,
            cantidad=Decimal("50"),
            realizada_por=usuario_admin,
        )
        assert mov.cantidad > 0
        stock = Stock.objects.get(producto=producto, almacen=almacen)
        assert stock.cantidad == Decimal("50")

    def test_primera_entrada_define_costo_promedio(self, producto, almacen, usuario_admin):
        """Sin stock previo, la primera ENTRADA fija el costo_promedio."""
        Movimiento.objects.create(
            tipo=Movimiento.Tipo.ENTRADA,
            producto=producto,
            almacen=almacen,
            cantidad=Decimal("10"),
            costo_unitario=Decimal("50"),
            realizada_por=usuario_admin,
        )
        producto.refresh_from_db()
        assert producto.costo_promedio == Decimal("50.00")

    def test_entrada_con_costo_actualiza_promedio_ponderado(self, producto, almacen, usuario_admin):
        """Entrada con costo recalcula el promedio ponderado sobre el stock previo."""
        Stock.objects.create(producto=producto, almacen=almacen, cantidad=Decimal("100"))
        producto.costo_promedio = Decimal("10")
        producto.save()

        Movimiento.objects.create(
            tipo=Movimiento.Tipo.ENTRADA,
            producto=producto,
            almacen=almacen,
            cantidad=Decimal("50"),
            costo_unitario=Decimal("20"),
            realizada_por=usuario_admin,
        )
        producto.refresh_from_db()
        # (10*100 + 20*50) / 150 = 2000/150 = 13.333... → 13.33
        assert producto.costo_promedio == Decimal("13.33")

    def test_entrada_sin_costo_no_toca_costo_promedio(self, producto, almacen, usuario_admin):
        Stock.objects.create(producto=producto, almacen=almacen, cantidad=Decimal("100"))
        producto.costo_promedio = Decimal("10")
        producto.save()

        Movimiento.objects.create(
            tipo=Movimiento.Tipo.ENTRADA,
            producto=producto,
            almacen=almacen,
            cantidad=Decimal("30"),
            realizada_por=usuario_admin,
        )
        producto.refresh_from_db()
        assert producto.costo_promedio == Decimal("10.00")

    def test_salida_no_cambia_costo_promedio(self, producto, almacen, usuario_admin):
        Stock.objects.create(producto=producto, almacen=almacen, cantidad=Decimal("100"))
        producto.costo_promedio = Decimal("10")
        producto.save()

        Movimiento.objects.create(
            tipo=Movimiento.Tipo.SALIDA,
            producto=producto,
            almacen=almacen,
            cantidad=Decimal("25"),
            costo_unitario=Decimal("99"),
            realizada_por=usuario_admin,
        )
        producto.refresh_from_db()
        assert producto.costo_promedio == Decimal("10.00")
