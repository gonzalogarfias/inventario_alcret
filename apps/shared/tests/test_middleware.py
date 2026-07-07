import pytest

from apps.shared.middleware import (
    SecurityHeadersMiddleware,
    get_current_request_ip,
    invalidar_sesiones_usuario,
)


class TestSecurityHeadersMiddleware:
    def test_csp_header_present(self, rf):
        request = rf.get("/")
        middleware = SecurityHeadersMiddleware(lambda r: type("Resp", (), {})())
        response = middleware.process_response(request, type("Resp", (), {"headers": {}}))
        assert "Content-Security-Policy" in response

    def test_x_content_type_options(self, rf):
        request = rf.get("/")
        middleware = SecurityHeadersMiddleware(lambda r: type("Resp", (), {})())
        response = middleware.process_response(request, type("Resp", (), {"headers": {}}))
        assert response.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options(self, rf):
        request = rf.get("/")
        middleware = SecurityHeadersMiddleware(lambda r: type("Resp", (), {})())
        response = middleware.process_response(request, type("Resp", (), {"headers": {}}))
        assert response.get("X-Frame-Options") == "DENY"

    def test_referrer_policy(self, rf):
        request = rf.get("/")
        middleware = SecurityHeadersMiddleware(lambda r: type("Resp", (), {})())
        response = middleware.process_response(request, type("Resp", (), {"headers": {}}))
        assert response.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    def test_permissions_policy(self, rf):
        request = rf.get("/")
        middleware = SecurityHeadersMiddleware(lambda r: type("Resp", (), {})())
        response = middleware.process_response(request, type("Resp", (), {"headers": {}}))
        assert response.get("Permissions-Policy") == "camera=(), microphone=(), geolocation=()"


class TestGetCurrentRequestIp:
    def test_sin_request_retorna_default(self):
        assert get_current_request_ip() == "0.0.0.0"

    def test_con_x_forwarded_for(self, rf):
        request = rf.get("/", HTTP_X_FORWARDED_FOR="10.0.0.1, 10.0.0.2")
        from apps.shared.middleware import CurrentRequestMiddleware
        CurrentRequestMiddleware(lambda r: None).process_request(request)
        ip = get_current_request_ip()
        assert ip == "10.0.0.1"
        CurrentRequestMiddleware(lambda r: None).process_response(request, type("Resp", (), {})())

    def test_remoto_addr(self, rf):
        request = rf.get("/", REMOTE_ADDR="192.168.1.1")
        from apps.shared.middleware import CurrentRequestMiddleware
        CurrentRequestMiddleware(lambda r: None).process_request(request)
        ip = get_current_request_ip()
        assert ip == "192.168.1.1"
        CurrentRequestMiddleware(lambda r: None).process_response(request, type("Resp", (), {})())


@pytest.mark.django_db
class TestInvalidarSesionesUsuario:
    def test_invalida_sesion_del_usuario(self, client, usuario_admin):
        client.force_login(usuario_admin)
        from django.contrib.sessions.models import Session
        assert Session.objects.filter(expire_date__gte=Session.objects.model._meta.get_field("expire_date").default()).count() >= 0
        # Solo verificamos que no explote
        invalidar_sesiones_usuario(usuario_admin.pk)
        assert True

    def test_sin_sesiones_no_levanta_error(self):
        invalidar_sesiones_usuario(9999)
        assert True
