import pytest
from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.auditoria.models import AuditLog

Usuario = get_user_model()


@pytest.mark.django_db
class TestLoginSignals:
    def test_login_exitoso_crea_auditlog(self):
        Usuario.objects.create_user(
            email="login_ok@test.com", nombre="Login OK",
            rol=Usuario.Rol.VENDEDOR, password="Pass123!",
        )
        client = Client()
        response = client.post(reverse("login"), {"username": "login_ok@test.com", "password": "Pass123!"}, follow=True)
        logs = AuditLog.objects.filter(evento=AuditLog.Evento.LOGIN_OK)
        assert logs.count() >= 1

    def test_login_fallido_crea_auditlog(self):
        client = Client()
        response = client.post(reverse("login"), {"username": "noexiste@test.com", "password": "wrong"})
        logs = AuditLog.objects.filter(evento=AuditLog.Evento.LOGIN_FAIL)
        assert logs.count() >= 1

    def test_auditlog_login_fallido_guarda_username(self):
        client = Client()
        client.post(reverse("login"), {"username": "fallido@test.com", "password": "wrong"})
        log = AuditLog.objects.filter(evento=AuditLog.Evento.LOGIN_FAIL).first()
        assert log is not None
        assert log.datos.get("email") in ("fallido@test.com", "desconocido")
