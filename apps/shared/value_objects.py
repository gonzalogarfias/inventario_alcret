from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Self


class ValidationError(ValueError):
    pass


@dataclass(frozen=True)
class SKU:
    valor: str
    _PATRON = re.compile(r"^[A-Z0-9]{3,20}(-[A-Z0-9]{1,10})?$")

    def __post_init__(self) -> None:
        if not self.valor:
            raise ValidationError("SKU no puede estar vacío")
        if not self._PATRON.match(self.valor):
            raise ValidationError(
                f"SKU '{self.valor}' no cumple el patrón "
                f"^[A-Z0-9]{{3,20}}(-[A-Z0-9]{{1,10}})?$"
            )

    @classmethod
    def de_string(cls, valor: str) -> Self:
        return cls(valor=valor.strip().upper())

    def __str__(self) -> str:
        return self.valor


@dataclass(frozen=True)
class PrecioVenta:
    valor: Decimal
    _MIN = Decimal("0.01")
    _MAX = Decimal("999999999.99")

    def __post_init__(self) -> None:
        try:
            valor = Decimal(self.valor)
        except (InvalidOperation, TypeError):
            raise ValidationError(
                f"PrecioVenta debe ser un número decimal válido, got {self.valor!r}"
            )

        if valor < self._MIN:
            raise ValidationError(f"PrecioVenta debe ser >= {self._MIN}")
        if valor > self._MAX:
            raise ValidationError(f"PrecioVenta debe ser <= {self._MAX}")
        if valor.as_tuple().exponent < -2:
            raise ValidationError("PrecioVenta debe tener máximo 2 decimales")

        object.__setattr__(self, "valor", valor.quantize(Decimal("0.01")))

    @classmethod
    def de_string(cls, valor: str | float | Decimal) -> Self:
        return cls(valor=valor)

    def __str__(self) -> str:
        return str(self.valor)


@dataclass(frozen=True)
class CantidadStock:
    valor: Decimal
    _MIN = Decimal("0")
    _MAX = Decimal("999999999.999")

    def __post_init__(self) -> None:
        try:
            valor = Decimal(self.valor)
        except (InvalidOperation, TypeError):
            raise ValidationError(
                f"CantidadStock debe ser un número decimal válido, got {self.valor!r}"
            )

        if valor < self._MIN:
            raise ValidationError(f"CantidadStock debe ser >= {self._MIN}")
        if valor > self._MAX:
            raise ValidationError(f"CantidadStock debe ser <= {self._MAX}")
        if valor.as_tuple().exponent < -3:
            raise ValidationError("CantidadStock debe tener máximo 3 decimales")

        object.__setattr__(self, "valor", valor.quantize(Decimal("0.001")))

    @classmethod
    def de_string(cls, valor: str | float | Decimal) -> Self:
        return cls(valor=Decimal(str(valor)))

    def __str__(self) -> str:
        return str(self.valor)

    def es_positiva(self) -> bool:
        """True si la cantidad es mayor que cero."""
        return self.valor > Decimal("0")

    def __add__(self, other: CantidadStock) -> CantidadStock:
        """Suma dos cantidades."""
        return CantidadStock(valor=self.valor + other.valor)

    def __sub__(self, other: CantidadStock) -> CantidadStock:
        """Resta dos cantidades. Lanza ValidationError si resultado negativo."""
        resultado = self.valor - other.valor
        if resultado < Decimal("0"):
            raise ValidationError("Resultado de resta sería negativo")
        return CantidadStock(valor=resultado)


@dataclass(frozen=True)
class EmailAddress:

    valor: str
    _PATRON = re.compile(
        r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    )

    def __post_init__(self) -> None:
        if not self.valor:
            raise ValidationError("Email no puede estar vacío")
        if not self._PATRON.match(self.valor):
            raise ValidationError(f"Email inválido: {self.valor}")

    @classmethod
    def de_string(cls, valor: str) -> Self:
        """Factory method con strip."""
        return cls(valor=valor.strip().lower())

    def __str__(self) -> str:
        return self.valor

    @property
    def dominio(self) -> str:
        """Retorna el dominio del email (ej: gmail.com)."""
        return self.valor.split("@")[1]

    @property
    def usuario(self) -> str:
        """Retorna la parte local del email (ej: juan)."""
        return self.valor.split("@")[0]
