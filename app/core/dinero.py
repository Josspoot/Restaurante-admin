"""Utilidades de dinero. Todo el proyecto usa Decimal, nunca float."""
from decimal import Decimal, ROUND_HALF_UP

CERO = Decimal("0.00")
_DOS_DECIMALES = Decimal("0.01")


def redondear(valor: Decimal | float | int) -> Decimal:
    """Redondea a 2 decimales con el criterio comercial (0.005 sube)."""
    return Decimal(str(valor)).quantize(_DOS_DECIMALES, rounding=ROUND_HALF_UP)
