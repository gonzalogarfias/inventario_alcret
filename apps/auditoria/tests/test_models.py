import uuid
from datetime import datetime

import pytest

from apps.auditoria.models import AuditLog


@pytest.mark.django_db
class TestAuditLogModel:
    def test_crear_auditlog(self, usuario_admin):
        log = AuditLog.objects.create(
            evento=AuditLog.Evento.LOGIN_OK,
            usuario=usuario_admin,
            ip_address="192.168.1.1",
            datos={"email": usuario_admin.email},
            hash_previo="",
        )
        assert log.pk is not None
        assert log.evento == AuditLog.Evento.LOGIN_OK
        assert log.usuario == usuario_admin
        assert log.ip_address == "192.168.1.1"
        assert str(log) == f"{log.evento} @ {log.timestamp}"

    def test_auditlog_es_inmutable(self, usuario_admin):
        log = AuditLog.objects.create(
            evento=AuditLog.Evento.LOGIN_OK,
            usuario=usuario_admin,
            ip_address="10.0.0.1",
            datos={},
            hash_previo="",
        )
        with pytest.raises(PermissionError, match="AuditLog es inmutable"):
            log.ip_address = "0.0.0.0"
            log.save()

    def test_primer_registro_hash_previo_ceros(self, db):
        AuditLog.objects.all().delete()
        log = AuditLog.objects.create(
            evento=AuditLog.Evento.USUARIO_CREADO,
            usuario=None,
            ip_address="10.0.0.1",
            datos={},
            hash_previo="",
        )
        assert log.hash_previo == "0" * 64

    def test_segundo_registro_hereda_hash_del_primero(self, usuario_admin):
        primero = AuditLog.objects.create(
            evento=AuditLog.Evento.LOGIN_OK, usuario=usuario_admin,
            ip_address="10.0.0.1", datos={}, hash_previo="",
        )
        segundo = AuditLog.objects.create(
            evento=AuditLog.Evento.LOGIN_FAIL, usuario=None,
            ip_address="10.0.0.2", datos={}, hash_previo="",
        )
        assert segundo.hash_previo == primero.calcular_hash()

    def test_calcular_hash_determinista(self, usuario_admin):
        log = AuditLog.objects.create(
            evento=AuditLog.Evento.EXPORTACION, usuario=usuario_admin,
            ip_address="10.0.0.1", datos={"tipo": "csv"}, hash_previo="",
        )
        hash1 = log.calcular_hash()
        hash2 = log.calcular_hash()
        assert hash1 == hash2
        assert len(hash1) == 64

    def test_calcular_hash_cambia_al_modificar_datos(self, usuario_admin):
        log = AuditLog.objects.create(
            evento=AuditLog.Evento.ENTRADA, usuario=usuario_admin,
            ip_address="10.0.0.1", datos={"original": True}, hash_previo="",
        )
        hash_original = log.calcular_hash()
        log.datos = {"modificado": True}
        hash_modificado = log.calcular_hash()
        assert hash_original != hash_modificado

    def test_verificar_integridad_devuelve_true_sin_romper(self, usuario_admin):
        log = AuditLog.objects.create(
            evento=AuditLog.Evento.SYNC_CRM, usuario=usuario_admin,
            ip_address="10.0.0.1", datos={}, hash_previo="",
        )
        resultado = log.verificar_integridad()
        assert isinstance(resultado, bool)

    def test_verificar_cadena_valida_para_cadena_completa(self, usuario_admin):
        AuditLog.objects.all().delete()
        for i in range(3):
            AuditLog.objects.create(
                evento=AuditLog.Evento.LOGIN_OK, usuario=usuario_admin,
                ip_address=f"10.0.0.{i}", datos={"n": i}, hash_previo="",
            )
        resultado = AuditLog.verificar_cadena()
        assert resultado["valida"] is True
        assert resultado["total"] == 3
        assert resultado["errores"] == []

    def test_verificar_cadena_detecta_registro_alterado(self, usuario_admin):
        AuditLog.objects.all().delete()
        registros = []
        for i in range(3):
            registros.append(
                AuditLog.objects.create(
                    evento=AuditLog.Evento.ENTRADA, usuario=usuario_admin,
                    ip_address=f"10.0.0.{i}", datos={"n": i}, hash_previo="",
                )
            )
        AuditLog.objects.filter(pk=registros[1].pk).update(datos={"n": 999})
        resultado = AuditLog.verificar_cadena()
        assert resultado["valida"] is False
        assert any(str(registros[2].id) in e["registro"] for e in resultado["errores"])

    def test_verificar_integridad_con_mismo_timestamp(self, usuario_admin):
        AuditLog.objects.all().delete()
        t = datetime(2026, 1, 1, 12, 0, 0)
        primero = AuditLog.objects.create(
            id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            evento=AuditLog.Evento.LOGIN_OK, usuario=usuario_admin,
            ip_address="10.0.0.1", datos={}, hash_previo="", timestamp=t,
        )
        segundo = AuditLog.objects.create(
            id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
            evento=AuditLog.Evento.LOGIN_FAIL, usuario=None,
            ip_address="10.0.0.2", datos={}, hash_previo="", timestamp=t,
        )
        assert segundo.hash_previo == primero.calcular_hash()
        assert primero.verificar_integridad() is True
        assert segundo.verificar_integridad() is True
        assert AuditLog.verificar_cadena()["valida"] is True

    def test_verificar_integridad_detecta_predecesor_alterado(self, usuario_admin):
        AuditLog.objects.all().delete()
        primero = AuditLog.objects.create(
            evento=AuditLog.Evento.ENTRADA, usuario=usuario_admin,
            ip_address="10.0.0.1", datos={"ok": True}, hash_previo="",
        )
        segundo = AuditLog.objects.create(
            evento=AuditLog.Evento.SALIDA, usuario=None,
            ip_address="10.0.0.2", datos={}, hash_previo="",
        )
        AuditLog.objects.filter(pk=primero.pk).update(datos={"ok": False})
        assert segundo.verificar_integridad() is False
