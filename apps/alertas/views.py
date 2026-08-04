import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import ListView

from apps.shared.middleware import get_current_request_ip
from apps.shared.services import registrar_audit_log

from .models import Alerta

logger = logging.getLogger(__name__)


class AlertaListView(LoginRequiredMixin, ListView):
    model = Alerta
    template_name = "alertas/alertas_list.html"
    context_object_name = "alertas"
    paginate_by = 20

    def get_queryset(self):
        return Alerta.objects.select_related("producto").order_by("-created_at")


alerta_list = AlertaListView.as_view()


class AlertaResolveView(LoginRequiredMixin, View):
    """Marca una alerta como resuelta.

    Solo acepta POST (cambio de estado). Un GET previo renderizaba un
    template inexistente y devolvía 500.

    NOTA: no modifica el stock. Solo confirma que el usuario la atendió.
    """

    http_method_names = ["post"]

    def post(self, request, pk):
        alerta = get_object_or_404(Alerta, pk=pk)
        if alerta.estado != Alerta.Estado.RESUELTA:
            alerta.estado = Alerta.Estado.RESUELTA
            alerta.resuelta_en = timezone.now()
            alerta.save(update_fields=["estado", "resuelta_en"])
            messages.success(request, "Alerta marcada como resuelta.")
            try:
                registrar_audit_log(
                    evento="ALERTA_RESUELTA",
                    usuario=request.user,
                    ip_address=get_current_request_ip(),
                    datos={
                        "alerta_id": str(alerta.pk),
                        "producto_id": str(alerta.producto_id) if alerta.producto_id else None,
                    },
                )
            except Exception as exc:
                logger.exception("No se pudo auditar resolución de alerta %s: %s", alerta.pk, exc)
        return redirect(reverse_lazy("alerta_list"))


alerta_resolve = AlertaResolveView.as_view()
