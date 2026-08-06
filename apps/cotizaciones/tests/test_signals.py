from unittest.mock import patch

import pytest
from django.test.utils import override_settings

from apps.clientes.models import Cliente
from apps.cotizaciones.models import Cotizacion
from apps.inventario.models import Producto


@pytest.mark.django_db
class TestCotizacionSignals:
    @pytest.fixture
    def cliente(self, db):  # noqa: ARG001
        return Cliente.objects.create(
            empresa="Transportes del Norte S.A. de C.V.",
            nombre="Juan Pérez",
            email="juan.perez@transportesnorte.com",
            rfc="TNO900101ABC",
        )

    @pytest.fixture
    def unidad(self, db, categoria):  # noqa: ARG001
        return Producto.objects.create(
            sku="KW-T680-001",
            nombre="Kenworth T680 2024",
            vin="3HHDMABN7RL000001",
            categoria=categoria,
            precio_venta=1500000.00,
        )

    @override_settings(CRM_WEBHOOK_URL="https://crm.example.com/webhook", CRM_HMAC_SECRET="test-secret")
    @patch("apps.cotizaciones.signals.enviar_evento_crm.delay")
    def test_cotizacion_creada_encola_evento(self, mock_delay, cliente, unidad, usuario_vendedor):
        Cotizacion.objects.create(
            folio="COT-00001",
            cliente=cliente,
            monto=1500000.00,
            esquema=Cotizacion.Esquema.CREDITO,
            unidad_interes=unidad,
            vendedor=usuario_vendedor,
        )
        mock_delay.assert_called_once()
        args, kwargs = mock_delay.call_args
        assert kwargs["evento"] == "cotizacion.creada"
        payload = kwargs["payload"]
        assert payload == {
            "cliente_email": cliente.email,
            "monto": "1500000.00",
            "esquema": Cotizacion.Esquema.CREDITO,
            "unidad_interes": "3HHDMABN7RL000001",
            "vendedor_email": usuario_vendedor.email,
        }

    @override_settings(CRM_WEBHOOK_URL="https://crm.example.com/webhook", CRM_HMAC_SECRET="test-secret")
    @patch("apps.cotizaciones.signals.enviar_evento_crm.delay")
    def test_cotizacion_usa_sku_si_no_hay_vin(self, mock_delay, cliente, producto, usuario_vendedor):
        Cotizacion.objects.create(
            folio="COT-00002",
            cliente=cliente,
            monto=100.00,
            esquema=Cotizacion.Esquema.CONTADO,
            unidad_interes=producto,
            vendedor=usuario_vendedor,
        )
        args, kwargs = mock_delay.call_args
        assert kwargs["payload"]["unidad_interes"] == producto.sku
