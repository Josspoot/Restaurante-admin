from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Categoria(Base):
    __tablename__ = "categorias"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(255))
    activa: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    productos: Mapped[list["Producto"]] = relationship(  # noqa: F821
        back_populates="categoria", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Categoria {self.id} {self.nombre}>"
