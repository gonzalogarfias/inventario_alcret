import uuid
from django.db import models


class DashboardConfig(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    config = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "configuración de dashboard"
        verbose_name_plural = "configuraciones de dashboard"

    def __str__(self):
        return self.nombre


class ReporteProgramado(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=50, choices=[
        ("EXCEL", "Excel"),
        ("PDF", "PDF"),
        ("CSV", "CSV"),
    ])
    cron_expresion = models.CharField(max_length=100)
    destinatarios = models.JSONField(default=list)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "reporte programado"
        verbose_name_plural = "reportes programados"

    def __str__(self):
        return self.nombre
