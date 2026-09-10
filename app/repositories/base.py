"""Repositorio generico, equivalente a JpaRepository<T, ID> de Spring Data."""
from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import Base

T = TypeVar("T", bound=Base)


class RepositorioBase(Generic[T]):
    modelo: type[T]

    def __init__(self, db: Session):
        self.db = db

    def obtener(self, id_: int) -> T | None:
        return self.db.get(self.modelo, id_)

    def listar(self, skip: int = 0, limit: int = 100) -> list[T]:
        stmt = select(self.modelo).offset(skip).limit(limit)
        return list(self.db.scalars(stmt).unique())

    def guardar(self, entidad: T) -> T:
        self.db.add(entidad)
        self.db.commit()
        self.db.refresh(entidad)
        return entidad

    def eliminar(self, entidad: T) -> None:
        self.db.delete(entidad)
        self.db.commit()
