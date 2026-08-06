from django.contrib import admin

from .models import Cliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ["empresa", "nombre", "email", "telefono", "rfc", "activo"]
    list_filter = ["activo"]
    search_fields = ["empresa", "nombre", "email", "rfc"]
