from django import forms
from django.core.exceptions import ValidationError

from apps.inventario.models import Movimiento
from apps.shared.permissions import puede_subir_factura
from apps.usuarios.models import Usuario

from .models import Factura


class MovimientoChoiceField(forms.ModelChoiceField):
    """ModelChoiceField con etiquetas legibles para asignar movimientos.

    Muestra tipo, producto (nombre + SKU), cantidad, almacén y fecha para
    que no sea necesario conocer el código del producto de memoria.
    """

    def label_from_instance(self, obj):
        tipo = obj.get_tipo_display()
        producto = obj.producto.nombre
        sku = obj.producto.sku
        cantidad = abs(obj.cantidad)
        almacen = obj.almacen.nombre
        fecha = obj.created_at.strftime("%d/%m/%Y %H:%M")
        return f"{tipo} — {producto} ({sku}) x{cantidad} · {almacen} · {fecha}"


class FacturaForm(forms.ModelForm):
    movimiento = MovimientoChoiceField(
        queryset=Movimiento.objects.select_related("producto", "almacen")
        .order_by("-created_at"),
        required=False,
        label="Movimiento asociado",
        help_text=(
            "Elegí el movimiento de inventario que respalda esta factura. "
            "Se muestra el producto, el almacén y la fecha para identificarlo."
        ),
    )

    class Meta:
        model = Factura
        fields = ["tipo", "numero", "proveedor_cliente", "monto", "fecha", "archivo", "movimiento", "observaciones"]
        widgets = {
            "fecha": forms.DateInput(attrs={"type": "date"}),
            "observaciones": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, user=None, user_rol=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

        if user_rol is None and user is not None:
            user_rol = user.rol

        base_classes = (
            "w-full px-3 py-2 border border-gray-300 rounded-lg text-sm "
            "focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
        )
        for field in self.fields.values():
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing} {base_classes}".strip()

        if user_rol:
            if user_rol == Usuario.Rol.VENDEDOR:
                self.fields["tipo"].choices = [(Factura.Tipo.VENTA.value, Factura.Tipo.VENTA.label)]
            elif user_rol == Usuario.Rol.ALMACENISTA:
                self.fields["tipo"].choices = [(Factura.Tipo.COMPRA.value, Factura.Tipo.COMPRA.label)]

    def clean_archivo(self):
        archivo = self.cleaned_data.get("archivo")
        if not archivo:
            return archivo

        max_size = 10 * 1024 * 1024  # 10 MiB
        if archivo.size > max_size:
            raise ValidationError("El archivo no puede superar los 10 MiB.")

        extension = archivo.name.rsplit(".", 1)[-1].lower() if "." in archivo.name else ""
        content_type = getattr(archivo, "content_type", "")
        tipos_permitidos = {
            "pdf": {"application/pdf"},
            "xml": {"application/xml", "text/xml", "application/octet-stream"},
        }
        if extension not in tipos_permitidos:
            raise ValidationError("Solo se permiten archivos PDF o XML.")
        if content_type and content_type not in tipos_permitidos[extension]:
            raise ValidationError("El tipo de contenido del archivo no coincide con su extensión.")

        posicion = archivo.tell()
        cabecera = archivo.read(256)
        archivo.seek(posicion)
        if extension == "pdf" and not cabecera.startswith(b"%PDF-"):
            raise ValidationError("El archivo PDF no tiene una cabecera válida.")
        if extension == "xml" and not cabecera.lstrip().startswith((b"<?xml", b"<")):
            raise ValidationError("El archivo XML no tiene una cabecera válida.")
        return archivo

    def clean(self):
        cleaned = super().clean()
        tipo = cleaned.get("tipo")
        if self.user is not None and tipo and not puede_subir_factura(self.user, tipo):
            raise ValidationError("No tenés permiso para subir este tipo de factura.")
        return cleaned
