"""Tests de seguridad RBAC para inventario.

Vulnerabilidades a cubrir:
  - VENDEDOR no puede crear ENTRADA
  - VENDEDOR no puede crear AJUSTE
  - ALMACENISTA no puede crear AJUSTE
  - VENDEDOR no puede crear/modificar productos
  - VENDEDOR no puede crear categorías/almacenes
"""

import pytest
from django.urls import reverse

from apps.inventario.models import Movimiento, Producto


@pytest.mark.django_db
class TestRBACMovimiento:
    """Tests RBAC para creación de movimientos.

    Matriz de permisos (ARQUITECTURA.md):
      - ENTRADA: Admin, Almacenista
      - SALIDA: Admin, Vendedor, Almacenista
      - AJUSTE: Solo Admin
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
        """VENDEDOR no puede registrar ENTRADAS (solo ADMIN y ALMACENISTA)."""
        client.force_login(usuario_vendedor)
        self._post_movimiento(client, Movimiento.Tipo.ENTRADA, producto, almacen)
        creado = Movimiento.objects.filter(producto=producto, tipo=Movimiento.Tipo.ENTRADA).exists()
        assert not creado, (
            "VULNERABILIDAD: VENDEDOR creó movimiento ENTRADA. "
            "Falta verificación de permiso en MovimientoCreateView"
        )

    def test_vendedor_no_puede_crear_ajuste(self, client, usuario_vendedor, producto, almacen):
        """VENDEDOR no puede registrar AJUSTES (solo ADMIN)."""
        client.force_login(usuario_vendedor)
        self._post_movimiento(client, Movimiento.Tipo.AJUSTE, producto, almacen)
        creado = Movimiento.objects.filter(producto=producto, tipo=Movimiento.Tipo.AJUSTE).exists()
        assert not creado, "VENDEDOR pudo crear AJUSTE"

    def test_almacenista_no_puede_crear_ajuste(self, client, usuario_almacenista, producto, almacen):
        """ALMACENISTA no puede registrar AJUSTES (solo ADMIN)."""
        client.force_login(usuario_almacenista)
        self._post_movimiento(client, Movimiento.Tipo.AJUSTE, producto, almacen)
        creado = Movimiento.objects.filter(producto=producto, tipo=Movimiento.Tipo.AJUSTE).exists()
        assert not creado, "ALMACENISTA pudo crear AJUSTE"

    def test_almacenista_puede_crear_entrada(self, client, usuario_almacenista, producto, almacen):
        """ALMACENISTA puede registrar ENTRADAS."""
        client.force_login(usuario_almacenista)
        self._post_movimiento(client, Movimiento.Tipo.ENTRADA, producto, almacen)
        assert Movimiento.objects.filter(producto=producto, tipo=Movimiento.Tipo.ENTRADA).exists()

    def test_vendedor_puede_crear_salida(self, client, usuario_vendedor, producto, almacen):
        """VENDEDOR puede registrar SALIDAS."""
        from apps.inventario.models import Stock
        Stock.objects.create(producto=producto, almacen=almacen, cantidad=100)
        client.force_login(usuario_vendedor)
        self._post_movimiento(client, Movimiento.Tipo.SALIDA, producto, almacen)
        assert Movimiento.objects.filter(producto=producto, tipo=Movimiento.Tipo.SALIDA).exists()

    def test_admin_puede_crear_ajuste(self, authenticated_client, producto, almacen):
        """ADMIN puede registrar AJUSTES."""
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
            "VULNERABILIDAD: VENDEDOR pudo crear producto"
        )

    def test_vendedor_no_puede_modificar_producto(self, client, usuario_vendedor, producto):
        """RBAC: VENDEDOR no puede modificar productos."""
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
            "VULNERABILIDAD: VENDEDOR pudo modificar producto"
        )


@pytest.mark.django_db
class TestRBACCategoria:
    def test_vendedor_no_puede_crear_categoria(self, client, usuario_vendedor):
        """RBAC: VENDEDOR no puede crear categorías."""
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
        """RBAC: VENDEDOR no puede crear almacenes."""
        client.force_login(usuario_vendedor)
        from apps.inventario.models import Almacen
        data = {"nombre": "Almacén Vendedor", "ubicacion": "Test"}
        client.post(reverse("almacen_create"), data, follow=True)
        assert not Almacen.objects.filter(nombre="Almacén Vendedor").exists(), (
            "VULNERABILIDAD: VENDEDOR pudo crear almacén"
        )


@pytest.mark.django_db
class TestValidacionStockSalida:
    """Tests de validación de stock suficiente antes de SALIDA."""

    def test_salida_sin_stock_disponible_falla(self, authenticated_client, producto, almacen):
        """No se puede registrar SALIDA si no hay stock."""
        data = {
            "tipo": Movimiento.Tipo.SALIDA,
            "producto": producto.pk,
            "almacen": almacen.pk,
            "cantidad": "10",
            "motivo": "Venta",
        }
        response = authenticated_client.post(reverse("movimiento_create"), data)
        assert not Movimiento.objects.filter(
            producto=producto, tipo=Movimiento.Tipo.SALIDA
        ).exists()
        assert "insuficiente" in response.content.decode().lower() or response.status_code == 200

    def test_salida_con_stock_insuficiente_falla(self, authenticated_client, producto, almacen):
        """No se puede registrar SALIDA si el stock es menor al solicitado."""
        from apps.inventario.models import Stock
        Stock.objects.create(producto=producto, almacen=almacen, cantidad=5)
        data = {
            "tipo": Movimiento.Tipo.SALIDA,
            "producto": producto.pk,
            "almacen": almacen.pk,
            "cantidad": "10",
            "motivo": "Venta",
        }
        authenticated_client.post(reverse("movimiento_create"), data)
        assert not Movimiento.objects.filter(
            producto=producto, tipo=Movimiento.Tipo.SALIDA, cantidad=-10
        ).exists()

    def test_salida_con_stock_suficiente_ok(self, authenticated_client, producto, almacen):
        """SALIDA exitosa cuando hay stock suficiente."""
        from apps.inventario.models import Stock
        Stock.objects.create(producto=producto, almacen=almacen, cantidad=100)
        data = {
            "tipo": Movimiento.Tipo.SALIDA,
            "producto": producto.pk,
            "almacen": almacen.pk,
            "cantidad": "10",
            "motivo": "Venta",
        }
        authenticated_client.post(reverse("movimiento_create"), data, follow=True)
        assert Movimiento.objects.filter(
            producto=producto, tipo=Movimiento.Tipo.SALIDA
        ).exists()
