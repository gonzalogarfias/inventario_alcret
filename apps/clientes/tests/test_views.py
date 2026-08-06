import pytest
from django.urls import reverse

from apps.clientes.models import Cliente


@pytest.mark.django_db
class TestClienteViews:
    def test_list_requiere_login(self, client):
        response = client.get(reverse("cliente_list"))
        assert response.status_code == 302

    def test_list_muestra_clientes(self, authenticated_client, client_vendedor):
        Cliente.objects.create(
            empresa="Empresa Test SA",
            nombre="Contacto Test",
            email="contacto@test.com",
        )
        response = authenticated_client.get(reverse("cliente_list"))
        assert response.status_code == 200
        assert b"Empresa Test SA" in response.content

    def test_create_requiere_login(self, client):
        response = client.get(reverse("cliente_create"))
        assert response.status_code == 302

    def test_create_cliente(self, authenticated_client):
        response = authenticated_client.post(
            reverse("cliente_create"),
            {
                "empresa": "Nueva Empresa SA",
                "nombre": "Nuevo Contacto",
                "email": "nuevo@empresa.com",
                "telefono": "+5281999888777",
                "rfc": "NES920101ABC",
            },
        )
        assert response.status_code == 302
        assert Cliente.objects.filter(email="nuevo@empresa.com").exists()

    def test_create_rfc_invalido(self, authenticated_client):
        response = authenticated_client.post(
            reverse("cliente_create"),
            {
                "empresa": "Empresa SA",
                "nombre": "Contacto",
                "email": "x@empresa.com",
                "rfc": "MAL",
            },
        )
        assert response.status_code == 200
        assert not Cliente.objects.filter(email="x@empresa.com").exists()

    def test_update_cliente(self, authenticated_client):
        cliente = Cliente.objects.create(
            empresa="Empresa SA",
            nombre="Contacto",
            email="c@empresa.com",
        )
        response = authenticated_client.post(
            reverse("cliente_update", args=[cliente.pk]),
            {
                "empresa": "Empresa SA",
                "nombre": "Contacto Actualizado",
                "email": "c@empresa.com",
                "activo": "on",
            },
        )
        assert response.status_code == 302
        cliente.refresh_from_db()
        assert cliente.nombre == "Contacto Actualizado"
