import pytest
from django.urls import reverse

from apps.clientes.models import Cliente
from apps.cotizaciones.models import Cotizacion
from apps.inventario.models import Producto


@pytest.fixture
def cliente(db):  # noqa: ARG001
    return Cliente.objects.create(
        empresa="Empresa Test SA",
        nombre="Contacto Test",
        email="contacto@test.com",
    )


@pytest.fixture
def unidad(db, categoria):  # noqa: ARG001
    return Producto.objects.create(
        sku="KW-TEST-001",
        nombre="Kenworth Test",
        vin="3HHDMABN7RL999999",
        categoria=categoria,
        precio_venta=1000000.00,
    )


@pytest.mark.django_db
class TestCotizacionViews:
    def test_list_requiere_login(self, client):
        response = client.get(reverse("cotizacion_list"))
        assert response.status_code == 302

    def test_list_muestra_cotizaciones(self, authenticated_client, cliente, unidad, usuario_vendedor):
        Cotizacion.objects.create(
            folio="COT-00001",
            cliente=cliente,
            monto=1000000.00,
            esquema=Cotizacion.Esquema.CREDITO,
            unidad_interes=unidad,
            vendedor=usuario_vendedor,
        )
        response = authenticated_client.get(reverse("cotizacion_list"))
        assert response.status_code == 200
        assert b"COT-00001" in response.content

    def test_create_requiere_login(self, client):
        response = client.get(reverse("cotizacion_create"))
        assert response.status_code == 302

    def test_create_cotizacion(self, authenticated_client, cliente, unidad, usuario_vendedor):
        response = authenticated_client.post(
            reverse("cotizacion_create"),
            {
                "folio": "",
                "cliente": str(cliente.pk),
                "monto": "1000000.00",
                "esquema": Cotizacion.Esquema.CREDITO,
                "unidad_interes": str(unidad.pk),
                "vendedor": str(usuario_vendedor.pk),
                "estado": Cotizacion.Estado.ENVIADA,
                "observaciones": "",
            },
        )
        assert response.status_code == 302
        cotizacion = Cotizacion.objects.first()
        assert cotizacion is not None
        assert cotizacion.folio == "COT-00001"
        assert cotizacion.unidad_interes == unidad

    def test_update_cotizacion(self, authenticated_client, cliente, unidad, usuario_vendedor):
        cotizacion = Cotizacion.objects.create(
            folio="COT-00002",
            cliente=cliente,
            monto=500000.00,
            esquema=Cotizacion.Esquema.CONTADO,
            unidad_interes=unidad,
            vendedor=usuario_vendedor,
        )
        response = authenticated_client.post(
            reverse("cotizacion_update", args=[cotizacion.pk]),
            {
                "folio": "COT-00002",
                "cliente": str(cliente.pk),
                "monto": "600000.00",
                "esquema": Cotizacion.Esquema.CONTADO,
                "unidad_interes": str(unidad.pk),
                "vendedor": str(usuario_vendedor.pk),
                "estado": Cotizacion.Estado.GANADA,
                "observaciones": "",
            },
        )
        assert response.status_code == 302
        cotizacion.refresh_from_db()
        assert cotizacion.monto == 600000.00
        assert cotizacion.estado == Cotizacion.Estado.GANADA
