from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, F, Sum
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.utils import timezone

from apps.inventario.models import Movimiento, Stock


@login_required
def datos_dashboard(request):
    today = timezone.now().date()
    treinta_dias = today - timedelta(days=30)

    stock_por_categoria = (
        Stock.objects.values("producto__categoria__nombre")
        .annotate(total=Sum("cantidad"))
        .order_by("-total")
    )

    movimientos_por_dia = (
        Movimiento.objects.filter(created_at__date__gte=treinta_dias)
        .annotate(dia=TruncDate("created_at"))
        .values("dia", "tipo")
        .annotate(total=Count("id"))
        .order_by("dia")
    )

    stock_por_almacen = (
        Stock.objects.values("almacen__nombre")
        .annotate(total=Sum("cantidad"))
        .order_by("-total")
    )

    productos_bajo_stock = (
        Stock.objects.select_related("producto", "almacen")
        .filter(
            cantidad__lte=F("producto__stock_minimo"),
            producto__stock_minimo__gt=0,
        )
        .values("producto__nombre", "almacen__nombre", "cantidad")
        [:10]
    )

    movimientos_por_tipo = (
        Movimiento.objects.filter(created_at__date__gte=treinta_dias)
        .values("tipo")
        .annotate(total=Count("id"))
    )

    return JsonResponse({
        "stock_por_categoria": [
            {"label": c["producto__categoria__nombre"], "value": float(c["total"])}
            for c in stock_por_categoria if c["producto__categoria__nombre"]
        ],
        "movimientos_por_dia": [
            {"dia": str(m["dia"]), "tipo": m["tipo"], "total": m["total"]}
            for m in movimientos_por_dia
        ],
        "stock_por_almacen": [
            {"label": a["almacen__nombre"], "value": float(a["total"])}
            for a in stock_por_almacen
        ],
        "productos_bajo_stock": list(productos_bajo_stock),
        "movimientos_por_tipo": {
            m["tipo"]: m["total"] for m in movimientos_por_tipo
        },
    })
