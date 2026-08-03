import uuid

from django.core.exceptions import ValidationError
from django.db import models

from apps.shared.value_objects import EmailAddress
from apps.shared.value_objects import ValidationError as VOWValidationError


def empty_dict():
    return {}


def empty_list():
    return []


class DashboardConfig(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    config = models.JSONField(default=empty_dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "configuración de dashboard"
        verbose_name_plural = "configuraciones de dashboard"

    def __str__(self):
        return self.nombre


class ReporteProgramado(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=100)
    tipo = models.CharField(
        max_length=50,
        choices=[
            ("EXCEL", "Excel"),
            ("PDF", "PDF"),
            ("CSV", "CSV"),
        ],
    )
    cron_expresion = models.CharField(
        max_length=100,
        help_text="Expresión cron estándar (5 campos: min hora día_mes mes día_semana)",
    )
    destinatarios = models.JSONField(default=empty_list, help_text="Lista de emails")
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "reporte programado"
        verbose_name_plural = "reportes programados"

    def clean(self):
        super().clean()
        self._validar_cron()
        self._validar_destinatarios()

    def _validar_destinatarios(self):
        emails = self.destinatarios or []
        for email in emails:
            try:
                EmailAddress.de_string(email)
            except VOWValidationError:
                raise ValidationError(
                    {"destinatarios": f"Email inválido: {email}"}
                )

    def _validar_cron(self):
        """Valida sintaxis básica de expresión cron (5 campos)."""
        if not self.cron_expresion:
            return

        partes = self.cron_expresion.split()
        if len(partes) != 5:
            raise ValidationError(
                {
                    "cron_expresion": "La expresión cron debe tener exactamente 5 campos "
                    "(minuto hora día_mes mes día_semana)."
                }
            )

        # Validar cada campo básico
        for i, parte in enumerate(partes):
            if parte == "*":
                continue
            if parte.startswith("*/"):
                try:
                    int(parte[2:])
                except ValueError:
                    raise ValidationError(
                        {"cron_expresion": f"El campo {i + 1} tiene un intervalo inválido."}
                    )
                continue
            if "," in parte:
                for sub in parte.split(","):
                    try:
                        val = int(sub)
                        _validar_rango_campo(i, val)
                    except ValueError:
                        raise ValidationError(
                            {"cron_expresion": f"El campo {i + 1} tiene un valor inválido."}
                        )
                continue
            if "-" in parte:
                rango = parte.split("-")
                if len(rango) != 2:
                    raise ValidationError(
                        {"cron_expresion": f"El campo {i + 1} tiene un rango inválido."}
                    )
                try:
                    inicio = int(rango[0])
                    fin = int(rango[1])
                    _validar_rango_campo(i, inicio)
                    _validar_rango_campo(i, fin)
                    if inicio > fin:
                        raise ValidationError(
                            {"cron_expresion": f"El campo {i + 1} tiene un rango inválido (inicio > fin)."}
                        )
                except ValueError:
                    raise ValidationError(
                        {"cron_expresion": f"El campo {i + 1} tiene un rango inválido."}
                    )
                continue
            try:
                val = int(parte)
                _validar_rango_campo(i, val)
            except ValueError:
                raise ValidationError(
                    {"cron_expresion": f"El campo {i + 1} no es válido."}
                )

    def __str__(self):
        return self.nombre


def _validar_rango_campo(indice, valor):
    limites = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 7)]
    minimo, maximo = limites[indice]
    if valor < minimo or valor > maximo:
        raise ValidationError(
            {"cron_expresion": f"El campo {indice + 1} debe estar entre {minimo} y {maximo}."}
        )
