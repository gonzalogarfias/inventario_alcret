from django.contrib import admin

from apps.shared.middleware import get_current_request_ip
from apps.shared.services import registrar_audit_log

from .models import Factura


@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):
    list_display = ["numero", "get_tipo_display", "monto", "fecha", "proveedor_cliente", "created_at"]
    list_filter = ["tipo", "fecha"]
    search_fields = ["numero", "proveedor_cliente", "observaciones"]
    readonly_fields = ["created_at", "updated_at"]
    date_hierarchy = "fecha"

    fieldsets = [
        (None, {"fields": ["tipo", "numero", "proveedor_cliente", "monto", "fecha"]}),
        ("Archivo", {"fields": ["archivo"]}),
        ("Vinculación", {"fields": ["movimiento", "subido_por", "observaciones"]}),
        ("Auditoría", {"fields": ["created_at", "updated_at"]}),
    ]

    def save_model(self, request, obj, form, change):
        """Registra en auditoría cualquier alta/edición hecha desde el admin.

        Sin esto, un staff con permisos de admin podía modificar facturas
        sin dejar rastro en la cadena de auditoría (a diferencia de la
        vista factura_upload, que sí registra cada subida).
        """
        accion = "FACTURA_EDITADA_ADMIN" if change else "FACTURA_CREADA_ADMIN"
        super().save_model(request, obj, form, change)
        try:
            registrar_audit_log(
                evento="EXPORTACION",
                usuario=request.user,
                ip_address=get_current_request_ip(),
                datos={
                    "accion": accion,
                    "factura_id": str(obj.id),
                    "tipo": obj.tipo,
                    "monto": str(obj.monto),
                },
            )
        except Exception as e:
            # No se debe bloquear la operación del admin si la
            # auditoría falla, pero sí queda logueado como crítico.
            import logging
            logging.getLogger(__name__).critical(
                "FALLO al registrar edición de factura desde admin: %s", e, exc_info=True
            )

    def delete_model(self, request, obj):
        """Registra en auditoría el borrado individual desde el admin."""
        datos = {
            "accion": "FACTURA_ELIMINADA_ADMIN",
            "factura_id": str(obj.id),
            "tipo": obj.tipo,
            "monto": str(obj.monto),
            "numero": obj.numero,
        }
        super().delete_model(request, obj)
        try:
            registrar_audit_log(
                evento="EXPORTACION",
                usuario=request.user,
                ip_address=get_current_request_ip(),
                datos=datos,
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).critical(
                "FALLO al registrar borrado de factura desde admin: %s", e, exc_info=True
            )

    def delete_queryset(self, request, queryset):
        """Registra en auditoría el borrado masivo (acción 'Delete selected')."""
        facturas_info = [
            {"factura_id": str(f.id), "tipo": f.tipo, "monto": str(f.monto), "numero": f.numero}
            for f in queryset
        ]
        super().delete_queryset(request, queryset)
        try:
            registrar_audit_log(
                evento="EXPORTACION",
                usuario=request.user,
                ip_address=get_current_request_ip(),
                datos={"accion": "FACTURAS_ELIMINADAS_ADMIN_BULK", "facturas": facturas_info},
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).critical(
                "FALLO al registrar borrado masivo de facturas desde admin: %s", e, exc_info=True
            )
