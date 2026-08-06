from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView

from .models import Cliente


class ClienteListView(LoginRequiredMixin, ListView):
    model = Cliente
    template_name = "clientes/cliente_list.html"
    context_object_name = "clientes"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(
                empresa__icontains=q
            ) | qs.filter(nombre__icontains=q) | qs.filter(email__icontains=q) | qs.filter(rfc__icontains=q)
        return qs


cliente_list = ClienteListView.as_view()


class ClienteCreateView(LoginRequiredMixin, CreateView):
    model = Cliente
    template_name = "clientes/cliente_form.html"
    fields = ["empresa", "nombre", "email", "telefono", "rfc"]
    success_url = reverse_lazy("cliente_list")


cliente_create = ClienteCreateView.as_view()


class ClienteUpdateView(LoginRequiredMixin, UpdateView):
    model = Cliente
    template_name = "clientes/cliente_form.html"
    fields = ["empresa", "nombre", "email", "telefono", "rfc", "activo"]
    success_url = reverse_lazy("cliente_list")


cliente_update = ClienteUpdateView.as_view()
