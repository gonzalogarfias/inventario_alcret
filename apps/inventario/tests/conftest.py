"""Fixtures compartidas para tests de inventario.

Estas fixtures deben estar en el conftest.py raíz del proyecto
o en apps/conftest.py para ser accesibles globalmente.
"""

from decimal import Decimal

import pytest

from apps.inventario.models import Almacen, Categoria, Producto
from apps.usuarios.models import Usuario


@pytest.fixture
def categoria():
    return Categoria.objects.create(nombre="Test Categoría", descripcion="Para tests")


@pytest.fixture
def producto(categoria):
    return Producto.objects.create(
        sku="TEST-001",
        nombre="Producto Test",
        categoria=categoria,
        precio_venta=Decimal("100.00"),
        stock_minimo=Decimal("10"),
    )


@pytest.fixture
def almacen():
    return Almacen.objects.create(nombre="Almacén Test", ubicacion="Zona Test")


@pytest.fixture
def usuario_admin():
    return Usuario.objects.create(
        email="admin@test.com",
        nombre="Admin Test",
        rol=Usuario.Rol.ADMINISTRADOR,
        is_staff=True,
        is_superuser=True,
    )


@pytest.fixture
def usuario_vendedor():
    return Usuario.objects.create(
        email="vendedor@test.com",
        nombre="Vendedor Test",
        rol=Usuario.Rol.VENDEDOR,
    )


@pytest.fixture
def usuario_almacenista():
    return Usuario.objects.create(
        email="almacenista@test.com",
        nombre="Almacenista Test",
        rol=Usuario.Rol.ALMACENISTA,
    )


@pytest.fixture
def authenticated_client(client, usuario_admin):
    client.force_login(usuario_admin)
    return client
