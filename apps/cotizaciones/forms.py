from django import forms

from .models import Cotizacion


class CotizacionForm(forms.ModelForm):
    folio = forms.CharField(required=False, widget=forms.TextInput(attrs={"readonly": "readonly"}))

    class Meta:
        model = Cotizacion
        fields = [
            "folio", "cliente", "monto", "esquema", "unidad_interes",
            "vendedor", "estado", "observaciones",
        ]
