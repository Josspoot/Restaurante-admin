from fastapi import APIRouter, Query, status

from app.api.deps import DB, SoloAdmin
from app.schemas.producto import ProductoActualizar, ProductoCrear, ProductoRespuesta
from app.services import ProductoService

router = APIRouter(prefix="/productos", tags=["Productos (menú)"])


@router.get("", response_model=list[ProductoRespuesta])
def listar(
    db: DB,
    categoria_id: int | None = None,
    disponible: bool | None = None,
    texto: str | None = Query(default=None, description="Busca en nombre y descripción"),
    skip: int = 0,
    limit: int = Query(default=100, le=200),
):
    """Catálogo público del menú, con filtros para el front."""
    return ProductoService(db).listar(
        categoria_id=categoria_id, disponible=disponible, texto=texto, skip=skip, limit=limit
    )


@router.get("/{producto_id}", response_model=ProductoRespuesta)
def obtener(producto_id: int, db: DB):
    return ProductoService(db).obtener(producto_id)


@router.post("", response_model=ProductoRespuesta, status_code=status.HTTP_201_CREATED)
def crear(datos: ProductoCrear, db: DB, _: SoloAdmin):
    return ProductoService(db).crear(datos)


@router.patch("/{producto_id}", response_model=ProductoRespuesta)
def actualizar(producto_id: int, datos: ProductoActualizar, db: DB, _: SoloAdmin):
    return ProductoService(db).actualizar(producto_id, datos)


@router.delete("/{producto_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar(producto_id: int, db: DB, _: SoloAdmin):
    ProductoService(db).eliminar(producto_id)
