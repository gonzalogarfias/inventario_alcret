import pytest
from unittest.mock import patch
from apps.inventario.models import Movimiento


@pytest.mark.django_db
class TestIntegracionSignals:
    @patch("apps.integracion.signals.enviar_evento_crm.delay")
    def test_movimiento_encola_tarea_crm(self, mock_delay, producto, almacen, usuario_admin):
        Movimiento.objects.create(
            tipo=Movimiento.Tipo.ENTRADA,
            producto=producto,
            almacen=almacen,
            cantidad=10,
            realizada_por=usuario_admin,
        )
        mock_delay.assert_called_once()
        args, kwargs = mock_delay.call_args
        assert kwargs["evento"] == "stock.actualizado"
        assert kwargs["payload"]["producto_id"] == str(producto.pk)
        assert kwargs["payload"]["cantidad"] == "10"

    @patch("apps.integracion.signals.enviar_evento_crm.delay")
    def test_movimiento_no_encola_si_excepcion(self, mock_delay, producto, almacen, usuario_admin):
        mock_delay.side_effect = Exception("Redis caído")
        Movimiento.objects.create(
            tipo=Movimiento.Tipo.SALIDA,
            producto=producto,
            almacen=almacen,
            cantidad=5,
            realizada_por=usuario_admin,
        )
        mock_delay.assert_called_once()
