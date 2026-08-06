import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Cotizacion(models.Model):
    class Esquema(models.TextChoices):
        CONTADO = "CONTADO", "Contado"
        CREDITO = "CREDITO", "Crédito"
        ARRENDAMIENTO = "ARRENDAMIENTO", "Arrendamiento"

    class Estado(models.TextChoices):
        ENVIADA = "ENVIADA", "Enviada"
        GANADA = "GANADA", "Ganada"
        PERDIDA = "PERDIDA", "Perdida"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    folio = models.CharField(max_length=30, unique=True)
    cliente = models.ForeignKey(
        "clientes.Cliente", on_delete=models.PROTECT, related_name="cotizaciones"
    )
    monto = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))]
    )
    esquema = models.CharField(max_length=20, choices=Esquema.choices, default=Esquema.CONTADO)
    unidad_interes = models.ForeignKey(
        "inventario.Producto", on_delete=models.PROTECT, related_name="cotizaciones",
        verbose_name="Unidad de interés",
    )
    vendedor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="cotizaciones",
    )
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.ENVIADA)
    observaciones = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "cotización"
        verbose_name_plural = "cotizaciones"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["cliente", "-created_at"]),
            models.Index(fields=["estado", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.folio} - {self.cliente} - {self.unidad_interes.nombre}"
