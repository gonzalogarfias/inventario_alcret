import pytest
from unittest.mock import patch
from apps.integracion.tasks import enviar_evento_crm
from apps.integracion.models import SyncLog


@pytest.mark.django_db
class TestCrmTasks:
    def test_sin_config_marca_fallido(self):
        with patch("apps.integracion.tasks.settings.CRM_WEBHOOK_URL", None), \
             patch("apps.integracion.tasks.settings.CRM_HMAC_SECRET", None):
            enviar_evento_crm.run(evento="stock.actualizado", payload={"test": True})
        log = SyncLog.objects.latest("created_at")
        assert log.estado == "FALLIDO"
        assert log.evento == "stock.actualizado"

    def test_envio_exitoso(self):
        with patch("apps.integracion.tasks.settings.CRM_WEBHOOK_URL", "https://crm.test/webhook"), \
             patch("apps.integracion.tasks.settings.CRM_HMAC_SECRET", "secret-key"), \
             patch("requests.post") as mock_post:
            mock_response = mock_post.return_value
            mock_response.status_code = 200
            mock_response.text = "OK"
            mock_response.raise_for_status.return_value = None

            enviar_evento_crm.run(evento="producto.creado", payload={"sku": "TEST"})

            log = SyncLog.objects.latest("created_at")
            assert log.estado == "ENVIADO"
            assert log.evento == "producto.creado"
            mock_post.assert_called_once()

    def test_envio_fallido_reintenta(self):
        with patch("apps.integracion.tasks.settings.CRM_WEBHOOK_URL", "https://crm.test/webhook"), \
             patch("apps.integracion.tasks.settings.CRM_HMAC_SECRET", "secret-key"), \
             patch("requests.post") as mock_post:
            mock_post.side_effect = Exception("Connection timeout")

            with pytest.raises(Exception, match="Connection timeout"):
                enviar_evento_crm.run(evento="stock.actualizado", payload={"test": True})

            log = SyncLog.objects.latest("created_at")
            assert log.estado == "FALLIDO"
            assert "Connection timeout" in log.respuesta["error"]

    def test_firma_hmac_en_header(self):
        with patch("apps.integracion.tasks.settings.CRM_WEBHOOK_URL", "https://crm.test/webhook"), \
             patch("apps.integracion.tasks.settings.CRM_HMAC_SECRET", "secret-key"), \
             patch("requests.post") as mock_post:
            mock_response = mock_post.return_value
            mock_response.status_code = 200
            mock_response.text = "OK"
            mock_response.raise_for_status.return_value = None

            enviar_evento_crm.run(evento="stock.actualizado", payload={"id": "abc"})

            call_kwargs = mock_post.call_args[1]
            assert "X-Signature" in call_kwargs["headers"]
            assert call_kwargs["headers"]["Content-Type"] == "application/json"
