from decimal import Decimal

import pytest

from apps.shared.value_objects import SKU, CantidadStock, EmailAddress, PrecioVenta, ValidationError


class TestSKU:
    def test_sku_valido(self):
        sku = SKU.de_string("ABC-123")
        assert sku.valor == "ABC-123"

    def test_sku_vacio_lanza_error(self):
        with pytest.raises(ValidationError, match="no puede estar vacío"):
            SKU.de_string("")

    def test_sku_minusculas_se_normaliza(self):
        sku = SKU.de_string("abc-123")
        assert sku.valor == "ABC-123"

    def test_sku_patron_invalido(self):
        with pytest.raises(ValidationError, match="no cumple el patrón"):
            SKU.de_string("abc!!!")

    def test_sku_str(self):
        assert str(SKU.de_string("XYZ-999")) == "XYZ-999"


class TestPrecioVenta:
    def test_precio_valido(self):
        p = PrecioVenta.de_string("150.50")
        assert p.valor == Decimal("150.50")

    def test_precio_minimo(self):
        p = PrecioVenta.de_string("0.01")
        assert p.valor == Decimal("0.01")

    def test_precio_cero_lanza_error(self):
        with pytest.raises(ValidationError, match=">="):
            PrecioVenta.de_string("0")

    def test_precio_maximo_excedido(self):
        with pytest.raises(ValidationError, match="<="):
            PrecioVenta.de_string("1000000000")

    def test_precio_mas_de_2_decimales(self):
        with pytest.raises(ValidationError, match="máximo 2 decimales"):
            PrecioVenta.de_string("10.999")

    def test_precio_invalido(self):
        with pytest.raises(ValidationError, match="número decimal válido"):
            PrecioVenta.de_string("no-es-numero")

    def test_precio_str(self):
        assert str(PrecioVenta.de_string("99.99")) == "99.99"


class TestCantidadStock:
    def test_cantidad_valida(self):
        c = CantidadStock.de_string("100.500")
        assert c.valor == Decimal("100.500")

    def test_cantidad_cero_valida(self):
        c = CantidadStock.de_string("0")
        assert c.valor == Decimal("0")

    def test_cantidad_negativa(self):
        with pytest.raises(ValidationError, match=">="):
            CantidadStock.de_string("-1")

    def test_cantidad_maximo_excedido(self):
        with pytest.raises(ValidationError, match="<="):
            CantidadStock.de_string("1000000000")

    def test_cantidad_mas_de_3_decimales(self):
        with pytest.raises(ValidationError, match="máximo 3 decimales"):
            CantidadStock.de_string("10.9999")

    def test_es_positiva(self):
        assert CantidadStock.de_string("1").es_positiva() is True
        assert CantidadStock.de_string("0").es_positiva() is False

    def test_suma(self):
        a = CantidadStock.de_string("10")
        b = CantidadStock.de_string("5")
        assert (a + b).valor == Decimal("15")

    def test_resta_valida(self):
        a = CantidadStock.de_string("10")
        b = CantidadStock.de_string("3")
        assert (a - b).valor == Decimal("7")

    def test_resta_negativa_lanza_error(self):
        a = CantidadStock.de_string("3")
        b = CantidadStock.de_string("10")
        with pytest.raises(ValidationError, match="negativo"):
            a - b


class TestEmailAddress:
    def test_email_valido(self):
        e = EmailAddress.de_string("Test@Example.COM")
        assert e.valor == "test@example.com"

    def test_email_vacio(self):
        with pytest.raises(ValidationError, match="no puede estar vacío"):
            EmailAddress.de_string("")

    def test_email_invalido(self):
        with pytest.raises(ValidationError, match="inválido"):
            EmailAddress.de_string("no-es-email")

    def test_dominio(self):
        e = EmailAddress.de_string("juan@gmail.com")
        assert e.dominio == "gmail.com"

    def test_usuario(self):
        e = EmailAddress.de_string("juan@gmail.com")
        assert e.usuario == "juan"

    def test_str(self):
        assert str(EmailAddress.de_string("a@b.com")) == "a@b.com"
