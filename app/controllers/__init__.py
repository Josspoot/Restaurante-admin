"""Capa CONTROLADOR: expone los servicios como endpoints HTTP."""
from fastapi import APIRouter

from app.controllers import (
    auth_controller,
    categoria_controller,
    orden_controller,
    producto_controller,
)

api_router = APIRouter()
api_router.include_router(auth_controller.router)
api_router.include_router(categoria_controller.router)
api_router.include_router(producto_controller.router)
api_router.include_router(orden_controller.router)

__all__ = ["api_router"]
