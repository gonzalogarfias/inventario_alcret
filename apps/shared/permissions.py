"""Permisos de negocio centralizados por rol.

Mantener esta matriz alineada con ARQUITECTURA.md para evitar que cada vista
reimplemente reglas RBAC con diferencias sutiles.
"""

from apps.usuarios.models import Usuario

ROLES_FINANZAS = (
    Usuario.Rol.ADMINISTRADOR,
    Usuario.Rol.VENDEDOR,
    Usuario.Rol.ALMACENISTA,
)
ROLES_EXPORTACION_INVENTARIO = ROLES_FINANZAS


def puede_exportar_inventario(usuario) -> bool:
    """Indica si el usuario puede exportar reportes de inventario."""
    return bool(usuario.is_authenticated and usuario.rol in ROLES_EXPORTACION_INVENTARIO)


def puede_ver_finanzas(usuario) -> bool:
    """Indica si el usuario puede acceder al módulo financiero."""
    return bool(usuario.is_authenticated and usuario.rol in ROLES_FINANZAS)


def puede_subir_factura(usuario, tipo: str) -> bool:
    """Valida permisos de subida según tipo de factura.

    Matriz vigente:
      - ADMIN: COMPRA y VENTA
      - VENDEDOR: VENTA
      - ALMACENISTA: COMPRA
    """
    if not usuario.is_authenticated:
        return False
    if usuario.rol == Usuario.Rol.ADMINISTRADOR:
        return True
    if usuario.rol == Usuario.Rol.VENDEDOR:
        return tipo == "VENTA"
    if usuario.rol == Usuario.Rol.ALMACENISTA:
        return tipo == "COMPRA"
    return False


def puede_descargar_factura(usuario, factura) -> bool:
    """Valida permisos de descarga con la misma granularidad de subida."""
    return puede_subir_factura(usuario, factura.tipo)
