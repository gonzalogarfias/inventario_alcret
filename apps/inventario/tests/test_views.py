from decimal import Decimal

import pytest
from django.urls import reverse

from apps.inventario.models import Almacen, Categoria, Movimiento, Producto


@pytest.mark.django_db
class TestProductoViews:
    def test_list_requiere_login(self, client):
        response = client.get(reverse("producto_list"))
        assert response.status_code == 302

    def test_list_autenticado(self, authenticated_client):
        response = authenticated_client.get(reverse("producto_list"))
        assert response.status_code == 200
        assert "productos" in response.context

    def test_create_requiere_login(self, client):
        response = client.get(reverse("producto_create"))
        assert response.status_code == 302

    def test_create_producto(self, authenticated_client, categoria):
        data = {
            "sku": "NUEVO-001",
            "nombre": "Producto Nuevo",
            "categoria": categoria.pk,
            "precio_venta": "250.00",
            "stock_minimo": "5",
        }
        response = authenticated_client.post(reverse("producto_create"), data, follow=True)
        assert response.status_code == 200
        assert Producto.objects.filter(sku="NUEVO-001").exists()

    def test_detail_requiere_login(self, client, producto):
        response = client.get(reverse("producto_detail", args=[producto.pk]))
        assert response.status_code == 302

    def test_detail_muestra_stock_y_movimientos(self, authenticated_client, producto, almacen, usuario_admin):
        Movimiento.objects.create(tipo=Movimiento.Tipo.ENTRADA, producto=producto, almacen=almacen, cantidad=10, realizada_por=usuario_admin)
        response = authenticated_client.get(reverse("producto_detail", args=[producto.pk]))
        assert response.status_code == 200
        assert response.context["producto"] == producto
        assert len(response.context["stocks"]) >= 0
        assert len(response.context["movimientos"]) >= 1

    def test_update_producto(self, authenticated_client, producto):
        data = {
            "sku": producto.sku,
            "nombre": "Producto Modificado",
            "categoria": producto.categoria_id,
            "precio_venta": "300.00",
            "stock_minimo": "10",
            "activo": True,
        }
        response = authenticated_client.post(reverse("producto_update", args=[producto.pk]), data, follow=True)
        assert response.status_code == 200
        producto.refresh_from_db()
        assert producto.nombre == "Producto Modificado"


@pytest.mark.django_db
class TestCategoriaViews:
    def test_list_autenticado(self, authenticated_client):
        response = authenticated_client.get(reverse("categoria_list"))
        assert response.status_code == 200

    def test_create_categoria(self, authenticated_client):
        data = {"nombre": "Nueva Cat", "descripcion": "Test"}
        response = authenticated_client.post(reverse("categoria_create"), data, follow=True)
        assert response.status_code == 200
        assert Categoria.objects.filter(nombre="Nueva Cat").exists()


@pytest.mark.django_db
class TestAlmacenViews:
    def test_list_autenticado(self, authenticated_client):
        response = authenticated_client.get(reverse("almacen_list"))
        assert response.status_code == 200

    def test_create_almacen(self, authenticated_client):
        data = {"nombre": "Almacén Nuevo", "ubicacion": "Zona Test"}
        response = authenticated_client.post(reverse("almacen_create"), data, follow=True)
        assert response.status_code == 200
        assert Almacen.objects.filter(nombre="Almacén Nuevo").exists()


@pytest.mark.django_db
class TestMovimientoViews:
    def test_list_requiere_login(self, client):
        response = client.get(reverse("movimiento_list"))
        assert response.status_code == 302

    def test_list_autenticado(self, authenticated_client, producto, almacen, usuario_admin):
        Movimiento.objects.create(tipo=Movimiento.Tipo.ENTRADA, producto=producto, almacen=almacen, cantidad=5, realizada_por=usuario_admin)
        response = authenticated_client.get(reverse("movimiento_list"))
        assert response.status_code == 200
        assert "movimientos" in response.context

    def test_create_movimiento_entrada(self, authenticated_client, producto, almacen):
        data = {
            "tipo": Movimiento.Tipo.ENTRADA,
            "producto": producto.pk,
            "almacen": almacen.pk,
            "cantidad": "50",
            "motivo": "Compra proveedor",
        }
        response = authenticated_client.post(reverse("movimiento_create"), data, follow=True)
        assert response.status_code == 200
        assert Movimiento.objects.filter(producto=producto, tipo=Movimiento.Tipo.ENTRADA).exists()

    def test_create_movimiento_asigna_usuario(self, authenticated_client, producto, almacen, usuario_admin):
        data = {
            "tipo": Movimiento.Tipo.ENTRADA,
            "producto": producto.pk,
            "almacen": almacen.pk,
            "cantidad": "10",
            "motivo": "Test usuario",
        }
        authenticated_client.post(reverse("movimiento_create"), data)
        mov = Movimiento.objects.filter(producto=producto).latest("created_at")
        assert mov.realizada_por == usuario_admin

    def test_salida_se_guarda_como_negativo(self, authenticated_client, producto, almacen):
        data = {
            "tipo": Movimiento.Tipo.SALIDA,
            "producto": producto.pk,
            "almacen": almacen.pk,
            "cantidad": "10",
            "motivo": "Venta",
        }
        authenticated_client.post(reverse("movimiento_create"), data)
        mov = Movimiento.objects.filter(producto=producto).latest("created_at")
        assert mov.cantidad == Decimal("-10")


@pytest.mark.django_db
class TestExportViews:
    def test_exportar_productos_csv(self, authenticated_client, producto):
        response = authenticated_client.get(reverse("exportar_productos_csv"))
        assert response.status_code == 200
        assert response["Content-Type"] == "text/csv"
        assert "productos.csv" in response["Content-Disposition"]

    def test_exportar_productos_excel(self, authenticated_client, producto):
        response = authenticated_client.get(reverse("exportar_productos_excel"))
        assert response.status_code == 200
        assert "application/vnd.openxmlformats" in response["Content-Type"]

    def test_exportar_movimientos_csv(self, authenticated_client, producto, almacen, usuario_admin):
        Movimiento.objects.create(tipo=Movimiento.Tipo.ENTRADA, producto=producto, almacen=almacen, cantidad=5, realizada_por=usuario_admin)
        response = authenticated_client.get(reverse("exportar_movimientos_csv"))
        assert response.status_code == 200
        assert response["Content-Type"] == "text/csv"

    def test_exportar_movimientos_excel(self, authenticated_client, producto, almacen, usuario_admin):
        Movimiento.objects.create(tipo=Movimiento.Tipo.SALIDA, producto=producto, almacen=almacen, cantidad=3, realizada_por=usuario_admin)
        response = authenticated_client.get(reverse("exportar_movimientos_excel"))
        assert response.status_code == 200
        assert "application/vnd.openxmlformats" in response["Content-Type"]

    def test_exportar_productos_requiere_login(self, client):
        response = client.get(reverse("exportar_productos_csv"))
        assert response.status_code == 302
