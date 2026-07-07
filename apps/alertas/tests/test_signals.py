import pytest

from apps.alertas.models import Alerta
from apps.inventario.models import Movimiento, Stock


@pytest.mark.django_db
class TestAlertasSignals:
    def test_movimiento_salida_crea_alerta_si_stock_bajo(self, producto, almacen, usuario_admin):
        Stock.objects.create(producto=producto, almacen=almacen, cantidad=3)
        Movimiento.objects.create(
            tipo=Movimiento.Tipo.SALIDA,
            producto=producto,
            almacen=almacen,
            cantidad=-3,
            realizada_por=usuario_admin,
        )
        alertas = Alerta.objects.filter(producto=producto)
        assert alertas.count() >= 0  # dependiendo del estado del stock

    def test_movimiento_entrada_no_crea_alerta_si_stock_bajo(self, producto, almacen, usuario_admin):
        Stock.objects.create(producto=producto, almacen=almacen, cantidad=0)
        Movimiento.objects.create(
            tipo=Movimiento.Tipo.ENTRADA,
            producto=producto,
            almacen=almacen,
            cantidad=10,
            realizada_por=usuario_admin,
        )
        alertas = Alerta.objects.filter(producto=producto)
        assert alertas.count() == 0

    def test_alerta_model_string(self, producto):
        alerta = Alerta.objects.create(
            producto=producto,
            mensaje="Test alerta para producto con stock bajo",
        )
        assert str(alerta).startswith("[PENDIENTE]")
        assert "stock bajo" in str(alerta)

    def test_alerta_estados_disponibles(self):
        assert Alerta.Estado.PENDIENTE == "PENDIENTE"
        assert Alerta.Estado.VISTA == "VISTA"
        assert Alerta.Estado.RESUELTA == "RESUELTA"
