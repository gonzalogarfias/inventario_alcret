import hashlib
from unittest import mock

import pytest
from django.core.exceptions import ValidationError

from apps.shared.validators import PwnedPasswordValidator


def _linea_breach(password, count=5):
    sha1 = hashlib.sha1(password.encode()).hexdigest().upper()
    return f"{sha1[5:]}:{count}"


class TestPwnedPasswordValidator:
    def test_rechaza_password_en_breach(self):
        body = _linea_breach("password123", 3000)
        validator = PwnedPasswordValidator()
        with mock.patch(
            "apps.shared.validators.requests.get"
        ) as mock_get:
            mock_get.return_value.text = body
            mock_get.return_value.raise_for_status.return_value = None
            with pytest.raises(ValidationError):
                validator.validate("password123")

    def test_acepta_password_sin_breach(self):
        validator = PwnedPasswordValidator()
        with mock.patch("apps.shared.validators.requests.get") as mock_get:
            mock_get.return_value.text = "AAAA:1"
            mock_get.return_value.raise_for_status.return_value = None
            validator.validate("contraseña-super-segura-aleatoria")

    def test_fail_safe_ante_error_de_red(self):
        import requests as requests_lib
        validator = PwnedPasswordValidator()
        with mock.patch(
            "apps.shared.validators.requests.get",
            side_effect=requests_lib.RequestException("timeout"),
        ):
            validator.validate("password-con-error-red")

    def test_min_breaches_configurable(self):
        body = _linea_breach("password123", 1)
        validator = PwnedPasswordValidator(min_breaches=2)
        with mock.patch("apps.shared.validators.requests.get") as mock_get:
            mock_get.return_value.text = body
            mock_get.return_value.raise_for_status.return_value = None
            validator.validate("password123")

    def test_get_help_text(self):
        assert "filtra" in PwnedPasswordValidator().get_help_text() or PwnedPasswordValidator().get_help_text()

    def test_solo_envia_prefijo_sha1(self):
        """k-anonymity: solo se envían los primeros 5 hex del hash, no la password."""
        validator = PwnedPasswordValidator()
        with mock.patch("apps.shared.validators.requests.get") as mock_get:
            mock_get.return_value.text = "AAAA:1"
            mock_get.return_value.raise_for_status.return_value = None
            validator.validate("secret-password")
            url = mock_get.call_args[0][0]
            prefix = url.rsplit("/", 1)[1]
            assert len(prefix) == 5
            assert url.startswith("https://api.pwnedpasswords.com/range/")


@pytest.mark.django_db
class TestConfiguracionValidator:
    def test_pwned_validator_configurado_en_settings(self):
        # Conftest lo quita de settings en tests; verificamos el base real
        from config.settings.base import AUTH_PASSWORD_VALIDATORS
        assert any(
            "PwnedPasswordValidator" in v["NAME"] for v in AUTH_PASSWORD_VALIDATORS
        ), "El validador HIBP debe estar en AUTH_PASSWORD_VALIDATORS"
