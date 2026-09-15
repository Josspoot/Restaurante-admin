"""Andamiaje de las pruebas de extremo a extremo con Playwright.

A diferencia de las pruebas de la API, que llaman a la aplicación en el mismo
proceso, estas abren un navegador de verdad contra un servidor de verdad. Por
eso hace falta levantarlo: una sola vez por sesión, contra una base temporal
ya sembrada, y apagarlo al terminar.
"""
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

import httpx
import pytest
from playwright.sync_api import Page, expect

# Cuánto esperar a que una condición se cumpla antes de dar la prueba por mala.
# Playwright reintenta durante este tiempo en lugar de dormir a ciegas.
expect.set_options(timeout=8000)

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Cuentas de ejemplo que siembra seed.py, con el texto de su acceso rápido.
CUENTAS = {
    "admin": ("Admin", "admin@restaurante.com", "admin123"),
    "mesero": ("Mesero", "mesero@restaurante.com", "mesero123"),
    "cliente": ("Cliente", "cliente@correo.com", "cliente123"),
}


def _puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _esperar(url: str, segundos: float = 30) -> None:
    limite = time.monotonic() + segundos
    while time.monotonic() < limite:
        try:
            urllib.request.urlopen(url, timeout=1)
            return
        except (urllib.error.URLError, OSError):
            time.sleep(0.15)
    raise RuntimeError(f"El servidor no respondió en {segundos}s: {url}")


@pytest.fixture(scope="session")
def servidor(tmp_path_factory) -> str:
    """Levanta la aplicación en un puerto libre y devuelve su dirección.

    Es de sesión porque arrancar uvicorn cuesta un par de segundos y hacerlo
    por prueba multiplicaría el tiempo total. A cambio, las pruebas comparten
    base de datos: cada una debe crear lo suyo y afirmar sobre eso, nunca
    sobre totales globales.
    """
    base = tmp_path_factory.mktemp("e2e") / "e2e.db"
    entorno = {
        **os.environ,
        "DATABASE_URL": f"sqlite:///{base}",
        "ENTORNO": "desarrollo",          # deja visibles los accesos rápidos
        "SECRET_KEY": "llave-solo-para-pruebas-de-extremo-a-extremo-0123456789",
        "ADMIN_PASSWORD": "",             # conserva la contraseña de ejemplo
    }

    subprocess.run(
        [sys.executable, "seed.py"], cwd=RAIZ, env=entorno, check=True,
        capture_output=True,
    )

    puerto = _puerto_libre()
    proceso = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app",
         "--host", "127.0.0.1", "--port", str(puerto), "--no-server-header"],
        cwd=RAIZ, env=entorno, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    url = f"http://127.0.0.1:{puerto}"
    try:
        _esperar(f"{url}/api/v1/salud")
        yield url
    finally:
        proceso.terminate()
        try:
            proceso.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proceso.kill()


@pytest.fixture
def api(servidor):
    """Cliente HTTP autenticado, para preparar el escenario sin la interfaz.

    Montar una orden a base de clics es lento y hace que una prueba falle por
    razones que no está evaluando. Lo que no es el objeto de la prueba se
    prepara por API.
    """
    clientes = []

    def como(rol: str) -> httpx.Client:
        _, correo, clave = CUENTAS[rol]
        sesion = httpx.Client(base_url=f"{servidor}/api/v1", timeout=15)
        token = sesion.post(
            "/auth/login-json", json={"email": correo, "password": clave}
        ).json()["access_token"]
        sesion.headers["Authorization"] = f"Bearer {token}"
        clientes.append(sesion)
        return sesion

    yield como
    for sesion in clientes:
        sesion.close()


@pytest.fixture
def entrar(page: Page, servidor):
    """Entra por la interfaz con una de las cuentas de ejemplo."""

    def hacerlo(rol: str) -> Page:
        etiqueta, _, _ = CUENTAS[rol]
        page.goto(f"{servidor}/app/")
        page.get_by_role("button", name=etiqueta, exact=True).click()
        expect(page.locator("#cabecera")).to_be_visible()
        return page

    return hacerlo


@pytest.fixture(autouse=True)
def _errores_de_consola(page: Page):
    """Ninguna prueba debería dejar errores en la consola del navegador.

    Se comprueba al final de cada una: así un fallo silencioso de JavaScript
    rompe la prueba en vez de pasar desapercibido.
    """
    fallos = []
    page.on("pageerror", lambda e: fallos.append(f"excepción: {e}"))
    page.on(
        "console",
        lambda m: fallos.append(f"consola {m.type}: {m.text}")
        if m.type == "error"
        else None,
    )
    yield
    # El 422 de una validación deliberada no es un fallo de la aplicación.
    graves = [f for f in fallos if "422" not in f and "Unprocessable" not in f]
    assert not graves, "errores en el navegador: " + " | ".join(graves)


def pytest_collection_modifyitems(items):
    """Marca todo lo de esta carpeta como e2e, para poder filtrarlo."""
    for item in items:
        if "tests/e2e/" in str(item.fspath).replace(os.sep, "/"):
            item.add_marker(pytest.mark.e2e)
