import uuid

from django.core.validators import RegexValidator
from django.db import models


class Cliente(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.CharField(max_length=200, blank=True)
    nombre = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    telefono = models.CharField(max_length=30, blank=True)
    rfc = models.CharField(
        max_length=13,
        blank=True,
        validators=[RegexValidator(r"^[A-ZÑ&0-9]{12,13}$", "RFC inválido")],
    )
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "cliente"
        verbose_name_plural = "clientes"
        ordering = ["empresa", "nombre"]
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["rfc"]),
        ]

    def __str__(self):
        return self.empresa or self.nombre
