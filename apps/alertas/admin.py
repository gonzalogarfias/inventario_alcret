from django.contrib import admin

from .models import Alerta, AlertaConfig


@admin.register(AlertaConfig)
class AlertaConfigAdmin(admin.ModelAdmin):
    list_display = ["producto", "umbral_minimo", "activo"]
    list_filter = ["activo"]


@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    list_display = ["mensaje", "estado", "created_at"]
    list_filter = ["estado"]
    readonly_fields = ["id", "created_at"]
