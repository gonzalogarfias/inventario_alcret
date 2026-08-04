import logging
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db.models import Count, F, Sum
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.inventario.models import Movimiento, Stock
from apps.shared.middleware import get_current_request_ip
from apps.shared.services import registrar_audit_log
from apps.usuarios.models import Usuario

logger = logging.getLogger(__name__)

CACHE_TTL = 300  # 5 minutos


def _get_rol_usuario(request):
    """Devuelve el rol del usuario autenticado."""
    if not request.user.is_authenticated:
        return None
    return getattr(request.user, "rol", None)


def _registrar_auditoria_metricas(request, datos_extra=None):
    """Registra acceso a métricas en el audit log."""
    try:
        registrar_audit_log(
            evento="EXPORTACION",
            usuario=request.user if request.user.is_authenticated else None,
            ip_address=get_current_request_ip() or "0.0.0.0",
            datos=datos_extra or {},
        )
    except Exception as exc:
        logger.exception("Error al registrar auditoría de métricas: %s", exc)


def _build_cache_key(rol, suffix=""):
    """Genera clave de caché única por rol y sufijo."""
    return f"metricas:dashboard:{rol or 'anon'}:{suffix}"


def _cache_get(key):
    """Lee del caché sin romper la vista si Redis no está disponible."""
    try:
        return cache.get(key)
    except Exception:
        logger.exception("Cache.get falló (Redis caído?); continuando sin caché.")
        return None


def _cache_set(key, data, ttl):
    """Escribe al caché sin romper la vista si Redis no está disponible."""
    try:
        cache.set(key, data, ttl)
    except Exception:
        logger.exception("Cache.set falló (Redis caído?); continuando sin caché.")


@login_required
@require_http_methods(["GET"])
def datos_dashboard(request):
    """
    Endpoint JSON de métricas del dashboard con RBAC y cache.

    RBAC:
    - ADMINISTRADOR: acceso completo
    - VENDEDOR: métricas parciales (sin stock por almacén detallado)
    - ALMACENISTA: 403 — no debe ver métricas según matriz de permisos
    """
    rol = _get_rol_usuario(request)

    # RBAC: ALMACENISTA no ve métricas
    if rol == Usuario.Rol.ALMACENISTA:
        return JsonResponse(
            {"error": "No tienes permiso para ver métricas."},
            status=403,
        )

    # RBAC: VENDEDOR ve métricas parciales
    es_admin = rol == Usuario.Rol.ADMINISTRADOR

    cache_key = _build_cache_key(rol, "datos")
    cached = _cache_get(cache_key)
    if cached:
        # Auditoría también en cache hit (no se debe saltar el registro)
        _registrar_auditoria_metricas(
            request,
            {
                "rol": rol,
                "es_admin": es_admin,
                "metricas_solicitadas": "cache",
            },
        )
        return JsonResponse(cached)

    try:
        today = timezone.now().date()
        treinta_dias = today - timedelta(days=30)

        # Métricas base (todos los roles permitidos)
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

        movimientos_por_tipo = (
            Movimiento.objects.filter(created_at__date__gte=treinta_dias)
            .values("tipo")
            .annotate(total=Count("id"))
        )

        productos_bajo_stock = (
            Stock.objects.select_related("producto", "almacen")
            .filter(
                cantidad__lte=F("producto__stock_minimo"),
                producto__stock_minimo__gt=0,
            )
            .order_by("cantidad")
            .values("producto__nombre", "almacen__nombre", "cantidad")[:10]
        )

        data = {
            "stock_por_categoria": [
                {
                    "label": c["producto__categoria__nombre"],
                    "value": round(float(c["total"])),
                }
                for c in stock_por_categoria
                if c["producto__categoria__nombre"]
            ],
            "movimientos_por_dia": [
                {"dia": str(m["dia"]), "tipo": m["tipo"], "total": m["total"]}
                for m in movimientos_por_dia
            ],
            "productos_bajo_stock": list(productos_bajo_stock),
            "movimientos_por_tipo": {
                m["tipo"]: m["total"] for m in movimientos_por_tipo
            },
        }

        # Métricas solo para ADMIN
        if es_admin:
            stock_por_almacen = (
                Stock.objects.values("almacen__nombre")
                .annotate(total=Sum("cantidad"))
                .order_by("-total")
            )
            data["stock_por_almacen"] = [
                {
                    "label": a["almacen__nombre"],
                    "value": round(float(a["total"])),
                }
                for a in stock_por_almacen
            ]

        _cache_set(cache_key, data, CACHE_TTL)

        _registrar_auditoria_metricas(
            request,
            {
                "rol": rol,
                "es_admin": es_admin,
                "metricas_solicitadas": list(data.keys()),
            },
        )

        return JsonResponse(data)

    except Exception as exc:
        logger.exception("Error al generar métricas del dashboard: %s", exc)
        return JsonResponse(
            {"error": "Error interno al generar métricas."},
            status=500,
        )
