import pytest
from django.conf import settings


@pytest.mark.django_db
class TestSecuritySettings:
    def test_password_hasher_es_argon2(self):
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

    def test_session_expire_at_browser_close(self):
        assert settings.SESSION_EXPIRE_AT_BROWSER_CLOSE is True

    def test_csrf_cookie_httponly(self):
        assert settings.CSRF_COOKIE_HTTPONLY is True

    def test_x_frame_options_deny(self):
        assert settings.X_FRAME_OPTIONS == "DENY"

    def test_secure_hsts_enabled(self):
        assert settings.SECURE_HSTS_SECONDS >= 31536000

    def test_secure_browser_xss_filter(self):
        assert settings.SECURE_BROWSER_XSS_FILTER is True

    def test_secure_content_type_nosniff(self):
        assert settings.SECURE_CONTENT_TYPE_NOSNIFF is True

    def test_axes_failure_limit_5(self):
        assert settings.AXES_FAILURE_LIMIT == 5

    def test_axes_cooloff_time_1_hour(self):
        assert settings.AXES_COOLOFF_TIME == 1

    def test_password_reset_timeout_900(self):
        assert settings.PASSWORD_RESET_TIMEOUT == 900

    def test_auth_user_model_custom(self):
        assert settings.AUTH_USER_MODEL == "usuarios.Usuario"

    def test_auth_backends_incluye_axes_y_guardian(self):
        backends = settings.AUTHENTICATION_BACKENDS
        assert "axes.backends.AxesBackend" in backends
        assert "guardian.backends.ObjectPermissionBackend" in backends
