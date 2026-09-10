from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import RolUsuario


class UsuarioBase(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    email: EmailStr


class UsuarioRegistro(UsuarioBase):
    """Alta publica: siempre queda con rol CLIENTE."""

    # bcrypt ignora lo que pase de 72 bytes, asi que ese es el tope util.
    password: str = Field(min_length=8, max_length=72)


class UsuarioCrear(UsuarioRegistro):
    """Alta desde el panel de admin: aqui si se puede elegir el rol."""

    rol: RolUsuario = RolUsuario.CLIENTE


class UsuarioActualizar(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=120)
    rol: RolUsuario | None = None
    activo: bool | None = None


class UsuarioRespuesta(UsuarioBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rol: RolUsuario
    activo: bool
    creado_en: datetime


class UsuarioPublico(BaseModel):
    """Version reducida para anidar en otras respuestas.

    Sin correo: un cliente que abre su orden no tiene por que ver el email
    del mesero que lo atendio.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    rol: RolUsuario


class Credenciales(BaseModel):
    """Login por JSON (el de /docs usa form-data de OAuth2)."""

    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioRespuesta
