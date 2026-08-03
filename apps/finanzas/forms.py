from django import forms

from apps.usuarios.models import Usuario

from .models import Factura


class FacturaForm(forms.ModelForm):
    class Meta:
        model = Factura
        fields = ["tipo", "numero", "proveedor_cliente", "monto", "fecha", "archivo", "movimiento", "observaciones"]
        widgets = {
            "fecha": forms.DateInput(attrs={"type": "date"}),
            "observaciones": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, user_rol=None, **kwargs):
        super().__init__(*args, **kwargs)

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
