import pytest
from django.http import HttpResponse
from django.utils import timezone

from apps.shared.middleware import (
    SecurityHeadersMiddleware,
    get_current_request_ip,
    invalidar_sesiones_usuario,
)


class TestSecurityHeadersMiddleware:
    def response(self):
        return HttpResponse()

    def test_csp_header_present(self, rf):
        request = rf.get("/")
        middleware = SecurityHeadersMiddleware(lambda r: HttpResponse())
        response = middleware.process_response(request, self.response())
        assert "Content-Security-Policy" in response

    def test_x_content_type_options(self, rf):
        request = rf.get("/")
        middleware = SecurityHeadersMiddleware(lambda r: HttpResponse())
        response = middleware.process_response(request, self.response())
        assert response.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options(self, rf):
        request = rf.get("/")
        middleware = SecurityHeadersMiddleware(lambda r: HttpResponse())
        response = middleware.process_response(request, self.response())
        assert response.get("X-Frame-Options") == "DENY"

    def test_referrer_policy(self, rf):
        request = rf.get("/")
        middleware = SecurityHeadersMiddleware(lambda r: HttpResponse())
        response = middleware.process_response(request, self.response())
        assert response.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    def test_permissions_policy(self, rf):
        request = rf.get("/")
        middleware = SecurityHeadersMiddleware(lambda r: HttpResponse())
        response = middleware.process_response(request, self.response())
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
        CurrentRequestMiddleware(lambda r: None).process_response(request, HttpResponse())

    def test_remoto_addr(self, rf):
        request = rf.get("/", REMOTE_ADDR="192.168.1.1")
        from apps.shared.middleware import CurrentRequestMiddleware
        CurrentRequestMiddleware(lambda r: None).process_request(request)
        ip = get_current_request_ip()
        assert ip == "192.168.1.1"
        CurrentRequestMiddleware(lambda r: None).process_response(request, HttpResponse())


@pytest.mark.django_db
class TestInvalidarSesionesUsuario:
    def test_invalida_sesion_del_usuario(self, client, usuario_admin):
        client.force_login(usuario_admin)
        invalidar_sesiones_usuario(usuario_admin.pk)
        assert True

    def test_sin_sesiones_no_levanta_error(self):
        invalidar_sesiones_usuario(9999)
        assert True
