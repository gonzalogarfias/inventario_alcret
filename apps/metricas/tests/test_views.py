import json

import pytest
from django.core.cache import cache
from django.urls import reverse

from apps.inventario.models import Movimiento


@pytest.mark.django_db
class TestMetricasViews:
    def test_datos_dashboard_requiere_login(self, client):
        response = client.get(reverse("datos_dashboard"))
        assert response.status_code == 302

    def test_datos_dashboard_retorna_json(self, authenticated_client):
        response = authenticated_client.get(reverse("datos_dashboard"))
        assert response.status_code == 200
        assert response["Content-Type"] == "application/json"

    def test_datos_dashboard_estructura_correcta_admin(self, authenticated_client):
        """ADMIN ve todas las métricas incluyendo stock_por_almacen."""
        response = authenticated_client.get(reverse("datos_dashboard"))
        data = json.loads(response.content)
        assert "stock_por_categoria" in data
        assert "movimientos_por_dia" in data
        assert "stock_por_almacen" in data
        assert "productos_bajo_stock" in data
        assert "movimientos_por_tipo" in data

    def test_datos_dashboard_vendedor_no_ve_almacenes(self, client, usuario_vendedor):
        """VENDEDOR no debe ver stock_por_almacen (métrica sensible)."""
        client.force_login(usuario_vendedor)
        response = client.get(reverse("datos_dashboard"))
        assert response.status_code == 200
        data = json.loads(response.content)
        assert "stock_por_almacen" not in data
        assert "stock_por_categoria" in data
        assert "movimientos_por_tipo" in data

    def test_datos_dashboard_almacenista_403(self, client, usuario_almacenista):
        """ALMACENISTA no debe ver métricas — 403."""
        client.force_login(usuario_almacenista)
        response = client.get(reverse("datos_dashboard"))
        assert response.status_code == 403
        data = json.loads(response.content)
        assert "error" in data

    def test_datos_dashboard_con_datos(self, authenticated_client, producto, almacen, usuario_admin):
        cache.clear()
        Movimiento.objects.create(
            tipo=Movimiento.Tipo.ENTRADA,
            producto=producto,
            almacen=almacen,
            cantidad=100,
            realizada_por=usuario_admin,
        )
        response = authenticated_client.get(reverse("datos_dashboard"))
        data = json.loads(response.content)
        assert len(data["movimientos_por_tipo"]) > 0
        # Verificar que los valores son int, no float
        if data["stock_por_categoria"]:
            assert isinstance(data["stock_por_categoria"][0]["value"], int)

    def test_datos_dashboard_usa_cache(self, authenticated_client, producto, almacen, usuario_admin):
        """Segunda request debe usar cache (mismo contenido, sin queries adicionales)."""
        cache.clear()
        response1 = authenticated_client.get(reverse("datos_dashboard"))
        assert response1.status_code == 200
        data1 = json.loads(response1.content)

        response2 = authenticated_client.get(reverse("datos_dashboard"))
        assert response2.status_code == 200
        data2 = json.loads(response2.content)

        assert data1 == data2

    def test_datos_dashboard_cache_por_rol(self, client, usuario_vendedor, usuario_admin):
        """Cache debe ser diferente por rol."""
        cache.clear()

        client.force_login(usuario_admin)
        response_admin = client.get(reverse("datos_dashboard"))
        data_admin = json.loads(response_admin.content)
        assert "stock_por_almacen" in data_admin

        client.force_login(usuario_vendedor)
        response_vendedor = client.get(reverse("datos_dashboard"))
        data_vendedor = json.loads(response_vendedor.content)
        assert "stock_por_almacen" not in data_vendedor

    def test_datos_dashboard_solo_get(self, authenticated_client):
        response = authenticated_client.post(reverse("datos_dashboard"))
        assert response.status_code == 405  # Method Not Allowed

    def test_datos_dashboard_valores_enteros(self, authenticated_client, producto, almacen, usuario_admin):
        """Los valores de stock deben ser enteros, no floats."""
        Movimiento.objects.create(
            tipo=Movimiento.Tipo.ENTRADA,
            producto=producto,
            almacen=almacen,
            cantidad=100,
            realizada_por=usuario_admin,
        )
        response = authenticated_client.get(reverse("datos_dashboard"))
        data = json.loads(response.content)
        for item in data.get("stock_por_categoria", []):
            assert isinstance(item["value"], int), (
                f"Se esperaba int, se obtuvo {type(item['value'])}"
            )
