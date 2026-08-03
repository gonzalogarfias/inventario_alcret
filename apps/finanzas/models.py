import uuid
from decimal import Decimal

from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models


def upload_factura_path(instance, filename):
    return f"facturas/{instance.tipo.lower()}/{instance.fecha:%Y/%m}/{filename}"


class Factura(models.Model):
    class Tipo(models.TextChoices):
        COMPRA = "COMPRA", "Compra"
        VENTA = "VENTA", "Venta"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    numero = models.CharField(max_length=100, blank=True)
    proveedor_cliente = models.CharField(max_length=200, blank=True)
    monto = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    fecha = models.DateField()
    archivo = models.FileField(
        upload_to=upload_factura_path,
        validators=[FileExtensionValidator(allowed_extensions=["pdf", "xml"])],
        help_text="PDF o XML de la factura",
    )
    movimiento = models.ForeignKey(
        "inventario.Movimiento",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="facturas",
    )
    observaciones = models.TextField(blank=True)
    subido_por = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.SET_NULL,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "factura"
        verbose_name_plural = "facturas"
        ordering = ["-fecha", "-created_at"]
        indexes = [
            models.Index(fields=["tipo", "-fecha"]),
            models.Index(fields=["fecha"]),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} {self.numero or '#'} — ${self.monto:.2f}"
