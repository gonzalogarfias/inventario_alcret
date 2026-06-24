from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["evento", "usuario", "ip_address", "timestamp"]
    list_filter = ["evento", "timestamp"]
    search_fields = ["usuario__email", "ip_address"]
    readonly_fields = ["id", "evento", "usuario", "ip_address", "timestamp", "datos", "hash_previo"]

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return True
