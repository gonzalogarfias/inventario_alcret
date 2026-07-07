import pytest

from apps.inventario.models import Movimiento
from apps.inventario.services import registrar_movimiento


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
        with pytest.raises(ValueError, match="positivo"):
            registrar_movimiento(
                tipo=Movimiento.Tipo.ENTRADA,
                producto=producto,
                almacen=almacen,
                cantidad=0,
                realizada_por=usuario_admin,
            )

    def test_cantidad_negativa_lanza_error(self, producto, almacen, usuario_admin):
        with pytest.raises(ValueError, match="positivo"):
            registrar_movimiento(
                tipo=Movimiento.Tipo.ENTRADA,
                producto=producto,
                almacen=almacen,
                cantidad=-5,
                realizada_por=usuario_admin,
            )
