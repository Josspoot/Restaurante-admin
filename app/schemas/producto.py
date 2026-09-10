from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.categoria import CategoriaRespuesta


class ProductoBase(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    descripcion: str | None = Field(default=None, max_length=500)
    precio: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    imagen_url: str | None = Field(default=None, max_length=500)


class ProductoCrear(ProductoBase):
    categoria_id: int
    disponible: bool = True


class ProductoActualizar(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=120)
    descripcion: str | None = Field(default=None, max_length=500)
    precio: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    imagen_url: str | None = Field(default=None, max_length=500)
    categoria_id: int | None = None
    disponible: bool | None = None


class ProductoRespuesta(ProductoBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    disponible: bool
    categoria: CategoriaRespuesta
