import pytest
from django.urls import reverse

from apps.auditoria.models import AuditLog


@pytest.mark.django_db
class TestAuditLogListView:
    def test_list_requiere_login(self, client):
        response = client.get(reverse("auditlog_list"))
        assert response.status_code == 302

    def test_list_autenticado(self, authenticated_client, usuario_admin):
        AuditLog.objects.create(
            evento=AuditLog.Evento.LOGIN_OK, usuario=usuario_admin,
            ip_address="10.0.0.1", datos={}, hash_previo="",
        )
        response = authenticated_client.get(reverse("auditlog_list"))
        assert response.status_code == 200
        assert "logs" in response.context

    def test_list_paginada(self, authenticated_client):
        response = authenticated_client.get(reverse("auditlog_list"))
        assert response.context["paginator"].per_page == 30

    def test_list_filtra_por_evento(self, authenticated_client, usuario_admin):
        AuditLog.objects.create(evento=AuditLog.Evento.ENTRADA, usuario=usuario_admin, ip_address="1.1.1.1", datos={}, hash_previo="")
        AuditLog.objects.create(evento=AuditLog.Evento.SALIDA, usuario=usuario_admin, ip_address="2.2.2.2", datos={}, hash_previo="")
        response = authenticated_client.get(reverse("auditlog_list"), {"evento": "ENTRADA"})
        assert response.status_code == 200
        for log in response.context["logs"]:
            assert log.evento == "ENTRADA"


@pytest.mark.django_db
class TestExportAuditoriaViews:
    def test_exportar_csv_requiere_login(self, client):
        response = client.get(reverse("exportar_auditoria_csv"))
        assert response.status_code == 302

    def test_exportar_csv_autenticado(self, authenticated_client, usuario_admin):
        AuditLog.objects.create(evento=AuditLog.Evento.LOGIN_OK, usuario=usuario_admin, ip_address="10.0.0.1", datos={}, hash_previo="")
        response = authenticated_client.get(reverse("exportar_auditoria_csv"))
        assert response.status_code == 200
        assert response["Content-Type"] == "text/csv"

    def test_exportar_excel_autenticado(self, authenticated_client, usuario_admin):
        AuditLog.objects.create(evento=AuditLog.Evento.LOGIN_OK, usuario=usuario_admin, ip_address="10.0.0.1", datos={}, hash_previo="")
        response = authenticated_client.get(reverse("exportar_auditoria_excel"))
        assert response.status_code == 200
        assert "application/vnd.openxmlformats" in response["Content-Type"]
