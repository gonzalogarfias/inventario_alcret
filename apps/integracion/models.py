import uuid
from django.db import models


class WebhookCRM(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    evento = models.CharField(max_length=50)
    url_destino = models.URLField()
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "webhook CRM"
        verbose_name_plural = "webhooks CRM"

    def __str__(self):
        return f"{self.evento} -> {self.url_destino}"


class SyncLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    evento = models.CharField(max_length=50)
    estado = models.CharField(max_length=20, choices=[
        ("PENDIENTE", "Pendiente"),
        ("ENVIADO", "Enviado"),
        ("FALLIDO", "Fallido"),
    ], default="PENDIENTE")
    payload = models.JSONField()
    respuesta = models.JSONField(null=True, blank=True)
    intentos = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "log de sincronización"
        verbose_name_plural = "logs de sincronización"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.evento} - {self.estado} @ {self.created_at}"
