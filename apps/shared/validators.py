"""Validador de contraseñas contra filtraciones conocidas (Have I Been Pwned).

Protocolo k-anonymity: se envía solo el prefijo SHA-1 (5 caracteres hex) y se
compara contra la lista de sufijos devuelta. La contraseña nunca sale del
servidor.
"""

import hashlib

import requests
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class PwnedPasswordValidator:
    """Valida que la contraseña no figure en filtraciones conocidas.

    Configurables vía settings:
      - PWNED_VALIDATOR_TIMEOUT (segundos, default 2.0)
      - PWNED_VALIDATOR_FAIL_SAFE (default True: si la API no responde,
        no bloquea al usuario)
      - PWNED_VALIDATOR_MIN_BREACHES (default 1)
    """

    url = "https://api.pwnedpasswords.com/range/{prefix}"

    def __init__(self, min_breaches=1, timeout=2.0, fail_safe=True):
        self.min_breaches = getattr(settings, "PWNED_VALIDATOR_MIN_BREACHES", min_breaches)
        self.timeout = getattr(settings, "PWNED_VALIDATOR_TIMEOUT", timeout)
        self.fail_safe = getattr(settings, "PWNED_VALIDATOR_FAIL_SAFE", fail_safe)

    def validate(self, password, user=None):  # noqa: ARG002
        if self._breach_count(password) >= self.min_breaches:
            raise ValidationError(
                _("Esta contraseña apareció en una filtración de datos conocida. Elige otra.")
            )

    def get_help_text(self):
        return _("No uses contraseñas que hayan aparecido en filtraciones de datos.")

    def _breach_count(self, password):
        sha1 = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
        prefix, suffix = sha1[:5], sha1[5:]
        try:
            resp = requests.get(self.url.format(prefix=prefix), timeout=self.timeout)
            resp.raise_for_status()
        except requests.RequestException:
            if self.fail_safe:
                return 0
            raise ValidationError(
                _("No se pudo verificar la seguridad de la contraseña. Inténtalo de nuevo.")
            )
        for line in resp.text.splitlines():
            suf, count = line.split(":", 1)
            if suf.upper() == suffix:
                return int(count)
        return 0
