import uuid
import hashlib
import json
from django.db import models


class AuditLog(models.Model):
    class Evento(models.TextChoices):
        ENTRADA = "ENTRADA", "Entrada de inventario"
        SALIDA = "SALIDA", "Salida de inventario"
        AJUSTE = "AJUSTE", "Ajuste / merma"
        LOGIN_OK = "LOGIN_OK", "Inicio de sesión exitoso"
        LOGIN_FAIL = "LOGIN_FAIL", "Intento de sesión fallido"
        PASSWORD_RESET = "PASSWORD_RESET", "Recuperación de contraseña"
        PASSWORD_CHANGED = "PASSWORD_CHANGED", "Contraseña cambiada"
        USUARIO_CREADO = "USUARIO_CREADO", "Usuario creado"
        USUARIO_DESACTIVADO = "USUARIO_DESACTIVADO", "Usuario desactivado"
        PERMISO_CAMBIADO = "PERMISO_CAMBIADO", "Permiso modificado"
        EXPORTACION = "EXPORTACION", "Exportación de datos"
        SYNC_CRM = "SYNC_CRM", "Sincronización con CRM"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    evento = models.CharField(max_length=30, choices=Evento.choices)
    usuario = models.ForeignKey("usuarios.Usuario", null=True, on_delete=models.SET_NULL)
    ip_address = models.GenericIPAddressField()
    timestamp = models.DateTimeField(auto_now_add=True)
    datos = models.JSONField()
    hash_previo = models.CharField(max_length=64)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "registro de auditoría"
        verbose_name_plural = "registros de auditoría"

    def __str__(self):
        return f"{self.evento} @ {self.timestamp}"

    def calcular_hash(self):
        contenido = {
            "id": str(self.id),
            "evento": self.evento,
            "usuario_id": str(self.usuario_id) if self.usuario_id else None,
            "ip_address": self.ip_address,
            "timestamp": str(self.timestamp),
            "datos": self.datos,
            "hash_previo": self.hash_previo,
        }
        return hashlib.sha256(json.dumps(contenido, sort_keys=True, default=str).encode()).hexdigest()

    def save(self, *args, **kwargs):
        if self.pk and AuditLog.objects.filter(pk=self.pk).exists():
            raise PermissionError("AuditLog es inmutable. No se puede modificar un registro existente.")
        if not self.hash_previo:
            ultimo = AuditLog.objects.order_by("-timestamp").first()
            self.hash_previo = ultimo.calcular_hash() if ultimo else "0" * 64
        super().save(*args, **kwargs)

    def verificar_integridad(self):
        if self.hash_previo == "0" * 64:
            return True
        anterior = (
            AuditLog.objects.filter(timestamp__lt=self.timestamp)
            .order_by("-timestamp")
            .first()
        )
        if not anterior:
            return False
        return anterior.calcular_hash() == self.hash_previo
