from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import DB, SoloAdmin, UsuarioActual
from app.core.config import settings
from app.core.exceptions import NoAutorizado
from app.core.limitador import limitador_cuenta, limitador_login, limitador_registro
from app.schemas.usuario import (
    Credenciales,
    Token,
    UsuarioCrear,
    UsuarioRegistro,
    UsuarioRespuesta,
)
from app.services import AuthService

router = APIRouter(prefix="/auth", tags=["Autenticación"])


def _ip(peticion: Request) -> str:
    """IP del cliente, para contar intentos de login.

    X-Forwarded-For solo se lee si CONFIAR_PROXY está activo. Sin un proxy de
    verdad al frente, cualquiera podría falsificar esa cabecera y estrenar
    cupo de intentos en cada petición; detrás de uno (Render, Railway, Nginx)
    ocurre lo contrario: sin leerla, todos los usuarios comparten la IP del
    proxy y el límite se vuelve un bloqueo colectivo.
    """
    if settings.CONFIAR_PROXY:
        reenviada = peticion.headers.get("x-forwarded-for", "")
        if reenviada:
            return reenviada.split(",")[0].strip()
    return peticion.client.host if peticion.client else "desconocida"


def _entrar(db, peticion: Request, email: str, password: str) -> Token:
    """Login con freno de intentos, compartido por las dos rutas de entrada."""
    correo = email.strip().lower()
    ip, cuenta = f"ip:{_ip(peticion)}", f"cuenta:{correo}"

    # Dos cupos: uno estrecho por IP y otro más ancho por cuenta.
    limitador_login.revisar(ip)
    limitador_cuenta.revisar(cuenta)

    servicio = AuthService(db)
    try:
        usuario = servicio.autenticar(correo, password)
    except NoAutorizado:
        limitador_login.anotar_fallo(ip)
        limitador_cuenta.anotar_fallo(cuenta)
        raise

    limitador_cuenta.limpiar(cuenta)
    return Token(access_token=servicio.emitir_token(usuario), usuario=usuario)


@router.post("/registro", response_model=UsuarioRespuesta, status_code=status.HTTP_201_CREATED)
def registro(datos: UsuarioRegistro, db: DB, peticion: Request):
    """Alta pública de clientes. La contraseña necesita al menos 8 caracteres."""
    limitador_registro.revisar(f"ip:{_ip(peticion)}")
    limitador_registro.anotar_fallo(f"ip:{_ip(peticion)}")
    return AuthService(db).registrar(datos)


@router.post("/login", response_model=Token)
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DB, peticion: Request):
    """Login en formato OAuth2 (form-data). Es el que usa el botón Authorize de /docs.

    El campo `username` es el correo del usuario. Tras varios intentos fallidos
    la ruta se bloquea un rato (429).
    """
    return _entrar(db, peticion, form.username, form.password)


@router.post("/login-json", response_model=Token)
def login_json(datos: Credenciales, db: DB, peticion: Request):
    """Mismo login pero recibiendo JSON: más cómodo desde el front."""
    return _entrar(db, peticion, datos.email, datos.password)


@router.get("/yo", response_model=UsuarioRespuesta)
def perfil(usuario: UsuarioActual):
    """Datos del usuario dueño del token."""
    return usuario


@router.post("/usuarios", response_model=UsuarioRespuesta, status_code=status.HTTP_201_CREATED)
def crear_usuario(datos: UsuarioCrear, db: DB, _: SoloAdmin):
    """Alta de personal (meseros y administradores). Solo ADMIN."""
    return AuthService(db).crear_desde_admin(datos)
