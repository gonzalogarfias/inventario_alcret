from django.contrib import admin
from .models import DashboardConfig, ReporteProgramado


@admin.register(DashboardConfig)
class DashboardConfigAdmin(admin.ModelAdmin):
    list_display = ["nombre", "created_at"]


@admin.register(ReporteProgramado)
class ReporteProgramadoAdmin(admin.ModelAdmin):
    list_display = ["nombre", "tipo", "activo", "created_at"]
