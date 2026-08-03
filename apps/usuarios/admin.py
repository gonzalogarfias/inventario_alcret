from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(BaseUserAdmin):
    list_display = ["email", "nombre", "rol", "activo", "ultimo_acceso", "esta_bloqueado"]
    list_filter = ["rol", "activo"]
    search_fields = ["email", "nombre"]
    ordering = ["email"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Información personal", {"fields": ("nombre", "rol")}),
        ("Estado", {"fields": ("activo",)}),
        ("Seguridad", {"fields": ("intentos_fallidos", "bloqueado_hasta")}),
        ("Fechas", {"fields": ("ultimo_acceso", "fecha_creacion")}),
    )
    readonly_fields = ["fecha_creacion", "ultimo_acceso", "intentos_fallidos"]
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "nombre", "rol", "password1", "password2"),
            },
        ),
    )

    @admin.display(boolean=True, description="Bloqueado")
    def esta_bloqueado(self, obj):
        return obj.esta_bloqueado
