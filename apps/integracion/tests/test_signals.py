from decimal import Decimal
from unittest.mock import patch

import pytest
from django.test.utils import override_settings

from apps.inventario.models import Movimiento


@pytest.mark.django_db
class TestIntegracionSignals:
    @override_settings(CRM_WEBHOOK_URL="https://crm.example.com/webhook", CRM_HMAC_SECRET="test-secret")
    @patch("apps.integracion.signals.enviar_evento_crm.delay")
    def test_movimiento_encola_tarea_crm(self, mock_delay, producto, almacen, usuario_admin):
        from apps.inventario.models import Stock

        Stock.objects.create(producto=producto, almacen=almacen, cantidad=Decimal("50"))
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
        payload = kwargs["payload"]
        assert payload["producto_id"] == str(producto.pk)
        assert payload["almacen_id"] == str(almacen.pk)
        assert payload["sku_o_vin"] == (producto.vin or producto.sku)
        assert payload["nombre_unidad"] == producto.nombre
        assert payload["cantidad_disponible"] == "60"
        assert payload["tipo_movimiento"] == Movimiento.Tipo.ENTRADA

    @override_settings(CRM_WEBHOOK_URL="https://crm.example.com/webhook", CRM_HMAC_SECRET="test-secret")
    @patch("apps.integracion.signals.enviar_evento_crm.delay")
    def test_movimiento_no_encola_si_excepcion(self, mock_delay, producto, almacen, usuario_admin):
        from apps.inventario.models import Stock
        Stock.objects.create(producto=producto, almacen=almacen, cantidad=Decimal("100"))
        mock_delay.side_effect = Exception("Redis caído")
        Movimiento.objects.create(
            tipo=Movimiento.Tipo.SALIDA,
            producto=producto,
            almacen=almacen,
            cantidad=5,
            realizada_por=usuario_admin,
        )
        mock_delay.assert_called_once()
