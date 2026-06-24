from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, TemplateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import render
from django.db.models import Count, Sum
from django.utils import timezone
from apps.shared.middleware import get_current_request_ip
from apps.auditoria.models import AuditLog
from .models import Usuario
from apps.inventario.models import Producto, Movimiento, Almacen, Stock


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["total_productos"] = Producto.objects.filter(activo=True).count()
        ctx["total_almacenes"] = Almacen.objects.filter(activo=True).count()
        ctx["total_usuarios"] = Usuario.objects.filter(activo=True).count()
        ctx["total_movimientos_hoy"] = Movimiento.objects.filter(created_at__date=timezone.now().date()).count()
        ctx["stock_bajo"] = Stock.objects.filter(cantidad__lte=5).select_related("producto", "almacen")[:10]
        ctx["ultimos_movimientos"] = Movimiento.objects.select_related("producto", "almacen", "realizada_por").order_by("-created_at")[:10]
        ctx["productos_por_categoria"] = (
            Producto.objects.filter(activo=True)
            .values("categoria__nombre")
            .annotate(total=Count("id"))
            .order_by("-total")
        )
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
    fields = ["email", "nombre", "rol", "activo"]
    success_url = reverse_lazy("usuario_list")

    def form_valid(self, form):
        password = self.request.POST.get("password")
        if password:
            form.instance.set_password(password)
        messages.success(self.request, "Usuario creado correctamente.")
        return super().form_valid(form)


usuario_create = UsuarioCreateView.as_view()


class UsuarioUpdateView(PermissionRequiredMixin, UpdateView):
    model = Usuario
    template_name = "usuarios/usuario_form.html"
    permission_required = "usuarios.puede_gestionar_usuarios"
    fields = ["email", "nombre", "rol", "activo"]
    success_url = reverse_lazy("usuario_list")

    def form_valid(self, form):
        original = Usuario.objects.get(pk=self.object.pk) if self.object else None
        password = self.request.POST.get("password")
        if password:
            form.instance.set_password(password)
        response = super().form_valid(form)
        if original and original.activo and not form.instance.activo:
            AuditLog.objects.create(
                evento=AuditLog.Evento.USUARIO_DESACTIVADO,
                usuario=self.request.user,
                ip_address=get_current_request_ip(),
                datos={"usuario_id": str(form.instance.id), "email": form.instance.email},
                hash_previo="",
            )
        if password:
            AuditLog.objects.create(
                evento=AuditLog.Evento.PASSWORD_CHANGED,
                usuario=form.instance,
                ip_address=get_current_request_ip(),
                datos={"admin_id": str(self.request.user.id), "admin_email": self.request.user.email},
                hash_previo="",
            )
        messages.success(self.request, "Usuario actualizado correctamente.")
        return response


usuario_update = UsuarioUpdateView.as_view()
