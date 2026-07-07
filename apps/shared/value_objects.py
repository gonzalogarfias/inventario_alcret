import re
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class PrecioVenta:
    valor: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.valor, Decimal):
            object.__setattr__(self, "valor", Decimal(str(self.valor)))
        if self.valor < 0:
            raise ValueError("El precio de venta no puede ser negativo")
        if self.valor > 999999999.99:
            raise ValueError("El precio de venta supera el máximo permitido")


@dataclass(frozen=True)
class CantidadStock:
    valor: int

    def __post_init__(self) -> None:
        if not isinstance(self.valor, int):
            raise ValueError("La cantidad de stock debe ser un entero")
        if self.valor < 0:
            raise ValueError("La cantidad de stock no puede ser negativa")


@dataclass(frozen=True)
class SKU:
    valor: str
    _patron = re.compile(r"^[A-Z0-9]{3,20}(-[A-Z0-9]{1,10})?$")

    def __post_init__(self) -> None:
        if not self._patron.match(self.valor):
            raise ValueError(
                "El SKU debe tener 3-20 caracteres alfanuméricos en mayúsculas, "
                "con guión opcional (ej: PROD-001)"
            )


@dataclass(frozen=True)
class EmailAddress:
    valor: str
    _patron = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

    def __post_init__(self) -> None:
        if not self._patron.match(self.valor):
            raise ValueError(f"Email inválido: {self.valor}")
