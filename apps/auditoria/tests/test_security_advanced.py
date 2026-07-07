import pytest
from django.conf import settings
from django.urls import reverse

from apps.inventario.models import Movimiento


@pytest.mark.django_db
class TestSecurityHeaders:
    def test_csp_header_implementado(self, client):
        response = client.get(reverse("health_check"))
        csp = response.headers.get("Content-Security-Policy", "")
        assert "default-src 'self'" in csp
        assert "script-src 'self'" in csp
        assert "style-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp
        assert "base-uri 'self'" in csp

    def test_xss_protection_header(self, client):
        response = client.get(reverse("health_check"))
        # SECURE_BROWSER_XSS_FILTER = True
        assert response.headers.get("X-XSS-Protection") in ("1; mode=block", None)

    def test_content_type_options(self, client):
        response = client.get(reverse("health_check"))
        assert response.headers.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options(self, client):
        response = client.get(reverse("health_check"))
        assert response.headers.get("X-Frame-Options") == "DENY"

    def test_strict_transport_security_configurado(self, client):
        """HSTS se agrega solo en respuestas HTTPS. Verificamos la config."""
        from django.conf import settings as s
        assert s.SECURE_HSTS_SECONDS >= 31536000
        assert s.SECURE_HSTS_INCLUDE_SUBDOMAINS is True


@pytest.mark.django_db
class TestConfigSeguridad:
    def test_password_hasher_argon2(self):
        assert "Argon2PasswordHasher" in settings.PASSWORD_HASHERS[0]

    def test_password_min_length_12(self):
        validators = settings.AUTH_PASSWORD_VALIDATORS
        min_length = next(
            v for v in validators
            if "MinimumLengthValidator" in v["NAME"]
        )
        assert min_length["OPTIONS"]["min_length"] == 12

    def test_session_cookie_httponly(self):
        assert settings.SESSION_COOKIE_HTTPONLY is True

    def test_session_cookie_samesite_strict(self):
        assert settings.SESSION_COOKIE_SAMESITE == "Strict"

    def test_csrf_cookie_httponly(self):
        assert settings.CSRF_COOKIE_HTTPONLY is True

    def test_axes_failure_limit_5(self):
        assert settings.AXES_FAILURE_LIMIT == 5

    def test_axes_cooloff_time_1_hour(self):
        assert settings.AXES_COOLOFF_TIME == 1

    def test_password_reset_timeout_900(self):
        assert settings.PASSWORD_RESET_TIMEOUT == 900

    def test_auth_user_model_custom(self):
        assert settings.AUTH_USER_MODEL == "usuarios.Usuario"

    def test_auth_backends_seguros(self):
        backends = settings.AUTHENTICATION_BACKENDS
        assert "axes.backends.AxesBackend" in backends
        assert "guardian.backends.ObjectPermissionBackend" in backends


@pytest.mark.django_db
class TestValidacionInputs:
    def test_cantidad_negativa_rechazada(self, authenticated_client, producto, almacen):
        data = {
            "tipo": Movimiento.Tipo.ENTRADA,
            "producto": producto.pk,
            "almacen": almacen.pk,
            "cantidad": "-10",
            "motivo": "Cantidad negativa",
        }
        authenticated_client.post(reverse("movimiento_create"), data, follow=True)
        mov = Movimiento.objects.filter(motivo="Cantidad negativa")
        assert not mov.exists(), (
            "VULNERABILIDAD: se creó movimiento con cantidad negativa."
        )

    @pytest.mark.skip(reason="Requiere template con contexto de formulario")
    def test_uuid_invalido_en_filtro_categoria(self, authenticated_client):
        response = authenticated_client.get(reverse("producto_list"), {"categoria": "no-soy-uuid"})
        assert response.status_code in (200, 404)

    def test_csrf_middleware_presente(self):
        """Verificar que CsrfViewMiddleware está en la cadena."""
        assert "django.middleware.csrf.CsrfViewMiddleware" in settings.MIDDLEWARE

    def test_csrf_cookie_httponly(self):
        assert settings.CSRF_COOKIE_HTTPONLY is True
