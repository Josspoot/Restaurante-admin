from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import MetodoPago


class PagoCrear(BaseModel):
    metodo: MetodoPago
    monto: Decimal | None = Field(
        default=None, gt=0, max_digits=10, decimal_places=2,
        description="Si se omite, se cobra el saldo completo de la cuenta",
    )
    cuenta: int | None = Field(
        default=None, ge=1, le=20,
        description="Cuenta que se salda. Obligatorio si la mesa esta dividida",
    )
    propina: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    propina_porcentaje: Decimal | None = Field(
        default=None, ge=0, le=100, max_digits=5, decimal_places=2,
        description="Alternativa a `propina`: se calcula sobre el monto de este pago",
    )
    referencia: str | None = Field(
        default=None, max_length=120, description="Autorización de tarjeta o folio de transferencia"
    )

    @model_validator(mode="after")
    def _una_sola_forma_de_propina(self):
        if self.propina is not None and self.propina_porcentaje is not None:
            raise ValueError("Manda la propina como importe o como porcentaje, no ambos")
        return self


class PagoRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    metodo: MetodoPago
    monto: Decimal
    propina: Decimal
    propina_porcentaje: Decimal | None
    cuenta: int | None
    referencia: str | None
    creado_en: datetime


class LineaFactura(BaseModel):
    cantidad: int
    descripcion: str
    precio_unitario: Decimal
    importe: Decimal


class Factura(BaseModel):
    """Ticket final, de la orden completa o de una sola cuenta."""

    orden_numero: str
    fecha: datetime
    mesa: int | None
    atendio: str | None
    cliente: str | None
    cuenta: int | None = Field(default=None, description="None = ticket de toda la mesa")
    total_cuentas: int
    lineas: list[LineaFactura]
    subtotal: Decimal
    tasa_iva: Decimal
    impuestos: Decimal
    total: Decimal
    pagos: list[PagoRespuesta]
    total_pagado: Decimal
    propina_total: Decimal
    saldo: Decimal
    pagada: bool
