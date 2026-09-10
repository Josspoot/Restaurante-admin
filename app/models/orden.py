from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import EstadoOrden, TipoOrden

CERO = Decimal("0.00")


def _enum(tipo):
    return SAEnum(tipo, native_enum=False, values_callable=lambda e: [i.value for i in e])


class Orden(Base):
    """Cabecera de una comanda. Los totales se guardan calculados (desnormalizados)
    para que una factura vieja no cambie si despues suben los precios del menu."""

    __tablename__ = "ordenes"

    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)

    tipo: Mapped[TipoOrden] = mapped_column(_enum(TipoOrden), default=TipoOrden.LOCAL, nullable=False)
    estado: Mapped[EstadoOrden] = mapped_column(
        _enum(EstadoOrden), default=EstadoOrden.PENDIENTE, nullable=False, index=True
    )
    mesa: Mapped[int | None] = mapped_column(Integer)
    notas: Mapped[str | None] = mapped_column(String(500))

    cliente_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), index=True)
    mesero_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), index=True)

    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=CERO, nullable=False)
    impuestos: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=CERO, nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=CERO, nullable=False)

    # Mesa cerrada: la orden quedo terminada al 100% y ya no admite cambios.
    cerrada_en: Mapped[datetime | None] = mapped_column(DateTime)
    cerrada_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))

    creado_en: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    items: Mapped[list["OrdenItem"]] = relationship(  # noqa: F821
        back_populates="orden", cascade="all, delete-orphan", lazy="selectin"
    )
    pagos: Mapped[list["Pago"]] = relationship(  # noqa: F821
        back_populates="orden", cascade="all, delete-orphan", lazy="selectin"
    )
    cliente: Mapped["Usuario | None"] = relationship(  # noqa: F821
        foreign_keys=[cliente_id], lazy="joined"
    )
    cerrada_por: Mapped["Usuario | None"] = relationship(  # noqa: F821
        foreign_keys=[cerrada_por_id], lazy="joined"
    )
    mesero: Mapped["Usuario | None"] = relationship(  # noqa: F821
        foreign_keys=[mesero_id], lazy="joined"
    )

    # --- Propiedades derivadas (no se guardan en la BD) ---

    @property
    def total_pagado(self) -> Decimal:
        return sum((p.monto for p in self.pagos), CERO)

    @property
    def propina_total(self) -> Decimal:
        return sum((p.propina for p in self.pagos), CERO)

    @property
    def saldo(self) -> Decimal:
        return self.total - self.total_pagado

    @property
    def pagada(self) -> bool:
        return self.saldo <= CERO

    @property
    def cerrada(self) -> bool:
        return self.cerrada_en is not None

    @property
    def pendientes_para_cerrar(self) -> list[str]:
        """Que falta para poder dar la mesa por terminada.

        Es la unica definicion de la regla: el servicio la usa para rechazar el
        cierre y la interfaz para pintar la lista de requisitos.
        """
        if self.estado == EstadoOrden.CANCELADA:
            return ["La orden está cancelada"]
        faltas = []
        if self.estado != EstadoOrden.ENTREGADA:
            faltas.append("Faltan platillos por entregar")
        if not self.pagada:
            faltas.append(f"Faltan ${self.saldo} por cobrar")
        return faltas

    @property
    def puede_cerrarse(self) -> bool:
        return not self.cerrada and not self.pendientes_para_cerrar

    @property
    def ampliable(self) -> bool:
        """Si ahora mismo se le pueden agregar platillos.

        Comer en el local admite pedir mas en cualquier momento; para llevar y
        a domicilio se cierran en cuanto la comanda entra a cocina.
        """
        if self.estado == EstadoOrden.CANCELADA or self.cerrada:
            return False
        return self.tipo == TipoOrden.LOCAL or self.estado == EstadoOrden.PENDIENTE

    @property
    def tandas(self) -> list[int]:
        return sorted({i.tanda for i in self.items})

    @property
    def cuentas(self) -> list[int]:
        return sorted({i.cuenta for i in self.items})

    def __repr__(self) -> str:
        return f"<Orden {self.numero} {self.estado} ${self.total}>"
