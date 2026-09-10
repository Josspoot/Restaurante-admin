"""Dependencias compartidas: sesion de BD, usuario autenticado y control de roles.

Es el equivalente a la inyeccion de dependencias + @PreAuthorize de Spring.
"""
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import NoAutorizado, PermisoDenegado
from app.core.security import decodificar_token
from app.models import RolUsuario, Usuario
from app.repositories import UsuarioRepo

oauth2 = OAuth2PasswordBearer(tokenUrl=f"{settings.API_PREFIX}/auth/login")

DB = Annotated[Session, Depends(get_db)]


def get_usuario_actual(token: Annotated[str, Depends(oauth2)], db: DB) -> Usuario:
    payload = decodificar_token(token)
    usuario_id = payload.get("sub")
    if usuario_id is None:
        raise NoAutorizado("Token sin identificador de usuario")

    # Un "sub" manipulado no debe reventar con un 500 y su traza: es un token
    # invalido y punto.
    try:
        usuario_id = int(usuario_id)
    except (TypeError, ValueError):
        raise NoAutorizado("Token inválido")

    usuario = UsuarioRepo(db).obtener(usuario_id)
    if usuario is None:
        raise NoAutorizado("El usuario del token ya no existe")
    if not usuario.activo:
        raise NoAutorizado("La cuenta está desactivada")
    return usuario


UsuarioActual = Annotated[Usuario, Depends(get_usuario_actual)]


def requiere_roles(*roles: RolUsuario) -> Callable[[Usuario], Usuario]:
    """Fabrica de dependencias que restringe un endpoint a ciertos roles."""

    def verificar(usuario: UsuarioActual) -> Usuario:
        if usuario.rol not in roles:
            permitidos = ", ".join(r.value for r in roles)
            raise PermisoDenegado(f"Se requiere rol: {permitidos}")
        return usuario

    return verificar


# Atajos legibles para usar en los controladores
SoloAdmin = Annotated[Usuario, Depends(requiere_roles(RolUsuario.ADMIN))]
SoloPersonal = Annotated[Usuario, Depends(requiere_roles(RolUsuario.ADMIN, RolUsuario.MESERO))]
