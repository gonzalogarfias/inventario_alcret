from decimal import Decimal

import pytest

from apps.finanzas.models import Factura


@pytest.mark.django_db
class TestFacturaModel:
    def test_crear_factura_compra(self, usuario_admin, movimiento):
        f = Factura.objects.create(
            tipo=Factura.Tipo.COMPRA,
            numero="FACT-001",
            proveedor_cliente="Proveedor SA",
            monto=Decimal("1500.00"),
            fecha="2026-07-01",
            archivo="facturas/compra/test.pdf",
            movimiento=movimiento,
            subido_por=usuario_admin,
        )
        assert f.pk is not None
        assert str(f) == "Compra FACT-001 — $1500.00"
        assert f.movimiento == movimiento

    def test_crear_factura_venta(self, usuario_admin, producto, almacen):
        from apps.inventario.models import Movimiento, Stock
        Stock.objects.create(producto=producto, almacen=almacen, cantidad=Decimal("100"))
        mov = Movimiento.objects.create(
            tipo=Movimiento.Tipo.SALIDA,
            producto=producto,
            almacen=almacen,
            cantidad=10,
            realizada_por=usuario_admin,
        )
        f = Factura.objects.create(
            tipo=Factura.Tipo.VENTA,
            numero="FV-001",
            proveedor_cliente="Cliente X",
            monto=Decimal("2500.00"),
            fecha="2026-07-15",
            archivo="facturas/venta/fact.pdf",
            movimiento=mov,
            subido_por=usuario_admin,
        )
        assert f.get_tipo_display() == "Venta"
        assert f.monto == Decimal("2500.00")

    def test_monto_minimo(self, usuario_admin):
        from django.core.exceptions import ValidationError
        f = Factura(
            tipo=Factura.Tipo.COMPRA,
            monto=Decimal("0"),
            fecha="2026-07-01",
            archivo="test.pdf",
            subido_por=usuario_admin,
        )
        with pytest.raises(ValidationError):
            f.full_clean()

    def test_ordering(self, usuario_admin):
        Factura.objects.create(
            tipo=Factura.Tipo.COMPRA, monto=100, fecha="2026-07-20",
            archivo="a.pdf", subido_por=usuario_admin,
        )
        Factura.objects.create(
            tipo=Factura.Tipo.VENTA, monto=200, fecha="2026-07-10",
            archivo="b.pdf", subido_por=usuario_admin,
        )
        qs = Factura.objects.all()
        assert qs[0].fecha > qs[1].fecha or (qs[0].fecha == qs[1].fecha)
