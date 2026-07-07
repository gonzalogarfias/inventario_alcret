import json
import threading

from django.utils.deprecation import MiddlewareMixin

_thread_local = threading.local()


class CurrentRequestMiddleware(MiddlewareMixin):
    def process_request(self, request):
        _thread_local.current_request = request

    def process_response(self, request, response):
        if hasattr(_thread_local, "current_request"):
            del _thread_local.current_request
        return response


class SecurityHeadersMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        response["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
            "https://cdn.jsdelivr.net https://cdn.tailwindcss.com https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' "
            "https://cdn.jsdelivr.net https://cdn.tailwindcss.com https://fonts.googleapis.com; "
            "img-src 'self' data:; "
            "font-src 'self' https://fonts.gstatic.com; "
            "connect-src 'self' https://cdn.jsdelivr.net; "
            "form-action 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self';"
        )
        response["X-Content-Type-Options"] = "nosniff"
        response["X-Frame-Options"] = "DENY"
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response


def get_current_request_ip():
    request = getattr(_thread_local, "current_request", None)
    if request:
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "0.0.0.0")
    return "0.0.0.0"


def invalidar_sesiones_usuario(user_id):
    from django.contrib.sessions.models import Session
    from django.utils import timezone
    sessions = Session.objects.filter(expire_date__gte=timezone.now())
    for session in sessions:
        try:
            data = session.get_decoded()
            if str(data.get("_auth_user_id", "")) == str(user_id):
                session.delete()
        except (json.JSONDecodeError, Exception):
            continue
