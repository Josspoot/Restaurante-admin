from sqlalchemy import select

from app.models import Categoria
from app.repositories.base import RepositorioBase


class CategoriaRepo(RepositorioBase[Categoria]):
    modelo = Categoria

    def por_nombre(self, nombre: str) -> Categoria | None:
        return self.db.scalar(select(Categoria).where(Categoria.nombre == nombre))

    def listar_filtrado(self, solo_activas: bool = False) -> list[Categoria]:
        stmt = select(Categoria).order_by(Categoria.nombre)
        if solo_activas:
            stmt = stmt.where(Categoria.activa.is_(True))
        return list(self.db.scalars(stmt).unique())
