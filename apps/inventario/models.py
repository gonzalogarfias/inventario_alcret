import uuid
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone


class Categoria(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "categoría"
        verbose_name_plural = "categorías"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sku = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name="productos")
    precio_venta = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    costo_promedio = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    stock_minimo = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "producto"
        verbose_name_plural = "productos"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.sku} - {self.nombre}"


class Almacen(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=100, unique=True)
    ubicacion = models.CharField(max_length=255, blank=True)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "almacén"
        verbose_name_plural = "almacenes"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Stock(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name="stocks")
    almacen = models.ForeignKey(Almacen, on_delete=models.CASCADE, related_name="stocks")
    cantidad = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "stock"
        verbose_name_plural = "stocks"
        unique_together = ["producto", "almacen"]

    def __str__(self):
        return f"{self.producto.nombre} @ {self.almacen.nombre}: {self.cantidad}"


class Movimiento(models.Model):
    class Tipo(models.TextChoices):
        ENTRADA = "ENTRADA", "Entrada"
        SALIDA = "SALIDA", "Salida"
        AJUSTE = "AJUSTE", "Ajuste"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name="movimientos")
    almacen = models.ForeignKey(Almacen, on_delete=models.PROTECT, related_name="movimientos")
    cantidad = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.001"))])
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    motivo = models.TextField(blank=True)
    realizada_por = models.ForeignKey("usuarios.Usuario", on_delete=models.SET_NULL, null=True, related_name="movimientos")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "movimiento"
        verbose_name_plural = "movimientos"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.tipo} {self.producto.sku} x{self.cantidad}"
