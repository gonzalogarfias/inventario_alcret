from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import Usuario


class UsuarioForm(forms.ModelForm):
    """Formulario base para creación y edición de usuarios.

    Valida que la contraseña cumpla con los validadores configurados
    (AUTH_PASSWORD_VALIDATORS).
    """

    password = forms.CharField(
        widget=forms.PasswordInput,
        required=False,
        help_text="Mínimo 12 caracteres. Déjalo en blanco para mantener la actual.",
    )

    class Meta:
        model = Usuario
        fields = ["email", "nombre", "rol", "activo"]

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email:
            email = email.lower().strip()
            qs = Usuario.objects.filter(email__iexact=email)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError("Ya existe un usuario con este email.")
        return email

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if password:
            validate_password(password)
        return password

    def save(self, commit=True):
        usuario = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            usuario.set_password(password)
        if commit:
            usuario.save()
        return usuario


class UsuarioCreateForm(UsuarioForm):
    """Formulario de creación: password obligatoria."""

    password = forms.CharField(
        widget=forms.PasswordInput,
        required=True,
        help_text="Mínimo 12 caracteres. No uses contraseñas comunes.",
    )

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if not password:
            raise ValidationError("La contraseña es obligatoria.")
        validate_password(password)
        return password
