"""Servicios compartidos entre apps del proyecto Inventario.

Regla de arquitectura: No importar modelos entre apps directamente.
Usar señales o estos servicios para desacoplar.
"""

import logging
from contextlib import contextmanager
from typing import Any, Callable

from django.db import transaction

logger = logging.getLogger(__name__)


def ejecutar_en_transaccion(func: Callable, *args: Any, **kwargs: Any) -> Any:
    """Ejecuta una función dentro de una transacción atómica.

    Versión funcional (más flexible que context manager).
    Útil cuando la lógica de negocio ya está encapsulada en una función.

    Args:
        func: Función a ejecutar atómicamente.
        *args, **kwargs: Argumentos para la función.

    Returns:
        El resultado de func(*args, **kwargs).

    Example:
        resultado = ejecutar_en_transaccion(registrar_movimiento, producto, cantidad)
    """
    with transaction.atomic():
        return func(*args, **kwargs)


@contextmanager
def transaccion_atomica():
    """Context manager alternativo para transacciones atómicas.

    Uso:
        with transaccion_atomica():
            movimiento.save()
            stock.cantidad = F('cantidad') + cantidad
            stock.save()
    """
    with transaction.atomic():
        yield


def registrar_audit_log(
    evento: str,
    usuario: Any | None,
    ip_address: str | None = None,
    datos: dict[str, Any] | None = None,
) -> Any:
    """Crea un registro de auditoría de forma segura.

    Este servicio desacopla la creación de AuditLog para que otras apps
    no importen directamente el modelo de auditoria.

    Args:
        evento: Código del evento (ver AuditLog.Evento)
        usuario: Instancia de Usuario o None
        ip_address: IP del request. Si es None, intenta obtenerla del thread-local.
        datos: Dict serializable con datos del evento.

    Returns:
        Instancia de AuditLog creada.

    Raises:
        Exception: Si falla la creación del log (no debe silenciarse en flujo crítico).
    """
    from apps.auditoria.models import AuditLog
    from apps.shared.middleware import get_current_request_ip

    if ip_address is None:
        ip_address = get_current_request_ip()

    if datos is None:
        datos = {}

    try:
        log = AuditLog.objects.create(
            evento=evento,
            usuario=usuario,
            ip_address=ip_address,
            datos=datos,
        )
        logger.debug("AuditLog creado: %s (%s)", evento, log.id)
        return log
    except Exception as e:
        logger.critical(
            "FALLA CRÍTICA: No se pudo crear AuditLog para evento %s. "
            "Usuario=%s, Datos=%s. Error: %s",
            evento,
            usuario,
            datos,
            e,
            exc_info=True,
        )
        raise
