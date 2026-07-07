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

    def test_auditlog_evento_coincide_con_tipo(self, producto, almacen, usuario_admin):
        Movimiento.objects.create(tipo=Movimiento.Tipo.SALIDA, producto=producto, almacen=almacen, cantidad=1, realizada_por=usuario_admin)
        assert AuditLog.objects.filter(evento=AuditLog.Evento.SALIDA).count() == 1
        Movimiento.objects.create(tipo=Movimiento.Tipo.AJUSTE, producto=producto, almacen=almacen, cantidad=5, realizada_por=usuario_admin)
        assert AuditLog.objects.filter(evento=AuditLog.Evento.AJUSTE).count() == 1
