import logging
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import DecimalField, F, Sum
from django.db.models.functions import TruncMonth
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.inventario.models import Movimiento, Producto, Stock
from apps.shared.middleware import get_current_request_ip
from apps.shared.services import registrar_audit_log
from apps.usuarios.models import Usuario

from .forms import FacturaForm
from .models import Factura

logger = logging.getLogger(__name__)

ROLES_FINANZAS = [Usuario.Rol.ADMINISTRADOR, Usuario.Rol.VENDEDOR, Usuario.Rol.ALMACENISTA]


def _check_roles(request, roles):
    if request.user.rol not in roles:
        messages.error(request, "No tenés permiso para realizar esta acción.")
        return False
    return True


@login_required
def finanzas_dashboard(request):
    if not _check_roles(request, ROLES_FINANZAS):
        return redirect("dashboard")
    facturas = Factura.objects.select_related("movimiento", "subido_por").order_by("-fecha")[:20]
    return render(request, "finanzas/dashboard.html", {
        "facturas_recientes": facturas,
    })


@login_required
def factura_upload(request):
    if not _check_roles(request, ROLES_FINANZAS):
        return redirect("dashboard")
    rol = request.user.rol
    if request.method == "POST":
        form = FacturaForm(request.POST, request.FILES, user_rol=rol)
        if form.is_valid():
            factura = form.save(commit=False)
            factura.subido_por = request.user
            factura.save()
            registrar_audit_log(
                evento="EXPORTACION",
                usuario=request.user,
                ip_address=get_current_request_ip(),
                datos={
                    "accion": "FACTURA_SUBIDA",
                    "factura_id": str(factura.id),
                    "tipo": factura.tipo,
                    "monto": str(factura.monto),
                },
            )
            messages.success(request, f"Factura {factura.get_tipo_display().lower()} subida correctamente.")
            logger.info("Factura subida: %s por %s", factura.id, request.user.email)
            return redirect("finanzas_dashboard")
    else:
        form = FacturaForm(user_rol=rol)
    return render(request, "finanzas/factura_form.html", {"form": form})


@login_required
def factura_archivo(request, pk):
    """Sirve el archivo de una factura SOLO a usuarios autorizados.

    Los archivos de /media/ NUNCA deben servirse como estáticos públicos
    (nginx no expone /media/): cada descarga pasa por esta vista, que
    aplica el mismo chequeo de roles que el resto del módulo.
    """
    if not _check_roles(request, ROLES_FINANZAS):
        return redirect("dashboard")
    factura = get_object_or_404(Factura, pk=pk)
    try:
        archivo = factura.archivo.open("rb")
    except (FileNotFoundError, ValueError):
        messages.error(request, "El archivo de la factura no está disponible.")
        return redirect("finanzas_dashboard")
    return FileResponse(archivo, as_attachment=True)


@login_required
@require_http_methods(["GET"])
def datos_finanzas(request):
    if not _check_roles(request, ROLES_FINANZAS):
        return JsonResponse({"error": "Forbidden"}, status=403)

    hoy = timezone.now().date()
    doce_meses = hoy - timedelta(days=365)

    # Antes se sumaba "cantidad" (unidades de stock) y se mostraba con
    # formato de dinero. Ahora se multiplica cantidad x costo del
    # producto para obtener el monto real en pesos de cada movimiento.
    meses = (
        Movimiento.objects
        .filter(created_at__date__gte=doce_meses)
        .annotate(mes=TruncMonth("created_at"))
        .values("mes", "tipo")
        .annotate(
            total=Sum(
                F("cantidad") * F("producto__costo_promedio"),
                output_field=DecimalField(),
            )
        )
        .order_by("mes")
    )

    compras_por_mes = {}
    ventas_por_mes = {}
    for m in meses:
        mes_str = m["mes"].strftime("%Y-%m") if m["mes"] else ""
        monto = abs(float(m["total"] or 0))
        if m["tipo"] == Movimiento.Tipo.ENTRADA:
            compras_por_mes[mes_str] = compras_por_mes.get(mes_str, 0) + monto
        elif m["tipo"] == Movimiento.Tipo.SALIDA:
            ventas_por_mes[mes_str] = ventas_por_mes.get(mes_str, 0) + monto

    facturas_por_mes = (
        Factura.objects
        .filter(fecha__gte=doce_meses)
        .annotate(mes=TruncMonth("fecha"))
        .values("mes", "tipo")
        .annotate(total=Sum("monto"))
        .order_by("mes")
    )

    facturas_data = {}
    for f in facturas_por_mes:
        mes_str = f["mes"].strftime("%Y-%m") if f["mes"] else ""
        if mes_str not in facturas_data:
            facturas_data[mes_str] = {"COMPRA": 0, "VENTA": 0}
        facturas_data[mes_str][f["tipo"]] = float(f["total"])

    valor_inventario = (
        Stock.objects
        .aggregate(
            total=Sum(
                F("cantidad") * F("producto__costo_promedio"),
                output_field=DecimalField(),
            )
        )["total"] or 0
    )
    costo_promedio = 0
    prods = Producto.objects.filter(activo=True)
    if prods.exists():
        costo_total = sum(float(p.costo_promedio) for p in prods if p.costo_promedio)
        costo_promedio = round(costo_total / prods.count(), 2)

    labels = sorted(set(list(compras_por_mes.keys()) + list(ventas_por_mes.keys()) + list(facturas_data.keys())))

    return JsonResponse({
        "labels": labels,
        "compras": [compras_por_mes.get(label, 0) for label in labels],
        "ventas": [ventas_por_mes.get(label, 0) for label in labels],
        "facturas_compras": [facturas_data.get(label, {}).get("COMPRA", 0) for label in labels],
        "facturas_ventas": [facturas_data.get(label, {}).get("VENTA", 0) for label in labels],
        "valor_inventario": float(valor_inventario),
        "costo_promedio": float(costo_promedio),
    })
