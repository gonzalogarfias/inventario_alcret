import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestRBACInventario:
    def test_vendedor_no_puede_crear_producto(self, client, usuario_vendedor, categoria):
        client.force_login(usuario_vendedor)
        response = client.post(reverse("producto_create"), {
            "sku": "VEND-TEST",
            "nombre": "Producto Vendedor",
            "categoria": categoria.pk,
            "precio_venta": 50,
        })
        assert response.status_code in (302, 403)

    def test_almacenista_puede_crear_producto(self, client, usuario_almacenista, categoria):
        client.force_login(usuario_almacenista)
        response = client.post(reverse("producto_create"), {
            "sku": "ALMAC-TEST",
            "nombre": "Producto Almacenista",
            "categoria": categoria.pk,
            "precio_venta": 50,
        })
        assert response.status_code in (200, 302)

    def test_admin_puede_crear_producto(self, authenticated_client, categoria):
        response = authenticated_client.post(reverse("producto_create"), {
            "sku": "ADMIN-TEST",
            "nombre": "Producto Admin",
            "categoria": categoria.pk,
            "precio_venta": 50,
        })
        assert response.status_code in (200, 302)

    def test_vendedor_no_puede_crear_categoria(self, client, usuario_vendedor):
        client.force_login(usuario_vendedor)
        response = client.post(reverse("categoria_create"), {
            "nombre": "Cat Vendedor",
            "descripcion": "Test",
        })
        assert response.status_code in (302, 403)

    def test_vendedor_no_puede_crear_almacen(self, client, usuario_vendedor):
        client.force_login(usuario_vendedor)
        response = client.post(reverse("almacen_create"), {
            "nombre": "Almacén Vendedor",
            "ubicacion": "Test",
        })
        assert response.status_code in (302, 403)

    def test_vendedor_puede_ver_lista_productos(self, client, usuario_vendedor):
        client.force_login(usuario_vendedor)
        response = client.get(reverse("producto_list"))
        assert response.status_code == 200
