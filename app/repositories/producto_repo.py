from sqlalchemy import select

from app.models import Producto
from app.repositories.base import RepositorioBase


class ProductoRepo(RepositorioBase[Producto]):
    modelo = Producto

    def buscar(
        self,
        categoria_id: int | None = None,
        disponible: bool | None = None,
        texto: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Producto]:
        stmt = select(Producto)
        if categoria_id is not None:
            stmt = stmt.where(Producto.categoria_id == categoria_id)
        if disponible is not None:
            stmt = stmt.where(Producto.disponible.is_(disponible))
        if texto:
            patron = f"%{texto.strip()}%"
            stmt = stmt.where(Producto.nombre.ilike(patron) | Producto.descripcion.ilike(patron))
        stmt = stmt.order_by(Producto.nombre).offset(skip).limit(limit)
        return list(self.db.scalars(stmt).unique())
