# apps/usuarios/tests/test_forms.py
import pytest

from apps.usuarios.forms import UsuarioCreateForm, UsuarioForm
from apps.usuarios.models import Usuario


@pytest.mark.django_db
class TestUsuarioCreateForm:
    def test_password_obligatoria(self):
        form = UsuarioCreateForm(data={
            "email": "test@example.com",
            "nombre": "Test",
            "rol": Usuario.Rol.VENDEDOR,
        })
        assert not form.is_valid()
        assert "password" in form.errors

    def test_password_validada(self):
        form = UsuarioCreateForm(data={
            "email": "test@example.com",
            "nombre": "Test",
            "rol": Usuario.Rol.VENDEDOR,
            "password": "123",  # muy corta
        })
        assert not form.is_valid()
        assert "password" in form.errors

    def test_email_duplicado(self):
        Usuario.objects.create_user(
            email="dup@example.com", nombre="Original",
            rol=Usuario.Rol.VENDEDOR, password="SecurePass123!",
        )
        form = UsuarioCreateForm(data={
            "email": "dup@example.com",
            "nombre": "Duplicado",
            "rol": Usuario.Rol.VENDEDOR,
            "password": "SecurePass123!",
        })
        assert not form.is_valid()
        assert "email" in form.errors

    def test_email_case_insensitive(self):
        Usuario.objects.create_user(
            email="Case@Example.com", nombre="Original",
            rol=Usuario.Rol.VENDEDOR, password="SecurePass123!",
        )
        form = UsuarioCreateForm(data={
            "email": "case@example.com",
            "nombre": "Duplicado",
            "rol": Usuario.Rol.VENDEDOR,
            "password": "SecurePass123!",
        })
        assert not form.is_valid()
        assert "email" in form.errors

    def test_save_hashea_password(self):
        form = UsuarioCreateForm(data={
            "email": "hash@example.com",
            "nombre": "Hash",
            "rol": Usuario.Rol.VENDEDOR,
            "password": "SecurePass123!",
        })
        assert form.is_valid()
        usuario = form.save()
        assert usuario.password != "SecurePass123!"
        assert usuario.check_password("SecurePass123!")


@pytest.mark.django_db
class TestUsuarioUpdateForm:
    def test_password_opcional(self):
        usuario = Usuario.objects.create_user(
            email="update@example.com", nombre="Original",
            rol=Usuario.Rol.VENDEDOR, password="SecurePass123!",
        )
        form = UsuarioForm(data={
            "email": "update@example.com",
            "nombre": "Modificado",
            "rol": Usuario.Rol.VENDEDOR,
        }, instance=usuario)
        assert form.is_valid()
        usuario = form.save()
        assert usuario.check_password("SecurePass123!")  # sin cambio

    def test_cambio_password(self):
        usuario = Usuario.objects.create_user(
            email="changepass@example.com", nombre="Change",
            rol=Usuario.Rol.VENDEDOR, password="OldPass123!",
        )
        form = UsuarioForm(data={
            "email": "changepass@example.com",
            "nombre": "Change",
            "rol": Usuario.Rol.VENDEDOR,
            "password": "NewSecurePass789!",
        }, instance=usuario)
        assert form.is_valid()
        usuario = form.save()
        assert usuario.check_password("NewSecurePass789!")

    def test_email_unico_en_update(self):
        Usuario.objects.create_user(
            email="otro@example.com", nombre="Otro",
            rol=Usuario.Rol.VENDEDOR, password="SecurePass123!",
        )
        usuario = Usuario.objects.create_user(
            email="update@example.com", nombre="Update",
            rol=Usuario.Rol.VENDEDOR, password="SecurePass123!",
        )
        form = UsuarioForm(data={
            "email": "otro@example.com",
            "nombre": "Update",
            "rol": Usuario.Rol.VENDEDOR,
        }, instance=usuario)
        assert not form.is_valid()
        assert "email" in form.errors
