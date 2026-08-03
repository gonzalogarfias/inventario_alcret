import pytest

from apps.alertas.models import Alerta, AlertaConfig


@pytest.mark.django_db
class TestAlertaConfig:
    def test_crear_config(self, producto):
        config = AlertaConfig.objects.create(producto=producto, umbral_minimo=10)
        assert config.umbral_minimo == 10
        assert config.activo is True

    def test_str_con_producto(self, producto):
        config = AlertaConfig.objects.create(producto=producto, umbral_minimo=5)
        assert producto.nombre in str(config)

    def test_str_global(self):
        config = AlertaConfig.objects.create(umbral_minimo=5)
        assert "global" in str(config)

    def test_unique_together_producto(self, producto):
        AlertaConfig.objects.create(producto=producto, umbral_minimo=10)
        with pytest.raises(Exception):  # IntegrityError
            AlertaConfig.objects.create(producto=producto, umbral_minimo=20)


@pytest.mark.django_db
class TestAlerta:
    def test_crear_alerta(self, producto):
        alerta = Alerta.objects.create(
            producto=producto,
            mensaje="Stock bajo",
            estado=Alerta.Estado.PENDIENTE,
        )
        assert alerta.estado == Alerta.Estado.PENDIENTE
        assert alerta.resuelta_en is None

    def test_estado_choices(self):
        for valor, _ in Alerta.Estado.choices:
            assert isinstance(valor, str)

    def test_str(self, producto):
        alerta = Alerta.objects.create(
            producto=producto,
            mensaje="Mensaje de prueba largo para truncamiento",
            estado=Alerta.Estado.PENDIENTE,
        )
        assert "[PENDIENTE]" in str(alerta)
        assert "Mensaje de prueba" in str(alerta)

    def test_ordering(self, producto):
        from datetime import timedelta

        from django.utils import timezone
        a1 = Alerta.objects.create(producto=producto, mensaje="Primera", estado=Alerta.Estado.PENDIENTE)
        a1.created_at = timezone.now() - timedelta(hours=1)
        a1.save()
        a2 = Alerta.objects.create(producto=producto, mensaje="Segunda", estado=Alerta.Estado.PENDIENTE)
        alertas = list(Alerta.objects.all())
        assert alertas[0] == a2
        assert alertas[1] == a1
