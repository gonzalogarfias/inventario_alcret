
import pytest
from django.urls import reverse

from apps.inventario.models import Movimiento, Producto


@pytest.mark.django_db
class TestRBACMovimiento:
    """Según matriz de permisos (ARQUITECTURA.md):
    - VENDEDOR: Registrar entrada ❌, Registrar salida ✅, Ajuste ❌
    - ALMACENISTA: Registrar entrada ✅, Registrar salida ✅, Ajuste ❌
    - ADMIN: todo ✅

    IMPORTANTE: Usamos existencia en BD como indicador real de vulnerabilidad,
    no el status HTTP (la vista actual usa form_invalid, no 403).
    """

    def _post_movimiento(self, client, tipo, producto, almacen, cantidad="10", motivo="Test"):
        return client.post(reverse("movimiento_create"), {
            "tipo": tipo,
            "producto": producto.pk,
            "almacen": almacen.pk,
            "cantidad": cantidad,
            "motivo": motivo,
        }, follow=True)

    def test_vendedor_no_puede_crear_entrada(self, client, usuario_vendedor, producto, almacen):
        """VULNERABILIDAD CONFIRMADA: VENDEDOR puede crear ENTRADA sin restricción."""
        client.force_login(usuario_vendedor)
        self._post_movimiento(client, Movimiento.Tipo.ENTRADA, producto, almacen)
        creado = Movimiento.objects.filter(producto=producto, tipo=Movimiento.Tipo.ENTRADA).exists()
        assert not creado, (
            "VULNERABILIDAD: VENDEDOR creó movimiento ENTRADA. "
            "Falta verificación de permiso 'usuarios.puede_registrar_entrada' en MovimientoCreateView"
        )

    def test_vendedor_no_puede_crear_ajuste(self, client, usuario_vendedor, producto, almacen):
        client.force_login(usuario_vendedor)
        self._post_movimiento(client, Movimiento.Tipo.AJUSTE, producto, almacen)
        creado = Movimiento.objects.filter(producto=producto, tipo=Movimiento.Tipo.AJUSTE).exists()
        assert not creado, "VENDEDOR pudo crear AJUSTE - permiso 'puede_ajustar_stock' mal asignado"

    def test_almacenista_no_puede_crear_ajuste(self, client, usuario_almacenista, producto, almacen):
        client.force_login(usuario_almacenista)
        self._post_movimiento(client, Movimiento.Tipo.AJUSTE, producto, almacen)
        creado = Movimiento.objects.filter(producto=producto, tipo=Movimiento.Tipo.AJUSTE).exists()
        assert not creado, "ALMACENISTA pudo crear AJUSTE"

    def test_almacenista_puede_crear_entrada(self, client, usuario_almacenista, producto, almacen):
        client.force_login(usuario_almacenista)
        self._post_movimiento(client, Movimiento.Tipo.ENTRADA, producto, almacen)
        assert Movimiento.objects.filter(producto=producto, tipo=Movimiento.Tipo.ENTRADA).exists()

    def test_vendedor_puede_crear_salida(self, client, usuario_vendedor, producto, almacen):
        client.force_login(usuario_vendedor)
        self._post_movimiento(client, Movimiento.Tipo.SALIDA, producto, almacen)
        assert Movimiento.objects.filter(producto=producto, tipo=Movimiento.Tipo.SALIDA).exists()

    def test_admin_puede_crear_ajuste(self, authenticated_client, producto, almacen):
        self._post_movimiento(authenticated_client, Movimiento.Tipo.AJUSTE, producto, almacen)
        assert Movimiento.objects.filter(producto=producto, tipo=Movimiento.Tipo.AJUSTE).exists()


@pytest.mark.django_db
class TestRBACProducto:
    def test_vendedor_no_puede_crear_producto(self, client, usuario_vendedor, categoria):
        """RBAC: VENDEDOR no puede crear productos (solo ADMIN y ALMACENISTA)."""
        client.force_login(usuario_vendedor)
        data = {
            "sku": "VENDEDOR-SKU-001",
            "nombre": "Producto creado por vendedor",
            "categoria": categoria.pk,
            "precio_venta": "150.00",
            "stock_minimo": "5",
        }
        client.post(reverse("producto_create"), data, follow=True)
        assert not Producto.objects.filter(sku="VENDEDOR-SKU-001").exists(), (
            "VULNERABILIDAD: VENDEDOR pudo crear producto — falta restricción por rol"
        )

    def test_vendedor_no_puede_modificar_producto(self, client, usuario_vendedor, producto):
        client.force_login(usuario_vendedor)
        data = {
            "sku": producto.sku,
            "nombre": "Modificado por vendedor",
            "categoria": producto.categoria_id,
            "precio_venta": "200.00",
            "stock_minimo": "10",
            "activo": True,
        }
        client.post(reverse("producto_update", args=[producto.pk]), data, follow=True)
        producto.refresh_from_db()
        assert producto.nombre != "Modificado por vendedor", (
            "VULNERABILIDAD: VENDEDOR pudo modificar producto — falta restricción por rol"
        )


@pytest.mark.django_db
class TestRBACCategoria:
    def test_vendedor_no_puede_crear_categoria(self, client, usuario_vendedor):
        client.force_login(usuario_vendedor)
        from apps.inventario.models import Categoria
        data = {"nombre": "Cat Vendedor", "descripcion": "Test"}
        client.post(reverse("categoria_create"), data, follow=True)
        assert not Categoria.objects.filter(nombre="Cat Vendedor").exists(), (
            "VULNERABILIDAD: VENDEDOR pudo crear categoría"
        )


@pytest.mark.django_db
class TestRBACAlmacen:
    def test_vendedor_no_puede_crear_almacen(self, client, usuario_vendedor):
        client.force_login(usuario_vendedor)
        from apps.inventario.models import Almacen
        data = {"nombre": "Almacén Vendedor", "ubicacion": "Test"}
        client.post(reverse("almacen_create"), data, follow=True)
        assert not Almacen.objects.filter(nombre="Almacén Vendedor").exists(), (
            "VULNERABILIDAD: VENDEDOR pudo crear almacén"
        )
