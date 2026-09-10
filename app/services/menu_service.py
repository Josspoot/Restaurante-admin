"""Reglas de negocio del menu: categorias y productos."""
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dinero import redondear
from app.core.exceptions import RecursoNoEncontrado, ReglaDeNegocio
from app.models import Categoria, Producto
from app.repositories import CategoriaRepo, ProductoRepo
from app.schemas.categoria import CategoriaActualizar, CategoriaCrear
from app.schemas.producto import ProductoActualizar, ProductoCrear


class CategoriaService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CategoriaRepo(db)

    def listar(self, solo_activas: bool = False) -> list[Categoria]:
        return self.repo.listar_filtrado(solo_activas)

    def obtener(self, id_: int) -> Categoria:
        categoria = self.repo.obtener(id_)
        if not categoria:
            raise RecursoNoEncontrado(f"No existe la categoría {id_}")
        return categoria

    def crear(self, datos: CategoriaCrear) -> Categoria:
        if self.repo.por_nombre(datos.nombre):
            raise ReglaDeNegocio(f"Ya existe una categoría llamada '{datos.nombre}'")
        return self.repo.guardar(Categoria(**datos.model_dump()))

    def actualizar(self, id_: int, datos: CategoriaActualizar) -> Categoria:
        categoria = self.obtener(id_)
        for campo, valor in datos.model_dump(exclude_unset=True).items():
            setattr(categoria, campo, valor)
        return self.repo.guardar(categoria)

    def eliminar(self, id_: int) -> None:
        categoria = self.obtener(id_)
        if categoria.productos:
            raise ReglaDeNegocio(
                "No se puede eliminar una categoría con productos. "
                "Desactívala o mueve sus productos primero."
            )
        self.repo.eliminar(categoria)


class ProductoService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ProductoRepo(db)
        self.categorias = CategoriaService(db)

    def listar(self, **filtros) -> list[Producto]:
        return self.repo.buscar(**filtros)

    def obtener(self, id_: int) -> Producto:
        producto = self.repo.obtener(id_)
        if not producto:
            raise RecursoNoEncontrado(f"No existe el producto {id_}")
        return producto

    def crear(self, datos: ProductoCrear) -> Producto:
        self.categorias.obtener(datos.categoria_id)  # valida la FK antes de insertar
        payload = datos.model_dump()
        payload["precio"] = redondear(payload["precio"])
        return self.repo.guardar(Producto(**payload))

    def actualizar(self, id_: int, datos: ProductoActualizar) -> Producto:
        producto = self.obtener(id_)
        cambios = datos.model_dump(exclude_unset=True)
        if "categoria_id" in cambios:
            self.categorias.obtener(cambios["categoria_id"])
        if cambios.get("precio") is not None:
            cambios["precio"] = redondear(cambios["precio"])
        for campo, valor in cambios.items():
            setattr(producto, campo, valor)
        return self.repo.guardar(producto)

    def eliminar(self, id_: int) -> None:
        producto = self.obtener(id_)
        try:
            self.repo.eliminar(producto)
        except IntegrityError:
            # Esta referenciado por ordenes historicas: no se borra, se oculta.
            self.db.rollback()
            producto.disponible = False
            self.repo.guardar(producto)
            raise ReglaDeNegocio(
                "El producto aparece en órdenes anteriores, no se puede borrar. "
                "Se marcó como no disponible."
            )
