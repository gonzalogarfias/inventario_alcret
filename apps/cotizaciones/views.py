import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView

from apps.usuarios.models import Usuario

from .forms import CotizacionForm
from .models import Cotizacion

logger = logging.getLogger(__name__)


class CotizacionPermissionMixin(LoginRequiredMixin):
    roles_permitidos: list[str] = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if self.roles_permitidos and request.user.rol not in self.roles_permitidos:
            messages.error(request, "No tenés permiso para realizar esta acción.")
            return super().dispatch(request, *args, **kwargs)
        return super().dispatch(request, *args, **kwargs)


class CotizacionListView(LoginRequiredMixin, ListView):
    model = Cotizacion
    template_name = "cotizaciones/cotizacion_list.html"
    context_object_name = "cotizaciones"
    paginate_by = 20

    def get_queryset(self):
        qs = Cotizacion.objects.select_related("cliente", "unidad_interes", "vendedor")
        estado = self.request.GET.get("estado")
        q = self.request.GET.get("q")
        if estado:
            qs = qs.filter(estado=estado)
        if q:
            qs = qs.filter(
                folio__icontains=q
            ) | qs.filter(cliente__empresa__icontains=q) | qs.filter(cliente__nombre__icontains=q)
        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["estados"] = Cotizacion.Estado.choices
        return ctx


cotizacion_list = CotizacionListView.as_view()


class CotizacionCreateView(CotizacionPermissionMixin, CreateView):
    roles_permitidos = [Usuario.Rol.ADMINISTRADOR, Usuario.Rol.VENDEDOR]
    model = Cotizacion
    template_name = "cotizaciones/cotizacion_form.html"
    form_class = CotizacionForm
    success_url = reverse_lazy("cotizacion_list")

    def get_initial(self):
        initial = super().get_initial()
        initial["vendedor"] = self.request.user.id
        return initial

    def form_valid(self, form):
        if not form.instance.folio:
            form.instance.folio = f"COT-{Cotizacion.objects.count() + 1:05d}"
        messages.success(self.request, "Cotización creada correctamente.")
        logger.info(
            "Cotización creada: %s por %s",
            form.instance.folio,
            self.request.user.email,
        )
        return super().form_valid(form)


cotizacion_create = CotizacionCreateView.as_view()


class CotizacionUpdateView(CotizacionPermissionMixin, UpdateView):
    roles_permitidos = [Usuario.Rol.ADMINISTRADOR, Usuario.Rol.VENDEDOR]
    model = Cotizacion
    template_name = "cotizaciones/cotizacion_form.html"
    form_class = CotizacionForm
    success_url = reverse_lazy("cotizacion_list")

    def form_valid(self, form):
        messages.success(self.request, "Cotización actualizada correctamente.")
        logger.info(
            "Cotización actualizada: %s por %s",
            form.instance.folio,
            self.request.user.email,
        )
        return super().form_valid(form)


cotizacion_update = CotizacionUpdateView.as_view()
