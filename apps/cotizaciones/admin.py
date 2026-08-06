from django.contrib import admin

from .models import Cotizacion


@admin.register(Cotizacion)
class CotizacionAdmin(admin.ModelAdmin):
    list_display = ["folio", "cliente", "unidad_interes", "esquema", "monto", "vendedor", "estado", "created_at"]
    list_filter = ["estado", "esquema", "created_at"]
    search_fields = ["folio", "cliente__empresa", "cliente__nombre", "unidad_interes__sku", "unidad_interes__vin"]
