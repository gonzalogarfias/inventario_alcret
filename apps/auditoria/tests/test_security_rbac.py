import pytest
from django.urls import reverse

from apps.auditoria.models import AuditLog


@pytest.mark.django_db
class TestRBACExportAuditoria:
    """Según matriz de permisos:
    - Ver auditoría completa: ADMIN ✅, VENDEDOR ❌, ALMACENISTA ❌
    """

    def test_vendedor_no_puede_exportar_auditoria_csv(self, client, usuario_vendedor):
        client.force_login(usuario_vendedor)
        response = client.get(reverse("exportar_auditoria_csv"))
        assert response.status_code == 403, (
            f"VENDEDOR pudo exportar auditoría CSV (status {response.status_code}). "
            "VULNERABILIDAD: falta @permission_required('usuarios.puede_ver_auditoria_completa')"
        )

    def test_vendedor_no_puede_exportar_auditoria_excel(self, client, usuario_vendedor):
        client.force_login(usuario_vendedor)
        response = client.get(reverse("exportar_auditoria_excel"))
        assert response.status_code == 403, (
            f"VENDEDOR pudo exportar auditoría Excel (status {response.status_code}). "
            "VULNERABILIDAD: falta @permission_required('usuarios.puede_ver_auditoria_completa')"
        )

    def test_almacenista_no_puede_exportar_auditoria_csv(self, client, usuario_almacenista):
        client.force_login(usuario_almacenista)
        response = client.get(reverse("exportar_auditoria_csv"))
        assert response.status_code == 403, (
            f"ALMACENISTA pudo exportar auditoría CSV (status {response.status_code})"
        )

    def test_almacenista_no_puede_exportar_auditoria_excel(self, client, usuario_almacenista):
        client.force_login(usuario_almacenista)
        response = client.get(reverse("exportar_auditoria_excel"))
        assert response.status_code == 403, (
            f"ALMACENISTA pudo exportar auditoría Excel (status {response.status_code})"
        )

    def test_admin_puede_exportar_auditoria_csv(self, authenticated_client, usuario_admin):
        AuditLog.objects.create(
            evento=AuditLog.Evento.LOGIN_OK, usuario=usuario_admin,
            ip_address="10.0.0.1", datos={}, hash_previo="",
        )
        response = authenticated_client.get(reverse("exportar_auditoria_csv"))
        assert response.status_code == 200
        assert response["Content-Type"] == "text/csv"

    def test_admin_puede_exportar_auditoria_excel(self, authenticated_client, usuario_admin):
        AuditLog.objects.create(
            evento=AuditLog.Evento.LOGIN_OK, usuario=usuario_admin,
            ip_address="10.0.0.1", datos={}, hash_previo="",
        )
        response = authenticated_client.get(reverse("exportar_auditoria_excel"))
        assert response.status_code == 200
        assert "application/vnd.openxmlformats" in response["Content-Type"]

    def test_auditlog_list_requiere_permiso(self, client, usuario_vendedor):
        """La vista list de auditoría también debería requerir permiso."""
        client.force_login(usuario_vendedor)
        response = client.get(reverse("auditlog_list"))
        assert response.status_code == 403, (
            f"VENDEDOR pudo ver lista de auditoría (status {response.status_code}). "
            "VULNERABILIDAD: AuditLogListView debería usar PermissionRequiredMixin"
        )

    def test_auditlog_list_admin_puede_ver(self, authenticated_client, usuario_admin):
        AuditLog.objects.create(
            evento=AuditLog.Evento.LOGIN_OK, usuario=usuario_admin,
            ip_address="10.0.0.1", datos={}, hash_previo="",
        )
        response = authenticated_client.get(reverse("auditlog_list"))
        assert response.status_code == 200
        assert "logs" in response.context
