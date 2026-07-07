from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import ListView, UpdateView

from .models import Alerta


class AlertaListView(LoginRequiredMixin, ListView):
    model = Alerta
    template_name = "alertas/alertas_list.html"
    context_object_name = "alertas"
    paginate_by = 20

    def get_queryset(self):
        return Alerta.objects.select_related("producto").order_by("-created_at")


alerta_list = AlertaListView.as_view()


class AlertaResolveView(LoginRequiredMixin, UpdateView):
    model = Alerta
    fields = []
    success_url = reverse_lazy("alerta_list")

    def form_valid(self, form):
        form.instance.estado = Alerta.Estado.RESUELTA
        form.instance.resuelta_en = timezone.now()
        messages.success(self.request, "Alerta marcada como resuelta.")
        return super().form_valid(form)


alerta_resolve = AlertaResolveView.as_view()
