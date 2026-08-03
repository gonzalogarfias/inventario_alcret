from unittest.mock import patch

import pytest

from apps.auditoria.models import AuditLog
from apps.shared.services import ejecutar_en_transaccion, registrar_audit_log, transaccion_atomica


@pytest.mark.django_db
class TestEjecutarEnTransaccion:
    def test_ejecuta_funcion(self):
        def suma(a, b):
            return a + b
        assert ejecutar_en_transaccion(suma, 2, 3) == 5

    def test_rollback_en_error(self):
        from apps.inventario.models import Categoria
        def crear_y_fallar():
            Categoria.objects.create(nombre="Rollback Test")
            raise ValueError("Forzado")
        with pytest.raises(ValueError):
            ejecutar_en_transaccion(crear_y_fallar)
        assert not Categoria.objects.filter(nombre="Rollback Test").exists()


@pytest.mark.django_db
class TestTransaccionAtomica:
    def test_context_manager(self):
        from apps.inventario.models import Categoria
        with pytest.raises(ValueError), transaccion_atomica():
            Categoria.objects.create(nombre="CM Rollback")
            raise ValueError("Forzado")
        assert not Categoria.objects.filter(nombre="CM Rollback").exists()


@pytest.mark.django_db
class TestRegistrarAuditLog:
    def test_crea_auditlog(self, usuario_admin):
        log = registrar_audit_log(
            evento=AuditLog.Evento.ENTRADA,
            usuario=usuario_admin,
            ip_address="192.168.1.1",
            datos={"producto": "TEST"},
        )
        assert log.evento == AuditLog.Evento.ENTRADA
        assert log.usuario == usuario_admin
        assert log.ip_address == "192.168.1.1"

    def test_usa_ip_del_request(self, usuario_admin):
        with patch("apps.shared.middleware.get_current_request_ip", return_value="10.0.0.1"):
            log = registrar_audit_log(
                evento=AuditLog.Evento.SALIDA,
                usuario=usuario_admin,
            )
        assert log.ip_address == "10.0.0.1"

    def test_datos_default_vacio(self, usuario_admin):
        log = registrar_audit_log(
            evento=AuditLog.Evento.AJUSTE,
            usuario=usuario_admin,
            ip_address="127.0.0.1",
        )
        assert log.datos == {}

    def test_falla_critica_loggea(self, usuario_admin):
        mock_logger = patch("apps.shared.services.logger").start()
        with (
            patch("apps.auditoria.models.AuditLog.objects.create", side_effect=Exception("DB down")),
            pytest.raises(Exception, match="DB down"),
        ):
            registrar_audit_log(
                evento=AuditLog.Evento.LOGIN_OK,
                usuario=usuario_admin,
            )
        mock_logger.critical.assert_called_once()
        patch.stopall()
