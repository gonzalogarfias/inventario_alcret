from django.contrib import admin

from .models import SyncLog, WebhookCRM


@admin.register(WebhookCRM)
class WebhookCRMAdmin(admin.ModelAdmin):
    list_display = ["evento", "url_destino", "activo"]


@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    list_display = ["evento", "estado", "intentos", "created_at"]
    list_filter = ["estado", "evento"]
