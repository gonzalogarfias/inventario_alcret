import pytest

from apps.auditoria.models import AuditLog
from apps.usuarios.models import Usuario


@pytest.mark.django_db
class TestUsuarioSignals:
    def test_crear_usuario_crea_auditlog(self, db):
        AuditLog.objects.all().delete()
        usuario = Usuario.objects.create_user(
            email="nuevo@test.com",
            nombre="Nuevo Usuario",
            rol=Usuario.Rol.VENDEDOR,
            password="Pass123!",
        )
        logs = AuditLog.objects.filter(evento=AuditLog.Evento.USUARIO_CREADO)
        assert logs.count() == 1
        log = logs.first()
        assert log.usuario == usuario
        assert log.datos["email"] == "nuevo@test.com"
        assert log.datos["rol"] == Usuario.Rol.VENDEDOR

    def test_auditlog_tiene_ip_default(self, db):
        AuditLog.objects.all().delete()
        Usuario.objects.create_user(
            email="ip_default@test.com",
            nombre="IP Default",
            rol=Usuario.Rol.ALMACENISTA,
            password="Pass123!",
        )
        log = AuditLog.objects.filter(evento=AuditLog.Evento.USUARIO_CREADO).first()
        assert log is not None
        assert log.ip_address == "0.0.0.0"

    def test_actualizar_usuario_no_crea_auditlog(self, db):
        AuditLog.objects.all().delete()
        usuario = Usuario.objects.create_user(
            email="update@test.com",
            nombre="Original",
            rol=Usuario.Rol.VENDEDOR,
            password="Pass123!",
        )
        AuditLog.objects.all().delete()
        usuario.nombre = "Actualizado"
        usuario.save()
        logs_creados = AuditLog.objects.filter(evento=AuditLog.Evento.USUARIO_CREADO).count()
        assert logs_creados == 0
