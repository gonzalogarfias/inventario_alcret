import hashlib
import json
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.integracion.models import ClaveCRM, SyncLog
from apps.integracion.tasks import enviar_evento_crm, verificar_expiracion_claves


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

    def test_firma_hmac_es_sha256_del_cuerpo(self):
        import hashlib
        import hmac

        with patch("apps.integracion.tasks.settings.CRM_WEBHOOK_URL", "https://crm.test/webhook"), \
             patch("apps.integracion.tasks.settings.CRM_HMAC_SECRET", "secret-key"), \
             patch("requests.post") as mock_post:
            mock_response = mock_post.return_value
            mock_response.status_code = 200
            mock_response.text = "OK"
            mock_response.raise_for_status.return_value = None

            enviar_evento_crm.run(evento="stock.actualizado", payload={"id": "abc"})

            call_kwargs = mock_post.call_args[1]
            cuerpo = call_kwargs["data"]
            firma_esperada = hmac.new(b"secret-key", cuerpo, hashlib.sha256).hexdigest()
            assert call_kwargs["headers"]["X-Signature"] == firma_esperada

            # El cuerpo no debe modificarse después de firmarlo (integridad)
            assert json.loads(cuerpo)["evento"] == "stock.actualizado"


@pytest.mark.django_db
class TestVerificarExpiracionClaves:
    def _hash_clave(self, secreto="secreto"):
        return hashlib.sha256(secreto.encode()).hexdigest()

    def _crear_clave(self, **kwargs):
        datos = {
            "clave_publica": "clave-" + kwargs.get("clave_publica", "test"),
            "hash_clave": self._hash_clave(),
            "activa": True,
            "expira_en": timezone.now() + timedelta(days=90),
        }
        datos.update(kwargs)
        return ClaveCRM.objects.create(**datos)

    def test_desactiva_clave_vencida(self):
        clave = self._crear_clave(clave_publica="vencida")
        ClaveCRM.objects.filter(pk=clave.pk).update(
            expira_en=timezone.now() - timedelta(days=1)
        )
        verificar_expiracion_claves.run()
        clave.refresh_from_db()
        assert clave.activa is False
        assert clave.rotada_en is not None

    def test_no_toca_clave_vigente(self):
        clave = self._crear_clave(clave_publica="vigente")
        verificar_expiracion_claves.run()
        clave.refresh_from_db()
        assert clave.activa is True
        assert clave.rotada_en is None

    def test_no_desactiva_clave_proxima_a_expirar(self):
        """Dentro de 7 días solo se alerta (log), no se desactiva."""
        clave = self._crear_clave(
            clave_publica="proxima", expira_en=timezone.now() + timedelta(days=3)
        )
        verificar_expiracion_claves.run()
        clave.refresh_from_db()
        assert clave.activa is True

    def test_desactiva_solo_vencidas_entre_varias(self):
        vencida = self._crear_clave(clave_publica="vencida-2")
        ClaveCRM.objects.filter(pk=vencida.pk).update(
            expira_en=timezone.now() - timedelta(hours=1)
        )
        vigente = self._crear_clave(
            clave_publica="vigente-2", expira_en=timezone.now() + timedelta(days=30)
        )
        verificar_expiracion_claves.run()
        vencida.refresh_from_db()
        vigente.refresh_from_db()
        assert vencida.activa is False
        assert vigente.activa is True
