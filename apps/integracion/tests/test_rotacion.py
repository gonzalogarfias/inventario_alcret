import hashlib
from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.integracion.models import ClaveCRM


def _hash_clave(secreto="secreto-de-test"):
    return hashlib.sha256(secreto.encode()).hexdigest()


@pytest.mark.django_db
class TestClaveCRMModel:
    def test_crear_clave_activa(self):
        clave = ClaveCRM.objects.create(
            clave_publica="test-key-001",
            hash_clave=_hash_clave(),
            activa=True,
            expira_en=timezone.now() + timedelta(days=90),
        )
        assert clave.activa is True
        assert str(clave.clave_publica) == "test-key-001"

    def test_nueva_clave_desactiva_anterior(self):
        vieja = ClaveCRM.objects.create(
            clave_publica="clave-vieja",
            hash_clave=_hash_clave("vieja"),
            activa=True,
            expira_en=timezone.now() + timedelta(days=90),
        )
        assert vieja.activa is True

        nueva = ClaveCRM.objects.create(
            clave_publica="clave-nueva",
            hash_clave=_hash_clave("nueva"),
            activa=True,
            expira_en=timezone.now() + timedelta(days=90),
        )
        vieja.refresh_from_db()
        assert vieja.activa is False
        assert nueva.activa is True

    def test_str_representation(self):
        clave = ClaveCRM.objects.create(
            clave_publica="test-key-002",
            hash_clave=_hash_clave(),
            activa=True,
            expira_en=timezone.now() + timedelta(days=90),
        )
        assert "test-key-002" in str(clave)
        assert "activa" in str(clave)

    def test_rechaza_hash_invalido(self):
        with pytest.raises(ValidationError):
            ClaveCRM.objects.create(
                clave_publica="test-key-003",
                hash_clave="no-es-un-hash",
                activa=True,
                expira_en=timezone.now() + timedelta(days=90),
            )

    def test_rechaza_expiracion_pasada(self):
        with pytest.raises(ValidationError):
            ClaveCRM.objects.create(
                clave_publica="test-key-004",
                hash_clave=_hash_clave(),
                activa=True,
                expira_en=timezone.now() - timedelta(days=1),
            )

    def test_permite_expirar_clave_existente(self):
        """Un registro existente puede vencerse aunque su expira_en ya pasó."""
        clave = ClaveCRM.objects.create(
            clave_publica="test-key-005",
            hash_clave=_hash_clave(),
            activa=True,
            expira_en=timezone.now() + timedelta(days=90),
        )
        clave.expira_en = timezone.now() - timedelta(days=1)
        clave.activa = False
        clave.rotada_en = timezone.now()
        clave.save()
        clave.refresh_from_db()
        assert clave.activa is False
