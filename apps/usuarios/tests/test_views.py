import pytest
from django.urls import reverse

from apps.usuarios.models import Usuario


@pytest.mark.django_db
class TestDashboardView:
    def test_dashboard_requiere_login(self, client):
        response = client.get(reverse("dashboard"))
        assert response.status_code == 302
        assert "/accounts/login/" in response.url

    def test_dashboard_autenticado(self, authenticated_client):
        response = authenticated_client.get(reverse("dashboard"))
        assert response.status_code == 200
        assert "total_productos" in response.context
        assert "total_almacenes" in response.context
        assert "total_usuarios" in response.context


@pytest.mark.django_db
class TestUsuarioListView:
    def test_lista_requiere_login(self, client):
        response = client.get(reverse("usuario_list"))
        assert response.status_code == 302

    def test_lista_requiere_permiso_gestionar(self, client, usuario_vendedor):
        client.force_login(usuario_vendedor)
        response = client.get(reverse("usuario_list"))
        assert response.status_code == 403

    def test_lista_con_permiso_devuelve_200(self, authenticated_client, usuario_vendedor):
        response = authenticated_client.get(reverse("usuario_list"))
        assert response.status_code == 200
        assert "usuarios" in response.context

    def test_lista_filtra_por_email(self, authenticated_client):
        Usuario.objects.create_user(
            email="filtro@test.com", nombre="Filtro", rol=Usuario.Rol.VENDEDOR, password="Pass123!"
        )
        response = authenticated_client.get(reverse("usuario_list"), {"q": "filtro"})
        assert response.status_code == 200
        assert response.context["usuarios"].count() >= 1

    def test_lista_paginada(self, authenticated_client):
        response = authenticated_client.get(reverse("usuario_list"))
        paginator = response.context["paginator"]
        assert paginator.per_page == 20


@pytest.mark.django_db
class TestUsuarioCreateView:
    def test_create_requiere_login(self, client):
        response = client.get(reverse("usuario_create"))
        assert response.status_code == 302

    def test_create_requiere_permiso(self, client, usuario_vendedor):
        client.force_login(usuario_vendedor)
        response = client.get(reverse("usuario_create"))
        assert response.status_code == 403

    def test_create_usuario_exitoso(self, authenticated_client):
        data = {
            "email": "nuevo@test.com",
            "nombre": "Nuevo Usuario",
            "rol": Usuario.Rol.VENDEDOR,
            "password": "PassWord123!",
        }
        response = authenticated_client.post(reverse("usuario_create"), data, follow=True)
        assert response.status_code == 200
        assert Usuario.objects.filter(email="nuevo@test.com").exists()

    def test_create_con_password_setea_hash(self, authenticated_client):
        data = {
            "email": "hash@test.com",
            "nombre": "Hash Check",
            "rol": Usuario.Rol.ALMACENISTA,
            "password": "StrongPass456!",
        }
        authenticated_client.post(reverse("usuario_create"), data)
        usuario = Usuario.objects.get(email="hash@test.com")
        assert usuario.password != "StrongPass456!"


@pytest.mark.django_db
class TestUsuarioUpdateView:
    def test_update_requiere_login(self, client, usuario_admin):
        response = client.get(reverse("usuario_update", args=[usuario_admin.pk]))
        assert response.status_code == 302

    def test_update_requiere_permiso(self, client, usuario_admin, usuario_vendedor):
        client.force_login(usuario_vendedor)
        response = client.get(reverse("usuario_update", args=[usuario_admin.pk]))
        assert response.status_code == 403

    def test_update_actualiza_datos(self, authenticated_client, usuario_vendedor):
        data = {
            "email": "vendedor@test.com",
            "nombre": "Vendedor Modificado",
            "rol": Usuario.Rol.VENDEDOR,
        }
        response = authenticated_client.post(
            reverse("usuario_update", args=[usuario_vendedor.pk]),
            data,
            follow=True,
        )
        assert response.status_code == 200
        usuario_vendedor.refresh_from_db()
        assert usuario_vendedor.nombre == "Vendedor Modificado"
