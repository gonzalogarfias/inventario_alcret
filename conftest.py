import pytest
from django.contrib.auth import get_user_model

Usuario = get_user_model()


@pytest.fixture(autouse=True)
def _test_settings(settings):
    settings.STORAGES = {"staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}}
    settings.STATIC_ROOT = None
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True


@pytest.fixture
def usuario_admin(db):
    usuario = Usuario.objects.create_user(
        email="admin@test.com",
        nombre="Admin Test",
        rol=Usuario.Rol.ADMINISTRADOR,
        password="AdminPass123!",
    )
    usuario.is_staff = True
    usuario.is_superuser = True
    usuario.save()
    return usuario


@pytest.fixture
def usuario_vendedor(db):
    return Usuario.objects.create_user(
        email="vendedor@test.com",
        nombre="Vendedor Test",
        rol=Usuario.Rol.VENDEDOR,
        password="VendPass123!",
    )


@pytest.fixture
def usuario_almacenista(db):
    return Usuario.objects.create_user(
        email="almacen@test.com",
        nombre="Almacenista Test",
        rol=Usuario.Rol.ALMACENISTA,
        password="AlmacPass123!",
    )


@pytest.fixture
def categoria(db):
    from apps.inventario.models import Categoria
    return Categoria.objects.create(nombre="Test Categoría", descripcion="Descripción test")


@pytest.fixture
def producto(db, categoria):
    from apps.inventario.models import Producto
    return Producto.objects.create(
        sku="TEST-001",
        nombre="Producto Test",
        categoria=categoria,
        precio_venta=100.00,
        stock_minimo=5,
    )


@pytest.fixture
def almacen(db):
    from apps.inventario.models import Almacen
    return Almacen.objects.create(nombre="Almacén Test", ubicacion="Ubicación test")


@pytest.fixture
def authenticated_client(client, usuario_admin):
    client.force_login(usuario_admin)
    return client
