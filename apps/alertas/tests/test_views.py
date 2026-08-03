import pytest
from django.urls import reverse

from apps.alertas.models import Alerta


@pytest.mark.django_db
class TestAlertaViews:
    def test_resolver_alerta_por_post(self, authenticated_client, producto):
        alerta = Alerta.objects.create(
            producto=producto,
            mensaje="Stock bajo",
            estado=Alerta.Estado.PENDIENTE,
        )
        response = authenticated_client.post(reverse("alerta_resolve", args=[alerta.pk]))
        alerta.refresh_from_db()
        assert response.status_code == 302
        assert alerta.estado == Alerta.Estado.RESUELTA
        assert alerta.resuelta_en is not None

    def test_resolver_alerta_get_devuelve_405(self, authenticated_client, producto):
        alerta = Alerta.objects.create(
            producto=producto,
            mensaje="Stock bajo",
            estado=Alerta.Estado.PENDIENTE,
        )
        response = authenticated_client.get(reverse("alerta_resolve", args=[alerta.pk]))
        assert response.status_code == 405
        alerta.refresh_from_db()
        assert alerta.estado == Alerta.Estado.PENDIENTE

    def test_resolver_alerta_ya_resuelta_no_duplica(self, authenticated_client, producto):
        from django.utils import timezone
        alerta = Alerta.objects.create(
            producto=producto,
            mensaje="Stock bajo",
            estado=Alerta.Estado.RESUELTA,
            resuelta_en=timezone.now(),
        )
        response = authenticated_client.post(reverse("alerta_resolve", args=[alerta.pk]))
        assert response.status_code == 302
        alerta.refresh_from_db()
        assert alerta.estado == Alerta.Estado.RESUELTA
