from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import MetodoPago


class Pago(Base):
    """Un abono a una orden. Una orden puede tener varios pagos (cuenta dividida)."""

    __tablename__ = "pagos"

    id: Mapped[int] = mapped_column(primary_key=True)
    orden_id: Mapped[int] = mapped_column(
        ForeignKey("ordenes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    metodo: Mapped[MetodoPago] = mapped_column(
        SAEnum(MetodoPago, native_enum=False, values_callable=lambda e: [i.value for i in e]),
        nullable=False,
    )
    monto: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    propina: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)

    # Si la propina se pidio por porcentaje se guarda cual fue, para poder
    # explicar en el ticket de donde salio el importe.
    propina_porcentaje: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))

    # Cuenta que se esta saldando. None = pago general contra toda la orden.
    cuenta: Mapped[int | None] = mapped_column(Integer)

    referencia: Mapped[str | None] = mapped_column(String(120))
    creado_en: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    orden: Mapped["Orden"] = relationship(back_populates="pagos")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Pago {self.metodo} ${self.monto}>"
