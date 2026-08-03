import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Count
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, ListView, TemplateView, UpdateView

from apps.alertas.models import Alerta
from apps.auditoria.models import AuditLog
from apps.inventario.models import Almacen, Movimiento, Producto, Stock
from apps.shared.middleware import get_current_request_ip, invalidar_sesiones_usuario

from .forms import UsuarioCreateForm, UsuarioForm
from .models import Usuario

logger = logging.getLogger(__name__)


def _get_client_ip() -> str:
    """Devuelve IP del request o '0.0.0.0' si no está disponible."""
    ip = get_current_request_ip()
    return ip if ip else "0.0.0.0"


def _registrar_auditoria(evento, usuario, datos_extra=None):
    """Helper para crear entradas de AuditLog de forma segura."""
    datos = datos_extra or {}
    try:
        AuditLog.objects.create(
            evento=evento,
            usuario=usuario,
            ip_address=_get_client_ip(),
            datos=datos,
            hash_previo="",
        )
    except Exception as exc:
        logger.exception("Error al registrar auditoría: %s", exc)


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        rol = self.request.user.rol

        # Todos los roles ven stock básico
        ctx["total_productos"] = Producto.objects.filter(activo=True).count()
        ctx["total_almacenes"] = Almacen.objects.filter(activo=True).count()
        ctx["total_movimientos_hoy"] = Movimiento.objects.filter(
            created_at__date=timezone.now().date()
        ).count()
        ctx["stock_bajo"] = (
            Stock.objects.filter(cantidad__lte=5)
            .select_related("producto", "almacen")[:10]
        )
        ctx["ultimos_movimientos"] = (
            Movimiento.objects.select_related("producto", "almacen", "realizada_por")
            .order_by("-created_at")[:10]
        )

        # Solo ADMIN ve métricas sensibles y completas
        if rol == Usuario.Rol.ADMINISTRADOR:
            ctx["total_usuarios"] = Usuario.objects.filter(activo=True).count()
            ctx["total_alertas"] = Alerta.objects.filter(estado="PENDIENTE").count()
            ctx["productos_por_categoria"] = (
                Producto.objects.filter(activo=True)
                .values("categoria__nombre")
                .annotate(total=Count("id"))
                .order_by("-total")
            )
        elif rol == Usuario.Rol.VENDEDOR:
            ctx["total_alertas"] = Alerta.objects.filter(estado="PENDIENTE").count()
        # ALMACENISTA: solo stock y movimientos

        return ctx


dashboard = DashboardView.as_view()


class UsuarioListView(PermissionRequiredMixin, ListView):
    model = Usuario
    template_name = "usuarios/usuario_list.html"
    context_object_name = "usuarios"
    permission_required = "usuarios.puede_gestionar_usuarios"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().order_by("email")
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(email__icontains=q) | qs.filter(nombre__icontains=q)
        return qs


usuario_list = UsuarioListView.as_view()


class UsuarioCreateView(PermissionRequiredMixin, CreateView):
    model = Usuario
    template_name = "usuarios/usuario_form.html"
    permission_required = "usuarios.puede_gestionar_usuarios"
    form_class = UsuarioCreateForm
    success_url = reverse_lazy("usuario_list")

    def form_valid(self, form):
        messages.success(self.request, "Usuario creado correctamente.")
        return super().form_valid(form)


usuario_create = UsuarioCreateView.as_view()


class UsuarioUpdateView(PermissionRequiredMixin, UpdateView):
    model = Usuario
    template_name = "usuarios/usuario_form.html"
    permission_required = "usuarios.puede_gestionar_usuarios"
    form_class = UsuarioForm
    success_url = reverse_lazy("usuario_list")

    def dispatch(self, request, *args, **kwargs):
        self.original = get_object_or_404(Usuario, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        original = self.original
        usuario = form.instance

        # Bloquear auto-desactivación
        if (
            original.pk == self.request.user.pk
            and original.activo
            and not form.cleaned_data.get("activo", True)
        ):
            messages.error(self.request, "No puedes desactivar tu propia cuenta.")
            return HttpResponseForbidden("No puedes desactivar tu propia cuenta.")

        # Bloquear auto-escalación de rol
        if (
            original.pk == self.request.user.pk
            and "rol" in form.changed_data
        ):
            messages.error(self.request, "No puedes cambiar tu propio rol.")
            return HttpResponseForbidden("No puedes cambiar tu propio rol.")

        # Detectar cambios ANTES de guardar
        cambios = {}
        for campo in ["email", "nombre", "rol", "activo"]:
            old = getattr(original, campo)
            new = form.cleaned_data.get(campo)
            if old != new:
                cambios[campo] = {"anterior": old, "nuevo": new}

        # Aplicar cambio de password antes de guardar
        password = form.cleaned_data.get("password")
        if password:
            usuario.set_password(password)

        response = super().form_valid(form)

        # Registrar auditoría POST-guardado
        if original.activo and not usuario.activo:
            _registrar_auditoria(
                AuditLog.Evento.USUARIO_DESACTIVADO,
                self.request.user,
                {
                    "usuario_id": str(usuario.id),
                    "email": usuario.email,
                    "admin_id": str(self.request.user.id),
                },
            )

        if "rol" in cambios:
            _registrar_auditoria(
                AuditLog.Evento.PERMISO_CAMBIADO,
                self.request.user,
                {
                    "usuario_id": str(usuario.id),
                    "email": usuario.email,
                    "rol_anterior": cambios["rol"]["anterior"],
                    "rol_nuevo": cambios["rol"]["nuevo"],
                },
            )

        if password:
            invalidar_sesiones_usuario(usuario.id)
            _registrar_auditoria(
                AuditLog.Evento.PASSWORD_CHANGED,
                usuario,
                {
                    "admin_id": str(self.request.user.id),
                    "admin_email": self.request.user.email,
                },
            )

        if cambios:
            logger.info(
                "Usuario %s modificado por %s. Cambios: %s",
                usuario.email,
                self.request.user.email,
                cambios,
            )

        messages.success(self.request, "Usuario actualizado correctamente.")
        return response


usuario_update = UsuarioUpdateView.as_view()
