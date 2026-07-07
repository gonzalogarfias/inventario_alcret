import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F, Sum, Value
from django.db.models.functions import Coalesce
from django.http import HttpResponse, StreamingHttpResponse
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, UpdateView
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

from .models import Almacen, Categoria, Movimiento, Producto, Stock


class InventarioPermissionMixin(LoginRequiredMixin):
    roles_permitidos = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if self.roles_permitidos and request.user.rol not in self.roles_permitidos:
            messages.error(request, "No tenés permiso para realizar esta acción.")
            return redirect(self.request.GET.get("next", reverse("producto_list")))
        return super().dispatch(request, *args, **kwargs)


class ProductoListView(LoginRequiredMixin, ListView):
    model = Producto
    template_name = "inventario/producto_list.html"
    context_object_name = "productos"
    paginate_by = 20

    def get_queryset(self):
        qs = Producto.objects.select_related("categoria").filter(activo=True)
        q = self.request.GET.get("q")
        cat = self.request.GET.get("categoria")
        stock = self.request.GET.get("stock")
        if q:
            qs = qs.filter(nombre__icontains=q) | qs.filter(sku__icontains=q)
        if cat:
            qs = qs.filter(categoria_id=cat)
        if stock == "bajo":
            qs = qs.annotate(
                total_stock=Coalesce(Sum("stocks__cantidad"), Value(0))
            ).filter(
                stock_minimo__gt=0,
                total_stock__lte=F("stock_minimo"),
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["categorias"] = Categoria.objects.filter(activo=True)
        return ctx


producto_list = ProductoListView.as_view()


class ProductoCreateView(InventarioPermissionMixin, CreateView):
    roles_permitidos = ["ADMIN", "ALMACEN"]
    model = Producto
    template_name = "inventario/producto_form.html"
    fields = ["sku", "nombre", "descripcion", "categoria", "precio_venta", "stock_minimo"]
    success_url = reverse_lazy("producto_list")

    def form_valid(self, form):
        messages.success(self.request, "Producto creado correctamente.")
        return super().form_valid(form)


producto_create = ProductoCreateView.as_view()


class ProductoUpdateView(InventarioPermissionMixin, UpdateView):
    roles_permitidos = ["ADMIN", "ALMACEN"]
    model = Producto
    template_name = "inventario/producto_form.html"
    fields = ["sku", "nombre", "descripcion", "categoria", "precio_venta", "stock_minimo", "activo"]
    success_url = reverse_lazy("producto_list")

    def form_valid(self, form):
        messages.success(self.request, "Producto actualizado correctamente.")
        return super().form_valid(form)


producto_update = ProductoUpdateView.as_view()


class ProductoDetailView(LoginRequiredMixin, DetailView):
    model = Producto
    template_name = "inventario/producto_detail.html"
    context_object_name = "producto"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["stocks"] = Stock.objects.filter(producto=self.object).select_related("almacen")
        ctx["movimientos"] = (
            Movimiento.objects.filter(producto=self.object)
            .select_related("almacen", "realizada_por")
            .order_by("-created_at")[:20]
        )
        return ctx


producto_detail = ProductoDetailView.as_view()


class CategoriaListView(LoginRequiredMixin, ListView):
    model = Categoria
    template_name = "inventario/categoria_list.html"
    context_object_name = "categorias"


categoria_list = CategoriaListView.as_view()


class CategoriaCreateView(InventarioPermissionMixin, CreateView):
    roles_permitidos = ["ADMIN", "ALMACEN"]
    model = Categoria
    template_name = "inventario/categoria_form.html"
    fields = ["nombre", "descripcion"]
    success_url = reverse_lazy("categoria_list")

    def form_valid(self, form):
        messages.success(self.request, "Categoría creada correctamente.")
        return super().form_valid(form)


categoria_create = CategoriaCreateView.as_view()


class CategoriaUpdateView(InventarioPermissionMixin, UpdateView):
    roles_permitidos = ["ADMIN", "ALMACEN"]
    model = Categoria
    template_name = "inventario/categoria_form.html"
    fields = ["nombre", "descripcion", "activo"]
    success_url = reverse_lazy("categoria_list")

    def form_valid(self, form):
        messages.success(self.request, "Categoría actualizada correctamente.")
        return super().form_valid(form)


categoria_update = CategoriaUpdateView.as_view()


class AlmacenListView(LoginRequiredMixin, ListView):
    model = Almacen
    template_name = "inventario/almacen_list.html"
    context_object_name = "almacenes"


almacen_list = AlmacenListView.as_view()


class AlmacenCreateView(InventarioPermissionMixin, CreateView):
    roles_permitidos = ["ADMIN", "ALMACEN"]
    model = Almacen
    template_name = "inventario/almacen_form.html"
    fields = ["nombre", "ubicacion"]
    success_url = reverse_lazy("almacen_list")

    def form_valid(self, form):
        messages.success(self.request, "Almacén creado correctamente.")
        return super().form_valid(form)


almacen_create = AlmacenCreateView.as_view()


class AlmacenUpdateView(InventarioPermissionMixin, UpdateView):
    roles_permitidos = ["ADMIN", "ALMACEN"]
    model = Almacen
    template_name = "inventario/almacen_form.html"
    fields = ["nombre", "ubicacion", "activo"]
    success_url = reverse_lazy("almacen_list")

    def form_valid(self, form):
        messages.success(self.request, "Almacén actualizado correctamente.")
        return super().form_valid(form)


almacen_update = AlmacenUpdateView.as_view()


class MovimientoListView(LoginRequiredMixin, ListView):
    model = Movimiento
    template_name = "inventario/movimiento_list.html"
    context_object_name = "movimientos"
    paginate_by = 25

    def get_queryset(self):
        qs = Movimiento.objects.select_related("producto", "almacen", "realizada_por").order_by("-created_at")
        tipo = self.request.GET.get("tipo")
        q = self.request.GET.get("q")
        if tipo:
            qs = qs.filter(tipo=tipo)
        if q:
            qs = qs.filter(producto__nombre__icontains=q) | qs.filter(producto__sku__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["tipos"] = Movimiento.Tipo.choices
        return ctx


movimiento_list = MovimientoListView.as_view()


class MovimientoCreateView(LoginRequiredMixin, CreateView):
    model = Movimiento
    template_name = "inventario/movimiento_form.html"
    fields = ["tipo", "producto", "almacen", "cantidad", "costo_unitario", "motivo"]
    success_url = reverse_lazy("movimiento_list")

    def get_initial(self):
        initial = super().get_initial()
        if self.request.GET.get("producto"):
            initial["producto"] = self.request.GET.get("producto")
        return initial

    def _check_movimiento_permission(self, form):
        from apps.usuarios.models import Usuario
        tipo = form.instance.tipo
        if tipo == Movimiento.Tipo.AJUSTE and not self.request.user.has_perm("usuarios.puede_ajustar_stock"):
            messages.error(self.request, "No tenés permiso para realizar ajustes de stock.")
            return False
        roles_permitidos_entrada = (Usuario.Rol.ADMINISTRADOR, Usuario.Rol.ALMACENISTA)
        if tipo == Movimiento.Tipo.ENTRADA and self.request.user.rol not in roles_permitidos_entrada:
            messages.error(self.request, "No tenés permiso para registrar entradas de stock.")
            return False
        return True

    def form_valid(self, form):
        if not self._check_movimiento_permission(form):
            return self.form_invalid(form)
        form.instance.realizada_por = self.request.user
        cantidad = form.instance.cantidad
        if cantidad <= 0:
            form.add_error("cantidad", "La cantidad debe ser un valor positivo.")
            return self.form_invalid(form)
        if form.instance.tipo == Movimiento.Tipo.SALIDA:
            form.instance.cantidad = cantidad * -1
        messages.success(self.request, f"Movimiento de {form.instance.get_tipo_display().lower()} registrado.")
        return super().form_valid(form)


movimiento_create = MovimientoCreateView.as_view()


class Echo:
    def write(self, value):
        return value


def _estilo_excel(ws):
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="1D4ED8", end_color="1D4ED8", fill_type="solid")
    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")
    ws.column_dimensions["A"].width = 15
    ws.column_dimensions["B"].width = 35
    ws.column_dimensions["C"].width = 20
    ws.column_dimensions["D"].width = 15
    ws.column_dimensions["E"].width = 15
    ws.column_dimensions["F"].width = 20
    ws.column_dimensions["G"].width = 20


@login_required
def exportar_productos_csv(request):
    qs = Producto.objects.select_related("categoria").filter(activo=True)
    pseudo_buffer = Echo()
    writer = csv.writer(pseudo_buffer)
    writer.writerow(["SKU", "Nombre", "Categoría", "Precio", "Stock Mínimo"])
    for p in qs:
        writer.writerow([p.sku, p.nombre, p.categoria.nombre, str(p.precio_venta), str(p.stock_minimo)])
    return StreamingHttpResponse(
        (pseudo_buffer.write for _ in range(1)),
        content_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="productos.csv"'},
    )


@login_required
def exportar_productos_excel(request):
    wb = Workbook()
    ws = wb.active
    ws.title = "Productos"
    ws.append(["SKU", "Nombre", "Categoría", "Precio", "Stock Mínimo"])
    _estilo_excel(ws)
    for p in Producto.objects.select_related("categoria").filter(activo=True):
        ws.append([p.sku, p.nombre, p.categoria.nombre, float(p.precio_venta), float(p.stock_minimo)])
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="productos.xlsx"'
    wb.save(response)
    return response


@login_required
def exportar_movimientos_csv(request):
    qs = Movimiento.objects.select_related("producto", "almacen", "realizada_por").order_by("-created_at")
    tipo = request.GET.get("tipo")
    if tipo:
        qs = qs.filter(tipo=tipo)
    pseudo_buffer = Echo()
    writer = csv.writer(pseudo_buffer)
    writer.writerow(["Tipo", "Producto", "SKU", "Almacén", "Cantidad", "Costo Unitario", "Realizado Por", "Fecha"])
    for m in qs:
        writer.writerow([
            m.tipo, m.producto.nombre, m.producto.sku, m.almacen.nombre,
            str(m.cantidad), str(m.costo_unitario or ""),
            str(m.realizada_por or ""), str(m.created_at),
        ])
    return StreamingHttpResponse(
        (pseudo_buffer.write for _ in range(1)),
        content_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="movimientos.csv"'},
    )


@login_required
def exportar_movimientos_excel(request):
    wb = Workbook()
    ws = wb.active
    ws.title = "Movimientos"
    ws.append(["Tipo", "Producto", "SKU", "Almacén", "Cantidad", "Costo Unitario", "Realizado Por", "Fecha"])
    _estilo_excel(ws)
    qs = Movimiento.objects.select_related("producto", "almacen", "realizada_por").order_by("-created_at")
    tipo = request.GET.get("tipo")
    if tipo:
        qs = qs.filter(tipo=tipo)
    for m in qs:
        ws.append([
            m.tipo, m.producto.nombre, m.producto.sku, m.almacen.nombre,
            float(m.cantidad),
            float(m.costo_unitario) if m.costo_unitario else "",
            str(m.realizada_por or ""), str(m.created_at),
        ])
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="movimientos.xlsx"'
    wb.save(response)
    return response
