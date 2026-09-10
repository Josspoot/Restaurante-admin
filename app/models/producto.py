from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Producto(Base):
    """Un platillo o bebida del menu."""

    __tablename__ = "productos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(500))
    precio: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    disponible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    imagen_url: Mapped[str | None] = mapped_column(String(500))

    categoria_id: Mapped[int] = mapped_column(
        ForeignKey("categorias.id", ondelete="CASCADE"), nullable=False, index=True
    )
    categoria: Mapped["Categoria"] = relationship(  # noqa: F821
        back_populates="productos", lazy="joined"
    )

    def __repr__(self) -> str:
        return f"<Producto {self.id} {self.nombre} ${self.precio}>"
