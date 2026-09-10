from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import EstadoItem


class OrdenItem(Base):
    """Linea de una orden. Guarda una copia del precio del producto en el
    momento de la venta (snapshot), igual que en un sistema de punto de venta real."""

    __tablename__ = "orden_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    orden_id: Mapped[int] = mapped_column(
        ForeignKey("ordenes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"), nullable=False)

    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    notas: Mapped[str | None] = mapped_column(String(255))

    # Ronda en la que se pidio. Todo lo que se manda junto a la cocina comparte
    # tanda; agregar platillos a una orden en marcha abre la siguiente.
    tanda: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Cada platillo avanza por su cuenta: la tanda 2 puede estar pendiente
    # mientras la tanda 1 ya se entrego.
    estado: Mapped[EstadoItem] = mapped_column(
        SAEnum(EstadoItem, native_enum=False, values_callable=lambda e: [i.value for i in e]),
        default=EstadoItem.PENDIENTE,
        nullable=False,
    )

    # Cuenta a la que se le carga este platillo al dividir la mesa (1, 2, 3...).
    cuenta: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    creado_en: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    orden: Mapped["Orden"] = relationship(back_populates="items")  # noqa: F821
    producto: Mapped["Producto"] = relationship(lazy="joined")  # noqa: F821

    @property
    def nombre_producto(self) -> str:
        return self.producto.nombre if self.producto else "(producto eliminado)"

    def __repr__(self) -> str:
        return f"<OrdenItem t{self.tanda} c{self.cuenta} {self.cantidad}x producto:{self.producto_id}>"
