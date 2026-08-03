from django.contrib import admin

from .models import DashboardConfig, ReporteProgramado


@admin.register(DashboardConfig)
class DashboardConfigAdmin(admin.ModelAdmin):
    list_display = ["nombre", "created_at", "updated_at"]
    search_fields = ["nombre", "descripcion"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(ReporteProgramado)
class ReporteProgramadoAdmin(admin.ModelAdmin):
    list_display = ["nombre", "tipo", "activo", "created_at", "updated_at"]
    list_filter = ["tipo", "activo"]
    search_fields = ["nombre", "cron_expresion"]
    readonly_fields = ["created_at", "updated_at"]
