from pathlib import Path

from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.http import FileResponse, JsonResponse
from django.urls import include, path
from django.views.decorators.cache import cache_control

from apps.auditoria.auth_views import AuditPasswordResetConfirmView, AuditPasswordResetView


def health_check(request):
    return JsonResponse({"status": "healthy"})

@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
def service_worker(request):
    sw_path = Path(__file__).resolve().parent.parent / "static" / "sw.js"
    return FileResponse(open(sw_path, "rb"), content_type="application/javascript")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health_check, name="health_check"),
    path("sw.js", service_worker, name="service_worker"),
    path("accounts/login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(next_page="login"), name="logout"),
    path("accounts/password-reset/", AuditPasswordResetView.as_view(template_name="registration/password_reset_form.html"), name="password_reset"),
    path("accounts/password-reset/done/", auth_views.PasswordResetDoneView.as_view(template_name="registration/password_reset_done.html"), name="password_reset_done"),
    path("accounts/reset/<uidb64>/<token>/", AuditPasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("accounts/reset/done/", auth_views.PasswordResetCompleteView.as_view(), name="password_reset_complete"),
    path("", include("apps.usuarios.urls")),
    path("", include("apps.inventario.urls")),
    path("", include("apps.auditoria.urls")),
    path("", include("apps.metricas.urls")),
    path("alertas/", include("apps.alertas.urls")),
]
