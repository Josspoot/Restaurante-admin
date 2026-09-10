from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import EstadoItem, EstadoOrden, TipoOrden
from app.schemas.pago import PagoRespuesta
from app.schemas.usuario import UsuarioPublico


class OrdenItemCrear(BaseModel):
    producto_id: int
    cantidad: int = Field(gt=0, le=99)
    notas: str | None = Field(default=None, max_length=255)
    cuenta: int = Field(default=1, ge=1, le=20, description="A que cuenta se le carga al dividir")


class OrdenItemRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    producto_id: int
    nombre_producto: str
    cantidad: int
    precio_unitario: Decimal
    subtotal: Decimal
    notas: str | None
    tanda: int
    estado: EstadoItem
    cuenta: int
    creado_en: datetime


class OrdenCrear(BaseModel):
    tipo: TipoOrden = TipoOrden.LOCAL
    mesa: int | None = Field(default=None, gt=0, le=200)
    notas: str | None = Field(default=None, max_length=500)
    cliente_id: int | None = Field(
        default=None, description="Solo lo usa el personal; el cliente se toma del token"
    )
    items: list[OrdenItemCrear] = Field(min_length=1)


class OrdenCambiarEstado(BaseModel):
    estado: EstadoOrden


class TandaCambiarEstado(BaseModel):
    estado: EstadoItem


class ItemAsignarCuenta(BaseModel):
    cuenta: int = Field(ge=1, le=20)


class CuentaResumen(BaseModel):
    """Lo que debe una de las cuentas en que se dividio la mesa."""

    numero: int
    items: list[OrdenItemRespuesta]
    subtotal: Decimal
    impuestos: Decimal
    total: Decimal
    pagado: Decimal
    propina: Decimal
    saldo: Decimal
    pagada: bool


class TandaResumen(BaseModel):
    """Una ronda de platillos, tal como la ve la cocina."""

    numero: int
    estado: EstadoItem
    items: list[OrdenItemRespuesta]


class ComandaCocina(BaseModel):
    """Una tanda pendiente vista desde la cocina, con lo minimo para prepararla."""

    orden_id: int
    numero: str
    tipo: TipoOrden
    mesa: int | None
    tanda: int
    estado: EstadoItem
    notas: str | None
    mesero_id: int | None
    mesero: str | None
    creado_en: datetime
    items: list[OrdenItemRespuesta]


class OrdenRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    numero: str
    tipo: TipoOrden
    estado: EstadoOrden
    mesa: int | None
    notas: str | None
    cliente: UsuarioPublico | None
    mesero: UsuarioPublico | None
    items: list[OrdenItemRespuesta]
    pagos: list[PagoRespuesta]
    subtotal: Decimal
    impuestos: Decimal
    total: Decimal
    total_pagado: Decimal
    propina_total: Decimal
    saldo: Decimal
    pagada: bool
    ampliable: bool
    cerrada: bool
    cerrada_en: datetime | None
    cerrada_por: UsuarioPublico | None
    pendientes_para_cerrar: list[str]
    puede_cerrarse: bool
    creado_en: datetime
    actualizado_en: datetime
