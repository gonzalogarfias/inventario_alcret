import logging

from django.conf import settings

from apps.auditoria.models import AuditLog
from apps.shared.middleware import get_current_request_ip

logger = logging.getLogger(__name__)


def registrar_evento_auditoria(evento, datos, usuario=None):
    AuditLog.objects.create(
        evento=evento,
        usuario=usuario,
        ip_address=get_current_request_ip(),
        datos=datos,
    )


def crm_configurado():
    return bool(settings.CRM_WEBHOOK_URL and settings.CRM_HMAC_SECRET)
