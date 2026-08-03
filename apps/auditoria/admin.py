"""Admin de auditoría.

Correcciones Fase 4:
  - has_add_permission = False (AuditLog solo se crea via código, nunca manual)
"""

from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["evento", "usuario", "ip_address", "timestamp"]
    list_filter = ["evento", "timestamp"]
    search_fields = ["usuario__email", "ip_address"]
    readonly_fields = [
        "id", "evento", "usuario", "ip_address",
        "timestamp", "datos", "hash_previo",
    ]

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        """AuditLog solo se crea via signals/código, nunca manualmente."""
        return False
