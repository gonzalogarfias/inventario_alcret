import json

import pytest
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

    def test_datos_dashboard_estructura_correcta(self, authenticated_client):
        response = authenticated_client.get(reverse("datos_dashboard"))
        data = json.loads(response.content)
        assert "stock_por_categoria" in data
        assert "movimientos_por_dia" in data
        assert "stock_por_almacen" in data
        assert "productos_bajo_stock" in data
        assert "movimientos_por_tipo" in data

    def test_datos_dashboard_con_datos(self, authenticated_client, producto, almacen, usuario_admin):
        Movimiento.objects.create(tipo=Movimiento.Tipo.ENTRADA, producto=producto, almacen=almacen, cantidad=100, realizada_por=usuario_admin)
        response = authenticated_client.get(reverse("datos_dashboard"))
        data = json.loads(response.content)
        assert len(data["movimientos_por_tipo"]) > 0
