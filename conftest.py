import tempfile
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission

Usuario = get_user_model()

_TEST_MEDIA_ROOT = Path(tempfile.mkdtemp(prefix="alcret-test-media-"))


@pytest.fixture(autouse=True)
def _test_settings(settings):
    settings.STORAGES = {
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}
    }
    settings.STATIC_ROOT = None
    settings.MEDIA_ROOT = str(_TEST_MEDIA_ROOT)
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    # El validador HIBP hace una llamada de red; se desactiva en tests
    settings.AUTH_PASSWORD_VALIDATORS = [
        v for v in settings.AUTH_PASSWORD_VALIDATORS
        if "PwnedPasswordValidator" not in v["NAME"]
    ]


@pytest.fixture
def usuario_admin(db):  # noqa: ARG001
    usuario = Usuario.objects.create_user(
        email="admin@test.com",
        nombre="Admin Test",
        rol=Usuario.Rol.ADMINISTRADOR,
        password="AdminPass123!",
        is_staff=True,
        is_superuser=True,
    )
    # Asignar permisos custom necesarios
    perm_gestion = Permission.objects.get(codename="puede_gestionar_usuarios")
    perm_ajuste = Permission.objects.get(codename="puede_ajustar_stock")
    perm_auditoria = Permission.objects.get(codename="puede_ver_auditoria_completa")
    perm_crm = Permission.objects.get(codename="puede_configurar_crm")
    usuario.user_permissions.add(perm_gestion, perm_ajuste, perm_auditoria, perm_crm)
    return usuario


@pytest.fixture
def usuario_vendedor(db):  # noqa: ARG001
    return Usuario.objects.create_user(
        email="vendedor@test.com",
        nombre="Vendedor Test",
        rol=Usuario.Rol.VENDEDOR,
        password="VendPass123!",
    )


@pytest.fixture
def usuario_almacenista(db):  # noqa: ARG001
    return Usuario.objects.create_user(
        email="almacen@test.com",
        nombre="Almacenista Test",
        rol=Usuario.Rol.ALMACENISTA,
        password="AlmacPass123!",
    )


@pytest.fixture
def usuario_bloqueado(db):  # noqa: ARG001
    from datetime import timedelta

    from django.utils import timezone
    usuario = Usuario.objects.create_user(
        email="bloqueado@test.com",
        nombre="Bloqueado Test",
        rol=Usuario.Rol.VENDEDOR,
        password="BloqPass123!",
    )
    usuario.intentos_fallidos = 5
    usuario.bloqueado_hasta = timezone.now() + timedelta(hours=1)
    usuario.save()
    return usuario


@pytest.fixture
def categoria(db):  # noqa: ARG001
    from apps.inventario.models import Categoria
    return Categoria.objects.create(nombre="Test Categoría", descripcion="Descripción test")


@pytest.fixture
def producto(db, categoria):  # noqa: ARG001
    from apps.inventario.models import Producto
    return Producto.objects.create(
        sku="TEST-001",
        nombre="Producto Test",
        categoria=categoria,
        precio_venta=100.00,
        stock_minimo=5,
    )


@pytest.fixture
def almacen(db):  # noqa: ARG001
    from apps.inventario.models import Almacen
    return Almacen.objects.create(nombre="Almacén Test", ubicacion="Ubicación test")


@pytest.fixture
def stock(db, producto, almacen):  # noqa: ARG001
    from apps.inventario.models import Stock
    return Stock.objects.create(producto=producto, almacen=almacen, cantidad=100)


@pytest.fixture
def movimiento(db, producto, almacen, usuario_admin):  # noqa: ARG001
    from apps.inventario.models import Movimiento
    return Movimiento.objects.create(
        tipo=Movimiento.Tipo.ENTRADA,
        producto=producto,
        almacen=almacen,
        cantidad=50,
        realizada_por=usuario_admin,
    )


@pytest.fixture
def alerta(db, producto):  # noqa: ARG001
    from apps.alertas.models import Alerta
    return Alerta.objects.create(
        producto=producto,
        mensaje="Stock bajo de Test",
        estado=Alerta.Estado.PENDIENTE,
    )


@pytest.fixture
def alerta_config(db, producto):  # noqa: ARG001
    from apps.alertas.models import AlertaConfig
    return AlertaConfig.objects.create(producto=producto, umbral_minimo=10)


@pytest.fixture
def auditlog(db, usuario_admin):  # noqa: ARG001
    from apps.auditoria.models import AuditLog
    return AuditLog.objects.create(
        evento=AuditLog.Evento.ENTRADA,
        usuario=usuario_admin,
        ip_address="127.0.0.1",
        datos={"test": True},
        hash_previo="",
    )


@pytest.fixture
def authenticated_client(client, usuario_admin):
    client.force_login(usuario_admin)
    return client


@pytest.fixture
def client_vendedor(client, usuario_vendedor):
    client.force_login(usuario_vendedor)
    return client


@pytest.fixture
def client_almacenista(client, usuario_almacenista):
    client.force_login(usuario_almacenista)
    return client
