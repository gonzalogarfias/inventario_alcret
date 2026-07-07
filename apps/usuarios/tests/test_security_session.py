import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse

from apps.auditoria.models import AuditLog

Usuario = get_user_model()


@pytest.mark.django_db
class TestSessionSecurity:
    def test_session_cookie_httponly(self):
        assert settings.SESSION_COOKIE_HTTPONLY is True

    def test_session_cookie_samesite_strict(self):
        assert settings.SESSION_COOKIE_SAMESITE == "Strict"

    def test_session_expire_at_browser_close(self):
        assert settings.SESSION_EXPIRE_AT_BROWSER_CLOSE is True

    def test_csrf_cookie_httponly(self):
        assert settings.CSRF_COOKIE_HTTPONLY is True

    @override_settings(SESSION_COOKIE_SECURE=True, CSRF_COOKIE_SECURE=True)
    def test_cookies_set_secure(self):
        assert settings.SESSION_COOKIE_SECURE is True
        assert settings.CSRF_COOKIE_SECURE is True

    @override_settings(SESSION_COOKIE_SECURE=True)
    def test_login_setea_cookie_segura(self, client):
        Usuario.objects.create_user(
            email="session@test.com", nombre="Session",
            rol=Usuario.Rol.VENDEDOR, password="TestPass123!",
        )
        response = client.post(reverse("login"), {
            "username": "session@test.com", "password": "TestPass123!",
        })
        assert "sessionid" in response.cookies
        assert response.cookies["sessionid"]["httponly"] is True
        assert response.cookies["sessionid"]["samesite"] == "Strict"

    def test_logout_invalida_sesion(self, client, usuario_vendedor):
        client.force_login(usuario_vendedor)
        response = client.get(reverse("dashboard"))
        assert response.status_code == 200
        client.logout()
        response = client.get(reverse("dashboard"))
        assert response.status_code == 302


@pytest.mark.django_db
class TestPasswordResetSecurity:
    def test_reset_respuesta_generica(self, client, usuario_admin):
        response_existe = client.post(reverse("password_reset"), {
            "email": usuario_admin.email,
        }, follow=True)
        response_no_existe = client.post(reverse("password_reset"), {
            "email": "noexiste@nadie.com",
        }, follow=True)
        assert response_existe.status_code == 200
        assert response_no_existe.status_code == 200
        assert response_existe.redirect_chain == response_no_existe.redirect_chain

    def test_reset_timeout_configurado(self):
        assert settings.PASSWORD_RESET_TIMEOUT == 900

    def test_reset_crea_auditlog_requested(self, client, usuario_admin):
        AuditLog.objects.all().delete()
        client.post(reverse("password_reset"), {
            "email": usuario_admin.email,
        })
        logs = AuditLog.objects.filter(
            evento=AuditLog.Evento.PASSWORD_RESET,
            datos__accion="PASSWORD_RESET_REQUESTED",
        )
        assert logs.count() >= 1

    def test_reset_crea_auditlog_completed(self, client, db):
        """Django 4.2: primero GET al token (redirect a set-password),
        luego POST al set-password URL."""
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        usuario = Usuario.objects.create_user(
            email="reset_complete@test.com", nombre="Reset Complete",
            rol=Usuario.Rol.VENDEDOR, password="OldPass123!",
        )
        uidb64 = urlsafe_base64_encode(force_bytes(usuario.pk))
        token = default_token_generator.make_token(usuario)

        step1 = client.get(
            reverse("password_reset_confirm", kwargs={"uidb64": uidb64, "token": token}),
        )
        assert step1.status_code == 302
        set_password_url = step1.url

        step2 = client.post(set_password_url, {
            "new_password1": "NewSecurePass789!",
            "new_password2": "NewSecurePass789!",
        })
        assert step2.status_code == 302

        logs = AuditLog.objects.filter(
            evento=AuditLog.Evento.PASSWORD_RESET,
            datos__accion="PASSWORD_RESET_COMPLETED",
        )
        assert logs.count() >= 1
        usuario.refresh_from_db()
        assert usuario.has_usable_password()

    def test_reset_token_un_solo_uso(self, client, db):
        """Verifica que el token de reset no permite cambiar la password dos veces."""
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        usuario = Usuario.objects.create_user(
            email="unsole@test.com", nombre="Unico Uso",
            rol=Usuario.Rol.VENDEDOR, password="FirstPass123!",
        )
        uidb64 = urlsafe_base64_encode(force_bytes(usuario.pk))
        token = default_token_generator.make_token(usuario)

        resp_token = client.get(
            reverse("password_reset_confirm", kwargs={"uidb64": uidb64, "token": token}),
        )
        client.post(resp_token.url, {
            "new_password1": "NewSecurePass789!",
            "new_password2": "NewSecurePass789!",
        })
        usuario.refresh_from_db()
        old_password = usuario.password

        resp_token2 = client.get(
            reverse("password_reset_confirm", kwargs={"uidb64": uidb64, "token": token}),
        )
        if resp_token2.status_code == 302:
            client.post(resp_token2.url, {
                "new_password1": "AnotherSecurePass1!",
                "new_password2": "AnotherSecurePass1!",
            })
            usuario.refresh_from_db()
            assert usuario.password == old_password, (
                "El token permitió cambiar la password dos veces. VULNERABILIDAD."
            )

    def test_password_change_invalida_sesion(self, client, db):
        """Django invalida la sesión tras cambio de password (redirige a login)."""
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        usuario = Usuario.objects.create_user(
            email="session_inval@test.com", nombre="Session Inval",
            rol=Usuario.Rol.VENDEDOR, password="OldPass123!",
        )
        client.force_login(usuario)
        response = client.get(reverse("dashboard"))
        assert response.status_code == 200

        uidb64 = urlsafe_base64_encode(force_bytes(usuario.pk))
        token = default_token_generator.make_token(usuario)
        resp_token = client.get(
            reverse("password_reset_confirm", kwargs={"uidb64": uidb64, "token": token}),
        )
        client.post(resp_token.url, {
            "new_password1": "NewSecurePass789!",
            "new_password2": "NewSecurePass789!",
        })

        response = client.get(reverse("dashboard"))
        assert response.status_code == 302, (
            "La sesión debería invalidarse tras cambio de password (ARQUITECTURA.md punto 5)."
        )
        assert "/accounts/login/" in response.url
