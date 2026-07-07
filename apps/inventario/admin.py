from django.contrib import admin

from .models import Almacen, Categoria, Movimiento, Producto, Stock


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ["nombre", "activo"]
    search_fields = ["nombre"]


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ["sku", "nombre", "categoria", "precio_venta", "stock_minimo", "activo"]
    list_filter = ["categoria", "activo"]
    search_fields = ["sku", "nombre"]


@admin.register(Almacen)
class AlmacenAdmin(admin.ModelAdmin):
    list_display = ["nombre", "ubicacion", "activo"]


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ["producto", "almacen", "cantidad"]
    list_filter = ["almacen"]


@admin.register(Movimiento)
class MovimientoAdmin(admin.ModelAdmin):
    list_display = ["tipo", "producto", "almacen", "cantidad", "realizada_por", "created_at"]
    list_filter = ["tipo", "almacen", "created_at"]
    search_fields = ["producto__sku", "producto__nombre"]
    readonly_fields = ["created_at"]
