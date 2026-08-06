from django import forms

from apps.shared.value_objects import SKU, PrecioVenta
from apps.shared.value_objects import ValidationError as VOValidationError

from .models import Producto


class ProductoForm(forms.ModelForm):
    """Formulario de producto con validación centralizada por Value Objects.

    La validación de SKU y PrecioVenta vive acá (una sola vez) y se reutiliza
    en ProductoCreateView y ProductoUpdateView.
    """

    class Meta:
        model = Producto
        fields = [
            "sku", "nombre", "vin", "descripcion", "categoria",
            "precio_venta", "stock_minimo", "activo",
        ]

    def clean_sku(self):
        sku = self.cleaned_data["sku"]
        try:
            SKU.de_string(sku)
        except VOValidationError as e:
            raise forms.ValidationError(str(e))
        return sku

    def clean_precio_venta(self):
        precio = self.cleaned_data["precio_venta"]
        try:
            PrecioVenta.de_string(str(precio))
        except VOValidationError as e:
            raise forms.ValidationError(str(e))
        return precio
