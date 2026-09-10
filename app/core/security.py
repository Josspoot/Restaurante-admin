"""Hashing de contrasenas y emision/validacion de tokens JWT."""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings
from app.core.exceptions import NoAutorizado

# bcrypt solo considera los primeros 72 bytes de la contrasena.
_LIMITE_BCRYPT = 72

# Hash de descarte para gastar el mismo tiempo cuando el correo no existe.
# Sin esto, un "no existe" responde en microsegundos y un "existe pero la
# contrasena falla" tarda lo que tarda bcrypt: la diferencia deja adivinar
# que correos estan registrados.
_HASH_SENUELO = bcrypt.hashpw(b"senuelo-de-tiempo-constante", bcrypt.gensalt())


def hashear_password(password: str) -> str:
    return bcrypt.hashpw(password.encode()[:_LIMITE_BCRYPT], bcrypt.gensalt()).decode()


def verificar_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode()[:_LIMITE_BCRYPT], hashed.encode())
    except ValueError:
        return False


def quemar_tiempo() -> None:
    """Ejecuta un bcrypt de mentira para igualar el tiempo de respuesta."""
    bcrypt.checkpw(b"senuelo-de-tiempo-constante", _HASH_SENUELO)


def crear_token(sub: str, rol: str) -> str:
    """Genera un JWT firmado con el id del usuario y su rol."""
    expira = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": sub, "rol": rol, "exp": expira, "iat": datetime.now(timezone.utc)}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decodificar_token(token: str) -> dict:
    try:
        # `algorithms` fijo evita que un token elija su propio algoritmo
        # (el clasico ataque de "alg: none" o de cambio HS/RS).
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
    except jwt.ExpiredSignatureError:
        raise NoAutorizado("El token expiró, inicia sesión de nuevo")
    except jwt.PyJWTError:
        raise NoAutorizado("Token inválido")
