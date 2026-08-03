import json
import logging
import threading

from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)

_thread_local = threading.local()


class CurrentRequestMiddleware(MiddlewareMixin):
    """Almacena el request actual en thread-local para acceso global.

    Útil para obtener IP del usuario en signals y servicios
    sin pasar request por toda la cadena de llamadas.

    NOTA: Este patrón thread-local asume workers WSGI síncronos
    (no gevent/eventlet/ASGI).
    """

    def process_request(self, request):
        _thread_local.current_request = request

    def process_response(self, request, response):
        if hasattr(_thread_local, "current_request"):
            delattr(_thread_local, "current_request")
        return response


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

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

        response["Service-Worker-Allowed"] = "/"

        return response


def get_current_request_ip() -> str:
    """Obtiene la IP del request actual desde thread-local.

    Usa HTTP_X_REAL_IP como fuente primaria (no falsificable por el cliente).
    Fallback a REMOTE_ADDR y luego a 0.0.0.0 si no hay request activo.
    """
    request = getattr(_thread_local, "current_request", None)
    if not request:
        return "0.0.0.0"
    real_ip = request.META.get("HTTP_X_REAL_IP")
    if real_ip:
        return real_ip.strip()
    return request.META.get("REMOTE_ADDR", "0.0.0.0")


def invalidar_sesiones_usuario(user_id: int | str) -> int:
    """Borra todas las sesiones activas de un usuario (NIST AC-12).

    Se llama desde:
      - UsuarioUpdateView (admin cambia password de otro usuario)
      - AuditPasswordResetConfirmView (usuario completa reset de password)

    Returns:
        Número de sesiones eliminadas.
    """
    from django.contrib.sessions.models import Session
    from django.utils import timezone

    eliminadas = 0
    sessions = Session.objects.filter(expire_date__gte=timezone.now())

    for session in sessions.iterator():  # .iterator() para memoria eficiente
        try:
            data = session.get_decoded()
            if str(data.get("_auth_user_id", "")) == str(user_id):
                session.delete()
                eliminadas += 1
        except json.JSONDecodeError as e:
            logger.warning(
                "Sesión con JSON corrupto encontrada (session_key=%s): %s",
                session.session_key, e,
            )
        except Exception as e:
            logger.error(
                "Error inesperado al procesar sesión (session_key=%s): %s",
                session.session_key, e,
                exc_info=True,
            )

    if eliminadas:
        logger.info("Invalidadas %d sesiones activas del usuario %s", eliminadas, user_id)

    return eliminadas
