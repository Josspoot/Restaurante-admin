"""Punto de entrada de la aplicacion (equivale a la clase con @SpringBootApplication)."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.controllers import api_router
from app.core.config import settings
from app.core.database import crear_tablas
from app.core.exceptions import (
    DemasiadosIntentos,
    ErrorDominio,
    NoAutorizado,
    PermisoDenegado,
    RecursoNoEncontrado,
    ReglaDeNegocio,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Al arrancar: crea el archivo SQLite y las tablas si no existen.
    crear_tablas()
    yield


# En producción la documentación deja de ser pública: describe todos los
# endpoints y sus esquemas, que es un mapa gratis para quien vaya a atacar.
_docs = settings.DOCS_PUBLICAS and not settings.es_produccion

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    docs_url="/docs" if _docs else None,
    redoc_url="/redoc" if _docs else None,
    openapi_url="/openapi.json" if _docs else None,
    description=(
        "API REST para la operación de un restaurante: menú, órdenes, "
        "cobros y facturación. Arquitectura por capas (modelo / servicio / controlador) "
        "con persistencia en SQLite."
    ),
    lifespan=lifespan,
)

# Un "*" en allow_origins junto con allow_credentials hace que Starlette
# refleje el Origin de quien pregunte: cualquier web podría leer las respuestas
# de la API en nombre del usuario. Si alguien configura "*", se apagan las
# credenciales para que el navegador siga bloqueando ese caso.
_origenes_abiertos = "*" in settings.CORS_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=not _origenes_abiertos,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=600,
)


# La documentación carga Swagger UI desde un CDN, así que necesita una política
# más suelta que el resto de la aplicación.
CSP_APP = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "   # el front usa atributos style en línea
    "img-src 'self' data:; "
    "font-src 'self'; "
    "connect-src 'self'; "
    "form-action 'self'; "
    "base-uri 'self'; "
    "object-src 'none'; "
    "frame-ancestors 'none'"
)
CSP_DOCS = (
    "default-src 'self'; "
    "script-src 'self' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "img-src 'self' data: https://fastapi.tiangolo.com; "
    "font-src 'self' https://cdn.jsdelivr.net; "
    "frame-ancestors 'none'"
)
RUTAS_DOCS = ("/docs", "/redoc", "/openapi.json")


@app.middleware("http")
async def cabeceras_de_seguridad(request: Request, call_next):
    """Defensas que viven en la cabecera y no en el código.

    Sin esto la página se puede meter en un iframe ajeno (clickjacking) y un
    XSS tendría permiso para cargar scripts de cualquier dominio.
    """
    respuesta = await call_next(request)
    es_doc = request.url.path.startswith(RUTAS_DOCS)

    respuesta.headers["Content-Security-Policy"] = CSP_DOCS if es_doc else CSP_APP
    respuesta.headers["X-Content-Type-Options"] = "nosniff"
    respuesta.headers["X-Frame-Options"] = "DENY"
    respuesta.headers["Referrer-Policy"] = "same-origin"
    respuesta.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
    respuesta.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    if settings.es_produccion:
        respuesta.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    # No anunciar el servidor. Ojo: la cabecera `server` la pone uvicorn en su
    # capa de protocolo, así que para quitarla del todo hay que arrancarlo con
    # --no-server-header; esto solo cubre lo que añada la propia aplicación.
    if "server" in respuesta.headers:
        del respuesta.headers["server"]
    return respuesta

# --- Traduccion de errores de dominio a respuestas HTTP (como @ControllerAdvice) ---

CODIGOS: list[tuple[type[ErrorDominio], int]] = [
    (RecursoNoEncontrado, 404),
    (ReglaDeNegocio, 409),
    (NoAutorizado, 401),
    (PermisoDenegado, 403),
    (DemasiadosIntentos, 429),
]


def _registrar_manejador(excepcion: type[ErrorDominio], codigo: int) -> None:
    @app.exception_handler(excepcion)
    async def manejar(request: Request, exc: ErrorDominio):  # noqa: ARG001
        headers = {"WWW-Authenticate": "Bearer"} if codigo == 401 else None
        return JSONResponse(
            status_code=codigo,
            content={"error": exc.__class__.__name__, "detalle": exc.mensaje},
            headers=headers,
        )


for _exc, _codigo in CODIGOS:
    _registrar_manejador(_exc, _codigo)


app.include_router(api_router, prefix=settings.API_PREFIX)

# El front es HTML/CSS/JS estatico: lo sirve la misma aplicacion en /app.
# Asi no hay que levantar un segundo servidor ni pelear con CORS en desarrollo.
FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
HAY_FRONTEND = FRONTEND.is_dir()

if HAY_FRONTEND:
    app.mount("/app", StaticFiles(directory=FRONTEND, html=True), name="frontend")


@app.get("/", include_in_schema=False)
def raiz():
    if HAY_FRONTEND:
        return RedirectResponse(url="/app/")
    return RedirectResponse(url="/docs" if _docs else f"{settings.API_PREFIX}/salud")


@app.get(f"{settings.API_PREFIX}/salud", tags=["Sistema"])
def salud():
    """Health check para el front o para un monitor."""
    return {"estado": "ok", "app": settings.APP_NAME, "version": settings.VERSION}
