import uuid

from django.db import models


class AlertaConfig(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    producto = models.ForeignKey(
        "inventario.Producto", on_delete=models.CASCADE, null=True, blank=True
    )
    umbral_minimo = models.PositiveIntegerField(
        help_text="Stock mínimo para disparar alerta (0 = usar stock_minimo del producto)"
    )
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "configuración de alerta"
        verbose_name_plural = "configuraciones de alerta"
        unique_together = ["producto"]

    def __str__(self):
        target = self.producto.nombre if self.producto else "global"
        return f"Alerta {target} < {self.umbral_minimo}"


class Alerta(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        VISTA = "VISTA", "Vista"
        RESUELTA = "RESUELTA", "Resuelta"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    producto = models.ForeignKey(
        "inventario.Producto", on_delete=models.CASCADE, null=True, blank=True
    )
    mensaje = models.TextField()
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    created_at = models.DateTimeField(auto_now_add=True)
    resuelta_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "alerta"
        verbose_name_plural = "alertas"
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.estado}] {self.mensaje[:50]}"
