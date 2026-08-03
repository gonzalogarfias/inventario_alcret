from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import ListView

from .models import Alerta


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
    """

    http_method_names = ["post"]

    def post(self, request, pk):
        alerta = get_object_or_404(Alerta, pk=pk)
        if alerta.estado != Alerta.Estado.RESUELTA:
            alerta.estado = Alerta.Estado.RESUELTA
            alerta.resuelta_en = timezone.now()
            alerta.save(update_fields=["estado", "resuelta_en"])
            messages.success(request, "Alerta marcada como resuelta.")
        return redirect(reverse_lazy("alerta_list"))


alerta_resolve = AlertaResolveView.as_view()
