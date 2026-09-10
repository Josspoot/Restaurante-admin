"""Capa de repositorios: unico lugar del proyecto que arma consultas SQL."""
from app.repositories.categoria_repo import CategoriaRepo
from app.repositories.orden_repo import OrdenRepo
from app.repositories.producto_repo import ProductoRepo
from app.repositories.usuario_repo import UsuarioRepo

__all__ = ["CategoriaRepo", "OrdenRepo", "ProductoRepo", "UsuarioRepo"]
