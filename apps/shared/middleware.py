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


def get_current_request_ip():
    request = getattr(_thread_local, "current_request", None)
    if request:
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "0.0.0.0")
    return "0.0.0.0"
