import hashlib
import hmac
import json
import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def enviar_evento_crm(self, evento, payload):
    from .models import SyncLog

    sync_log = SyncLog.objects.create(
        evento=evento,
        payload=payload,
        estado="PENDIENTE",
    )

    webhook_url = settings.CRM_WEBHOOK_URL
    secret = settings.CRM_HMAC_SECRET

    if not webhook_url or not secret:
        logger.warning("CRM_WEBHOOK_URL o CRM_HMAC_SECRET no configurados")
        sync_log.estado = "FALLIDO"
        sync_log.save()
        return

    import requests
    body = json.dumps({"evento": evento, "payload": payload}, default=str).encode()
    firma = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    try:
        resp = requests.post(
            webhook_url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "X-Signature": firma,
            },
            timeout=30,
        )
        resp.raise_for_status()
        sync_log.estado = "ENVIADO"
        sync_log.respuesta = {"status": resp.status_code, "body": resp.text}
    except Exception as exc:
        sync_log.estado = "FALLIDO"
        sync_log.respuesta = {"error": str(exc)}
        sync_log.intentos = self.request.retries + 1
        sync_log.save()

        backoff = [60, 300, 900][self.request.retries]
        raise self.retry(exc=exc, countdown=backoff)

    sync_log.intentos = self.request.retries + 1
    sync_log.save()


@shared_task
def verificar_expiracion_claves():
    from .models import ClaveCRM
    umbral = timezone.now() + timedelta(days=7)
    proximas = ClaveCRM.objects.filter(
        activa=True, expira_en__lte=umbral, expira_en__gt=timezone.now()
    )
    for clave in proximas:
        logger.warning(
            "Clave CRM %s expira el %s (dentro de 7 días)",
            clave.clave_publica, clave.expira_en,
        )
    vencidas = ClaveCRM.objects.filter(activa=True, expira_en__lte=timezone.now())
    for clave in vencidas:
        logger.error("Clave CRM %s EXPIRADA el %s", clave.clave_publica, clave.expira_en)
        clave.activa = False
        clave.rotada_en = timezone.now()
        clave.save()
