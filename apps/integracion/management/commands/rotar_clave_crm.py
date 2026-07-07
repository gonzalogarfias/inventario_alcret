import hashlib
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.integracion.models import ClaveCRM

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Rota la clave HMAC del CRM: genera una nueva, la activa, y desactiva la anterior."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dias-expiracion",
            type=int,
            default=90,
            help="Días de validez de la nueva clave (default: 90)",
        )
        parser.add_argument(
            "--actualizar-env",
            action="store_true",
            help="Actualizar el valor de CRM_HMAC_SECRET en el archivo .env",
        )

    def handle(self, *args, **options):
        dias = options["dias_expiracion"]
        secreto_nuevo = secrets.token_hex(32)
        clave_publica = secrets.token_hex(8)
        hash_clave = hashlib.sha256(secreto_nuevo.encode()).hexdigest()
        expira_en = timezone.now() + timedelta(days=dias)

        ClaveCRM.objects.create(
            clave_publica=clave_publica,
            hash_clave=hash_clave,
            activa=True,
            expira_en=expira_en,
        )

        logger.info("Clave CRM rotada. ID público: %s, expira: %s", clave_publica, expira_en)
        self.stdout.write(self.style.SUCCESS("Clave CRM rotada exitosamente"))
        self.stdout.write(f"  ID público: {clave_publica}")
        self.stdout.write(f"  Expira: {expira_en}")
        self.stdout.write(f"  Nuevo secreto (CRM_HMAC_SECRET): {secreto_nuevo}")
        self.stdout.write(self.style.WARNING("GUARDA este secreto de forma segura."))

        if options["actualizar_env"]:
            env_path = settings.BASE_DIR / ".env"
            if env_path.exists():
                contenido = env_path.read_text(encoding="utf-8")
                import re
                nuevo = re.sub(
                    r"^CRM_HMAC_SECRET=.*",
                    f"CRM_HMAC_SECRET={secreto_nuevo}",
                    contenido,
                    flags=re.MULTILINE,
                )
                env_path.write_text(nuevo, encoding="utf-8")
                self.stdout.write(self.style.SUCCESS(".env actualizado con el nuevo secreto."))
            else:
                self.stdout.write(self.style.WARNING("Archivo .env no encontrado."))
