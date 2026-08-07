from unittest.mock import patch

import pytest
from django.test.utils import override_settings

from apps.clientes.models import Cliente


@pytest.mark.django_db
class TestClienteSignals:
    @override_settings(CRM_WEBHOOK_URL="https://crm.example.com/webhook", CRM_HMAC_SECRET="test-secret")
    @patch("apps.clientes.signals.enviar_evento_crm.delay")
    def test_cliente_creado_encola_evento(self, mock_delay):
        cliente = Cliente.objects.create(
            empresa="Transportes del Norte S.A. de C.V.",
            nombre="Juan Pérez",
            email="juan.perez@transportesnorte.com",
            telefono="+528112345678",
            rfc="TNO900101ABC",
        )
        mock_delay.assert_called_once()
        args, kwargs = mock_delay.call_args
        assert kwargs["evento"] == "cliente.creado"
        payload = kwargs["payload"]
        assert payload == {
            "cliente_id": str(cliente.id),
            "empresa": cliente.empresa,
            "nombre": cliente.nombre,
            "email": cliente.email,
            "telefono": cliente.telefono,
            "rfc": cliente.rfc,
            "activo": cliente.activo,
            "created_at": cliente.created_at.isoformat(),
            "updated_at": cliente.updated_at.isoformat(),
        }

    @override_settings(CRM_WEBHOOK_URL="https://crm.example.com/webhook", CRM_HMAC_SECRET="test-secret")
    @patch("apps.clientes.signals.enviar_evento_crm.delay")
    def test_cliente_actualizado_encola_evento(self, mock_delay):
        cliente = Cliente.objects.create(
            empresa="Empresa SA",
            nombre="Contacto",
            email="contacto@empresa.com",
        )
        mock_delay.reset_mock()
        cliente.nombre = "Nuevo Contacto"
        cliente.save()
        mock_delay.assert_called_once()
        args, kwargs = mock_delay.call_args
        assert kwargs["evento"] == "cliente.actualizado"
        assert kwargs["payload"]["nombre"] == "Nuevo Contacto"

    @patch("apps.clientes.signals.enviar_evento_crm.delay")
    def test_cliente_no_encola_sin_webhook(self, mock_delay):
        Cliente.objects.create(
            empresa="Empresa SA",
            nombre="Contacto",
            email="contacto@empresa.com",
        )
        mock_delay.assert_not_called()
