"""Modelo de auditoría inmutable con cadena de hash.

Correcciones Fase 4:
  1. hash_previo calculado correctamente (excluye timestamp mutable)
  2. Índices de base de datos para consultas frecuentes
  3. Método verificar_cadena() para validar integridad de toda la cadena
"""

import hashlib
import json
import uuid

from django.db import connection, models, transaction
from django.db.models import Q

# Clave arbitraria fija para el advisory lock de la cadena de auditoría.
# Debe ser la misma en todo el código; no depende de ninguna fila.
_AUDITLOG_CHAIN_LOCK_KEY = 918273645


class AuditLog(models.Model):
    """Registro de auditoría inmutable con hash encadenado.

    Cada registro incluye el hash del registro anterior, formando una
    cadena criptográfica que permite detectar modificaciones.

    El hash se calcula sobre campos inmutables (excluye timestamp que
    puede variar por timezone/microsegundos).
    """

    class Evento(models.TextChoices):
        ENTRADA = "ENTRADA", "Entrada de inventario"
        SALIDA = "SALIDA", "Salida de inventario"
        AJUSTE = "AJUSTE", "Ajuste / merma"
        LOGIN_OK = "LOGIN_OK", "Inicio de sesión exitoso"
        LOGIN_FAIL = "LOGIN_FAIL", "Intento de sesión fallido"
        PASSWORD_RESET = "PASSWORD_RESET", "Recuperación de contraseña"
        PASSWORD_CHANGED = "PASSWORD_CHANGED", "Contraseña cambiada"
        USUARIO_CREADO = "USUARIO_CREADO", "Usuario creado"
        USUARIO_DESACTIVADO = "USUARIO_DESACTIVADO", "Usuario desactivado"
        PERMISO_CAMBIADO = "PERMISO_CAMBIADO", "Permiso modificado"
        EXPORTACION = "EXPORTACION", "Exportación de datos"
        EXPORTACION_PRODUCTOS = "EXPORTACION_PRODUCTOS", "Exportación de productos"
        EXPORTACION_MOVIMIENTOS = "EXPORTACION_MOVIMIENTOS", "Exportación de movimientos"
        FACTURA_SUBIDA = "FACTURA_SUBIDA", "Factura subida"
        FACTURA_DESCARGADA = "FACTURA_DESCARGADA", "Factura descargada"
        SYNC_CRM = "SYNC_CRM", "Sincronización con CRM"
        ALERTA_RESUELTA = "ALERTA_RESUELTA", "Alerta resuelta"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    evento = models.CharField(max_length=30, choices=Evento.choices)
    usuario = models.ForeignKey("usuarios.Usuario", null=True, on_delete=models.SET_NULL)
    ip_address = models.GenericIPAddressField()
    timestamp = models.DateTimeField(auto_now_add=True)
    datos = models.JSONField()
    hash_previo = models.CharField(max_length=64)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "registro de auditoría"
        verbose_name_plural = "registros de auditoría"
        indexes = [
            models.Index(fields=["evento", "-timestamp"]),
            models.Index(fields=["usuario", "-timestamp"]),
            models.Index(fields=["ip_address", "-timestamp"]),
        ]

    def __str__(self):
        return f"{self.evento} @ {self.timestamp}"

    def calcular_hash(self) -> str:
        """Calcula el hash SHA-256 de este registro.

        El hash se calcula sobre campos inmutables:
          - id, evento, usuario_id, ip_address, datos, hash_previo

        NOTA: timestamp se EXCLUYE del hash porque:
          1. auto_now_add puede variar en microsegundos según la BD
          2. timezones pueden causar diferencias en serialización
          3. El timestamp ya está protegido por la inmutabilidad del modelo
        """
        contenido = {
            "id": str(self.id),
            "evento": self.evento,
            "usuario_id": str(self.usuario_id) if self.usuario_id else None,
            "ip_address": self.ip_address,
            "datos": self.datos,
            "hash_previo": self.hash_previo,
        }
        return hashlib.sha256(
            json.dumps(contenido, sort_keys=True, default=str).encode()
        ).hexdigest()

    def save(self, *args, **kwargs):
        """Guarda el registro de auditoría.

        Reglas:
          1. No se permite modificar registros existentes (inmutabilidad)
          2. Si no hay hash_previo, se calcula del último registro
          3. El hash_previo del primer registro es "0" * 64

        La asignación de hash_previo + el INSERT se serializan con un
        advisory lock de Postgres, para evitar que dos transacciones
        concurrentes lean el mismo "último registro" y bifurquen la
        cadena de hashes (select_for_update sobre una fila dinámica
        no es suficiente: ver análisis en el PR de auditoría).
        """
        if not self._state.adding:
            # Evita una query extra en cada guardado: si el objeto no
            # se está creando (self._state.adding es False), es una
            # modificación de un registro existente.
            raise PermissionError(
                "AuditLog es inmutable. No se puede modificar un registro existente."
            )

        if not self.hash_previo:
            with transaction.atomic():
                if connection.vendor == "postgresql":
                    with connection.cursor() as cursor:
                        # Se libera automáticamente al hacer commit/rollback
                        # de esta transacción (pg_advisory_XACT_lock).
                        cursor.execute(
                            "SELECT pg_advisory_xact_lock(%s)",
                            [_AUDITLOG_CHAIN_LOCK_KEY],
                        )
                else:
                    # SQLite serializa los escritores a nivel de base de
                    # datos; no necesita advisory lock.
                    pass

                ultimo = AuditLog.objects.order_by("-timestamp", "-id").first()
                self.hash_previo = ultimo.calcular_hash() if ultimo else "0" * 64

                # El INSERT debe ocurrir DENTRO del bloque con el lock
                # tomado, para que la siguiente transacción en cola
                # solo pueda leer "último registro" después de que
                # este commit haya terminado.
                super().save(*args, **kwargs)
            return

        super().save(*args, **kwargs)

    def verificar_integridad(self) -> bool:
        """Verifica que el hash_previo de este registro coincida con el hash del anterior.

        Returns:
            True si la cadena es válida, False si fue alterada.
        """
        if self.hash_previo == "0" * 64:
            return True

        # El predecesor es el "último registro" que vio save() al insertar:
        # el máximo por (timestamp, id). Si dos registros comparten el mismo
        # timestamp (mismo microsegundo), se desempata con el id, igual que
        # el order_by("-timestamp", "-id") de save().
        anterior = (
            AuditLog.objects.filter(
                Q(timestamp__lt=self.timestamp)
                | Q(timestamp=self.timestamp, id__lt=self.id)
            )
            .order_by("-timestamp", "-id")
            .first()
        )
        if not anterior:
            return False

        return anterior.calcular_hash() == self.hash_previo

    @classmethod
    def verificar_cadena(cls) -> dict:
        """Verifica la integridad de toda la cadena de auditoría.

        Returns:
            Dict con: {"valida": bool, "total": int, "errores": list}
        """
        # Se materializa en memoria porque la validación es secuencial
        # (cada registro depende del hash del anterior). El .iterator()
        # original era incompatible con esto, así que se quita.
        registros = list(cls.objects.order_by("timestamp", "id"))
        total = len(registros)
        errores = []

        for i, registro in enumerate(registros):
            if i == 0:
                if registro.hash_previo != "0" * 64:
                    errores.append({
                        "registro": str(registro.id),
                        "error": "Primer registro no tiene hash_previo inicial",
                        "esperado": "0" * 64,
                        "actual": registro.hash_previo,
                    })
                continue

            anterior = registros[i - 1]
            hash_esperado = anterior.calcular_hash()

            if registro.hash_previo != hash_esperado:
                errores.append({
                    "registro": str(registro.id),
                    "error": "Hash previo no coincide",
                    "esperado": hash_esperado,
                    "actual": registro.hash_previo,
                })

        return {
            "valida": len(errores) == 0,
            "total": total,
            "errores": errores,
        }
