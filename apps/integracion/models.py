import uuid

from django.db import models
from django.utils import timezone


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


class ClaveCRM(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    clave_publica = models.CharField(max_length=64, unique=True, verbose_name="identificador público de la clave")
    hash_clave = models.CharField(max_length=128, verbose_name="SHA-256 del secreto")
    activa = models.BooleanField(default=True, verbose_name="clave en uso actualmente")
    creada_en = models.DateTimeField(auto_now_add=True)
    expira_en = models.DateTimeField(verbose_name="fecha de expiración")
    rotada_en = models.DateTimeField(null=True, blank=True, verbose_name="fecha en que fue rotada")

    class Meta:
        verbose_name = "clave CRM"
        verbose_name_plural = "claves CRM"
        ordering = ["-creada_en"]

    def __str__(self):
        estado = "activa" if self.activa else "inactiva"
        return f"{self.clave_publica} ({estado})"

    def save(self, *args, **kwargs):
        if self.activa:
            ClaveCRM.objects.filter(activa=True).exclude(pk=self.pk).update(
                activa=False, rotada_en=timezone.now()
            )
        super().save(*args, **kwargs)
