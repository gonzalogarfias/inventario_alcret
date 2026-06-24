import pytest
from decimal import Decimal
from django.db.utils import IntegrityError
from django.core.exceptions import ValidationError
from apps.inventario.models import Categoria, Producto, Almacen, Stock, Movimiento


@pytest.mark.django_db
class TestCategoriaModel:
    def test_crear_categoria(self):
        cat = Categoria.objects.create(nombre="Electrónicos", descripcion="Prod. electrónicos")
        assert cat.nombre == "Electrónicos"
        assert str(cat) == "Electrónicos"

    def test_categoria_nombre_unico(self):
        Categoria.objects.create(nombre="Única")
        with pytest.raises(IntegrityError):
            Categoria.objects.create(nombre="Única")


@pytest.mark.django_db
class TestProductoModel:
    def test_crear_producto(self, categoria):
        prod = Producto.objects.create(
            sku="SKU-001",
            nombre="Producto Alpha",
            categoria=categoria,
            precio_venta=Decimal("150.50"),
            stock_minimo=Decimal("10"),
        )
        assert prod.sku == "SKU-001"
        assert str(prod) == "SKU-001 - Producto Alpha"
        assert prod.activo is True
        assert prod.costo_promedio == Decimal("0")

    def test_sku_unico(self, categoria):
        Producto.objects.create(sku="UNICO", nombre="P1", categoria=categoria, precio_venta=10)
        with pytest.raises(IntegrityError):
            Producto.objects.create(sku="UNICO", nombre="P2", categoria=categoria, precio_venta=20)

    def test_precio_venta_minimo(self, categoria):
        with pytest.raises(ValidationError):
            prod = Producto(sku="ERR", nombre="Precio Cero", categoria=categoria, precio_venta=Decimal("0.00"))
            prod.full_clean()

    def test_stock_minimo_puede_ser_cero(self, categoria):
        prod = Producto.objects.create(
            sku="SKU-CERO", nombre="Stock Cero", categoria=categoria,
            precio_venta=Decimal("50"), stock_minimo=Decimal("0"),
        )
        assert prod.stock_minimo == Decimal("0")

    def test_activo_default_true(self, categoria):
        prod = Producto.objects.create(sku="ACTIVO", nombre="Activo", categoria=categoria, precio_venta=10)
        assert prod.activo is True


@pytest.mark.django_db
class TestAlmacenModel:
    def test_crear_almacen(self):
        alm = Almacen.objects.create(nombre="Central", ubicacion="Av. Siempre Viva 123")
        assert str(alm) == "Central"
        assert alm.activo is True

    def test_almacen_nombre_unico(self):
        Almacen.objects.create(nombre="Único")
        with pytest.raises(IntegrityError):
            Almacen.objects.create(nombre="Único")


@pytest.mark.django_db
class TestStockModel:
    def test_crear_stock(self, producto, almacen):
        stock = Stock.objects.create(producto=producto, almacen=almacen, cantidad=Decimal("100"))
        assert stock.cantidad == Decimal("100")
        assert str(stock) == f"{producto.nombre} @ {almacen.nombre}: 100"

    def test_unique_together_producto_almacen(self, producto, almacen):
        Stock.objects.create(producto=producto, almacen=almacen, cantidad=10)
        with pytest.raises(IntegrityError):
            Stock.objects.create(producto=producto, almacen=almacen, cantidad=20)

    def test_cantidad_default_cero(self, producto, almacen):
        stock = Stock.objects.create(producto=producto, almacen=almacen)
        assert stock.cantidad == Decimal("0")


@pytest.mark.django_db
class TestMovimientoModel:
    def test_crear_movimiento_entrada(self, producto, almacen, usuario_admin):
        mov = Movimiento.objects.create(
            tipo=Movimiento.Tipo.ENTRADA,
            producto=producto,
            almacen=almacen,
            cantidad=Decimal("10"),
            realizada_por=usuario_admin,
        )
        assert mov.tipo == Movimiento.Tipo.ENTRADA
        assert mov.cantidad == Decimal("10")
        assert str(mov) == f"ENTRADA {producto.sku} x10"

    def test_crear_movimiento_salida(self, producto, almacen, usuario_admin):
        mov = Movimiento.objects.create(
            tipo=Movimiento.Tipo.SALIDA,
            producto=producto,
            almacen=almacen,
            cantidad=Decimal("5"),
            realizada_por=usuario_admin,
        )
        assert mov.tipo == Movimiento.Tipo.SALIDA

    def test_crear_movimiento_ajuste(self, producto, almacen, usuario_admin):
        mov = Movimiento.objects.create(
            tipo=Movimiento.Tipo.AJUSTE,
            producto=producto,
            almacen=almacen,
            cantidad=Decimal("50"),
            realizada_por=usuario_admin,
        )
        assert mov.tipo == Movimiento.Tipo.AJUSTE

    def test_cantidad_minima(self, producto, almacen, usuario_admin):
        with pytest.raises(ValidationError):
            mov = Movimiento(
                tipo=Movimiento.Tipo.ENTRADA,
                producto=producto,
                almacen=almacen,
                cantidad=Decimal("0.0005"),
                realizada_por=usuario_admin,
            )
            mov.full_clean()

    def test_ordering_descendente(self, producto, almacen, usuario_admin):
        m1 = Movimiento.objects.create(tipo=Movimiento.Tipo.ENTRADA, producto=producto, almacen=almacen, cantidad=1, realizada_por=usuario_admin)
        m2 = Movimiento.objects.create(tipo=Movimiento.Tipo.SALIDA, producto=producto, almacen=almacen, cantidad=1, realizada_por=usuario_admin)
        qs = Movimiento.objects.all()
        assert qs[0] == m2
        assert qs[1] == m1
