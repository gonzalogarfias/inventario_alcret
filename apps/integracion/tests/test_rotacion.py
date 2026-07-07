from datetime import timedelta

import pytest
from django.utils import timezone

from apps.integracion.models import ClaveCRM


@pytest.mark.django_db
class TestClaveCRMModel:
    def test_crear_clave_activa(self):
        clave = ClaveCRM.objects.create(
            clave_publica="test-key-001",
            hash_clave="abc123hash",
            activa=True,
            expira_en=timezone.now() + timedelta(days=90),
        )
        assert clave.activa is True
        assert str(clave.clave_publica) == "test-key-001"

    def test_nueva_clave_desactiva_anterior(self):
        vieja = ClaveCRM.objects.create(
            clave_publica="clave-vieja",
            hash_clave="hash-viejo",
            activa=True,
            expira_en=timezone.now() + timedelta(days=90),
        )
        assert vieja.activa is True

        nueva = ClaveCRM.objects.create(
            clave_publica="clave-nueva",
            hash_clave="hash-nuevo",
            activa=True,
            expira_en=timezone.now() + timedelta(days=90),
        )
        vieja.refresh_from_db()
        assert vieja.activa is False
        assert nueva.activa is True

    def test_str_representation(self):
        clave = ClaveCRM.objects.create(
            clave_publica="test-key-002",
            hash_clave="hash123",
            activa=True,
            expira_en=timezone.now() + timedelta(days=90),
        )
        assert "test-key-002" in str(clave)
        assert "activa" in str(clave)
