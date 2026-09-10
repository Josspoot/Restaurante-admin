from fastapi import APIRouter, status

from app.api.deps import DB, SoloAdmin
from app.schemas.categoria import CategoriaActualizar, CategoriaCrear, CategoriaRespuesta
from app.services import CategoriaService

router = APIRouter(prefix="/categorias", tags=["Categorías"])


@router.get("", response_model=list[CategoriaRespuesta])
def listar(db: DB, solo_activas: bool = False):
    return CategoriaService(db).listar(solo_activas)


@router.get("/{categoria_id}", response_model=CategoriaRespuesta)
def obtener(categoria_id: int, db: DB):
    return CategoriaService(db).obtener(categoria_id)


@router.post("", response_model=CategoriaRespuesta, status_code=status.HTTP_201_CREATED)
def crear(datos: CategoriaCrear, db: DB, _: SoloAdmin):
    return CategoriaService(db).crear(datos)


@router.patch("/{categoria_id}", response_model=CategoriaRespuesta)
def actualizar(categoria_id: int, datos: CategoriaActualizar, db: DB, _: SoloAdmin):
    return CategoriaService(db).actualizar(categoria_id, datos)


@router.delete("/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar(categoria_id: int, db: DB, _: SoloAdmin):
    CategoriaService(db).eliminar(categoria_id)
