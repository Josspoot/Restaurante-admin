"""Configuracion central de la aplicacion.

Equivalente al application.properties / application.yml de Spring Boot.
Los valores se leen de variables de entorno o del archivo .env.
"""
import secrets
import sys
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# Valor que trae el repositorio. Nunca debe llegar a usarse tal cual: si
# alguien firma tokens con una llave publica, cualquiera puede fabricarse uno
# de administrador.
LLAVE_PLACEHOLDER = "cambia-esta-llave-por-una-larga-y-aleatoria"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    APP_NAME: str = "Restaurante API"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"

    # "desarrollo" afloja algunas cosas (docs abiertas, CORS local).
    # Cualquier otro valor se trata como produccion.
    ENTORNO: str = "desarrollo"

    # Persistencia
    DATABASE_URL: str = "sqlite:///./restaurante.db"

    # Seguridad (equivalente a Spring Security + JWT)
    SECRET_KEY: str = LLAVE_PLACEHOLDER
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # Fuerza bruta contra el login
    LOGIN_INTENTOS: int = 8
    LOGIN_VENTANA_SEGUNDOS: int = 300

    # Reglas de negocio
    IVA: float = 0.16

    # Origenes que pueden llamar a la API desde un navegador.
    # Nunca "*" junto con credenciales: eso permite que cualquier sitio lea
    # las respuestas de la API en nombre del usuario.
    CORS_ORIGINS: list[str] = [
        "http://localhost:8000", "http://127.0.0.1:8000",
        "http://localhost:8010", "http://127.0.0.1:8010",
        "http://localhost:5500", "http://127.0.0.1:5500",
    ]

    DOCS_PUBLICAS: bool = True

    @property
    def es_produccion(self) -> bool:
        return self.ENTORNO.lower() not in ("desarrollo", "dev", "local", "test")


def _asegurar_llave(config: Settings) -> Settings:
    """Impide que la aplicacion firme tokens con la llave de ejemplo."""
    if config.SECRET_KEY and config.SECRET_KEY != LLAVE_PLACEHOLDER:
        return config

    if config.es_produccion:
        sys.exit(
            "ERROR: SECRET_KEY sigue con el valor de ejemplo.\n"
            "Genera una y ponla en .env:\n"
            '  python -c "import secrets; print(secrets.token_urlsafe(48))"'
        )

    # En desarrollo no se detiene el arranque, pero tampoco se usa la llave
    # conocida: se genera una al vuelo (y las sesiones mueren en cada reinicio).
    config.SECRET_KEY = secrets.token_urlsafe(48)
    print(
        "\n  AVISO DE SEGURIDAD: no hay SECRET_KEY definida.\n"
        "  Se generó una temporal; cada reinicio cerrará las sesiones abiertas.\n"
        '  Para fijarla:  python -c "import secrets; print(secrets.token_urlsafe(48))"  ->  .env\n',
        file=sys.stderr,
    )
    return config


@lru_cache
def get_settings() -> Settings:
    """Cacheado para no releer el .env en cada request."""
    return _asegurar_llave(Settings())


settings = get_settings()
