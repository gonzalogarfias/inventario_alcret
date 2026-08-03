# apps/usuarios/tests/test_security.py
import pytest
from django.contrib.auth import get_user_model
from django.test.utils import override_settings
from django.urls import reverse

from apps.auditoria.models import AuditLog
from apps.usuarios.models import Usuario

UsuarioModel = get_user_model()


@pytest.mark.django_db
class TestRBACUsuariosGestion:
    def test_vendedor_no_puede_listar_usuarios(self, client, usuario_vendedor):
        client.force_login(usuario_vendedor)
        response = client.get(reverse("usuario_list"))
        assert response.status_code == 403

    def test_vendedor_no_puede_crear_usuario(self, client, usuario_vendedor):
        client.force_login(usuario_vendedor)
        response = client.get(reverse("usuario_create"))
        assert response.status_code == 403

    def test_vendedor_no_puede_editar_usuario(self, client, usuario_vendedor, usuario_admin):
        client.force_login(usuario_vendedor)
        response = client.get(reverse("usuario_update", args=[usuario_admin.pk]))
        assert response.status_code == 403

    def test_almacenista_no_puede_listar_usuarios(self, client, usuario_almacenista):
        client.force_login(usuario_almacenista)
        response = client.get(reverse("usuario_list"))
        assert response.status_code == 403

    def test_admin_puede_listar_usuarios(self, authenticated_client):
        response = authenticated_client.get(reverse("usuario_list"))
        assert response.status_code == 200


@pytest.mark.django_db
class TestRBACDashboard:
    def test_vendedor_puede_ver_dashboard(self, client, usuario_vendedor):
        client.force_login(usuario_vendedor)
        response = client.get(reverse("dashboard"))
        assert response.status_code == 200

    def test_almacenista_puede_ver_dashboard_basico(self, client, usuario_almacenista):
        """ALMACENISTA ve solo stock y movimientos, no métricas sensibles."""
        client.force_login(usuario_almacenista)
        response = client.get(reverse("dashboard"))
        assert response.status_code == 200
        assert "total_usuarios" not in response.context
        assert "total_alertas" not in response.context

    def test_admin_ve_todas_las_metricas(self, authenticated_client):
        response = authenticated_client.get(reverse("dashboard"))
        assert response.status_code == 200
        assert "total_usuarios" in response.context
        assert "total_alertas" in response.context


@pytest.mark.django_db
class TestCreacionUsuarios:
    @override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.Argon2PasswordHasher"])
    def test_create_usuario_setea_password_correctamente(self, authenticated_client):
        data = {
            "email": "seguro@test.com",
            "nombre": "Seguro Test",
            "rol": Usuario.Rol.VENDEDOR,
            "password": "SecurePass789!",
        }
        authenticated_client.post(reverse("usuario_create"), data, follow=True)
        usuario = UsuarioModel.objects.get(email="seguro@test.com")
        assert usuario.password != "SecurePass789!"
        assert usuario.password.startswith("argon2")

    def test_create_usuario_genera_auditlog(self, authenticated_client):
        AuditLog.objects.all().delete()
        data = {
            "email": "auditlog@test.com",
            "nombre": "Audit Log Test",
            "rol": Usuario.Rol.ALMACENISTA,
            "password": "AuditPass123!",
        }
        authenticated_client.post(reverse("usuario_create"), data, follow=True)
        assert AuditLog.objects.filter(
            evento=AuditLog.Evento.USUARIO_CREADO,
            datos__email="auditlog@test.com",
        ).exists()

    def test_create_usuario_sin_password_rechazado(self, authenticated_client):
        """El formulario UsuarioCreateForm rechaza creación sin password."""
        data = {
            "email": "nopass@test.com",
            "nombre": "No Pass",
            "rol": Usuario.Rol.VENDEDOR,
        }
        response = authenticated_client.post(reverse("usuario_create"), data)
        assert response.status_code == 200  # re-render con errores
        assert not UsuarioModel.objects.filter(email="nopass@test.com").exists()
