
import pytest

from apps.alertas.models import Alerta
from apps.inventario.models import Movimiento


@pytest.mark.django_db
class TestAlertaSignals:
    def test_movimiento_crea_alerta_si_stock_bajo(self, producto, almacen, usuario_admin):
        # Crear stock inicial bajo
        from apps.inventario.models import Stock
        Stock.objects.create(producto=producto, almacen=almacen, cantidad=3)
        producto.stock_minimo = 5
        producto.save()

        # Realizar salida que deje stock < mínimo
        Movimiento.objects.create(
            tipo=Movimiento.Tipo.SALIDA,
            producto=producto,
            almacen=almacen,
            cantidad=1,
            realizada_por=usuario_admin,
        )

        assert Alerta.objects.filter(producto=producto, estado=Alerta.Estado.PENDIENTE).exists()

    def test_movimiento_no_crea_alerta_si_stock_ok(self, producto, almacen, usuario_admin):
        from apps.inventario.models import Stock
        Stock.objects.create(producto=producto, almacen=almacen, cantidad=100)
        producto.stock_minimo = 5
        producto.save()

        Movimiento.objects.create(
            tipo=Movimiento.Tipo.SALIDA,
            producto=producto,
            almacen=almacen,
            cantidad=10,
            realizada_por=usuario_admin,
        )

        assert not Alerta.objects.filter(producto=producto).exists()
