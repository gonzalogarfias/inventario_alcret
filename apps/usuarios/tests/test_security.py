import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.auditoria.models import AuditLog
from apps.usuarios.models import Usuario

UsuarioModel = get_user_model()


@pytest.mark.django_db
class TestRBACUsuariosGestion:
    """Según matriz de permisos:
    - Gestionar usuarios: ADMIN ✅, VENDEDOR ❌, ALMACENISTA ❌
    Las vistas ya usan PermissionRequiredMixin con 'usuarios.puede_gestionar_usuarios'.
    """

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
    """El dashboard muestra KPIs y total_usuarios.
    Según matriz: Ver métricas y KPIs: ADMIN ✅, VENDEDOR ✅ parcial, ALMACENISTA ❌
    total_usuarios debería ser solo ADMIN.
    """

    def test_vendedor_puede_ver_dashboard(self, client, usuario_vendedor):
        client.force_login(usuario_vendedor)
        response = client.get(reverse("dashboard"))
        assert response.status_code == 200

    def test_almacenista_puede_ver_dashboard(self, client, usuario_almacenista):
        """Según matriz ALMACENISTA no debería ver métricas.
        Comportamiento actual: solo LoginRequiredMixin, cualquier rol ve dashboard."""
        client.force_login(usuario_almacenista)
        response = client.get(reverse("dashboard"))
        assert response.status_code == 200, (
            "ALMACENISTA ve dashboard. Según matriz debería tener acceso restringido."
        )

    def test_dashboard_muestra_total_usuarios(self, authenticated_client):
        """total_usuarios se muestra a cualquier rol autenticado.
        Esto podría ser información sensible para VENDEDOR/ALMACENISTA."""
        response = authenticated_client.get(reverse("dashboard"))
        assert "total_usuarios" in response.context
        assert response.context["total_usuarios"] >= 0


@pytest.mark.django_db
class TestCreacionUsuarios:
    """Mass Assignment y seguridad en creación de usuarios."""

    def test_create_usuario_setea_password_correctamente(self, authenticated_client):
        data = {
            "email": "seguro@test.com",
            "nombre": "Seguro Test",
            "rol": Usuario.Rol.VENDEDOR,
            "password": "SecurePass789!",
        }
        authenticated_client.post(reverse("usuario_create"), data, follow=True)
        usuario = UsuarioModel.objects.get(email="seguro@test.com")
        assert usuario.password != "SecurePass789!"  # debe estar hasheada
        assert usuario.password.startswith("argon2")  # debe ser Argon2

    def test_create_usuario_genera_auditlog(self, authenticated_client):
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
        """Si no se envía password, el formulario debe rechazar la creación."""
        data = {
            "email": "nopass@test.com",
            "nombre": "No Pass",
            "rol": Usuario.Rol.VENDEDOR,
        }
        authenticated_client.post(reverse("usuario_create"), data, follow=True)
        assert not UsuarioModel.objects.filter(email="nopass@test.com").exists(), (
            "Se creó usuario sin contraseña - VULNERABILIDAD: password debería ser obligatorio"
        )
