from django.http import HttpResponse
from django.test import RequestFactory

from apps.shared.middleware import SecurityHeadersMiddleware, get_current_request_ip


class TestSecurityHeadersMiddleware:
    def test_csp_header_presente(self):
        factory = RequestFactory()
        request = factory.get("/")
        middleware = SecurityHeadersMiddleware(lambda req: HttpResponse())
        response = middleware(request)
        assert "Content-Security-Policy" in response
        assert "default-src 'self'" in response["Content-Security-Policy"]

    def test_x_content_type_options(self):
        factory = RequestFactory()
        request = factory.get("/")
        middleware = SecurityHeadersMiddleware(lambda req: HttpResponse())
        response = middleware(request)
        assert response["X-Content-Type-Options"] == "nosniff"

    def test_x_frame_options(self):
        factory = RequestFactory()
        request = factory.get("/")
        middleware = SecurityHeadersMiddleware(lambda req: HttpResponse())
        response = middleware(request)
        assert response["X-Frame-Options"] == "DENY"

    def test_referrer_policy(self):
        factory = RequestFactory()
        request = factory.get("/")
        middleware = SecurityHeadersMiddleware(lambda req: HttpResponse())
        response = middleware(request)
        assert response["Referrer-Policy"] == "strict-origin-when-cross-origin"


class TestGetCurrentRequestIp:
    def test_ip_directa(self, rf):
        request = rf.get("/", REMOTE_ADDR="1.2.3.4")
        from apps.shared.middleware import CurrentRequestMiddleware
        ip = None
        def get_response(req):  # noqa: ARG001
            nonlocal ip
            ip = get_current_request_ip()
            return HttpResponse()
        CurrentRequestMiddleware(get_response)(request)
        assert ip == "1.2.3.4"

    def test_ip_x_real_ip(self, rf):
        request = rf.get("/", HTTP_X_REAL_IP="10.0.0.1")
        from apps.shared.middleware import CurrentRequestMiddleware
        ip = None
        def get_response(req):  # noqa: ARG001
            nonlocal ip
            ip = get_current_request_ip()
            return HttpResponse()
        CurrentRequestMiddleware(get_response)(request)
        assert ip == "10.0.0.1"

    def test_ip_fallback_remote_addr(self, rf):
        request = rf.get("/", REMOTE_ADDR="10.0.0.1")
        from apps.shared.middleware import CurrentRequestMiddleware
        ip = None
        def get_response(req):  # noqa: ARG001
            nonlocal ip
            ip = get_current_request_ip()
            return HttpResponse()
        CurrentRequestMiddleware(get_response)(request)
        assert ip == "10.0.0.1"
