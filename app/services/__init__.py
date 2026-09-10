"""Capa de servicios: aqui vive toda la logica de negocio.

Los controladores no deciden nada; solo traducen HTTP <-> servicios.
"""
from app.services.auth_service import AuthService
from app.services.menu_service import CategoriaService, ProductoService
from app.services.orden_service import OrdenService
from app.services.pago_service import PagoService

__all__ = ["AuthService", "CategoriaService", "OrdenService", "PagoService", "ProductoService"]
