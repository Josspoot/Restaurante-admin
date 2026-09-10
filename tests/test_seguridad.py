"""Pruebas de las defensas: fuerza bruta, cabeceras, tokens y fuga de datos."""
import jwt
import pytest

from app.core.config import LLAVE_PLACEHOLDER, settings
from app.core.security import crear_token

CREDENCIALES_MALAS = {"email": "admin@test.com", "password": "loQueSea123"}


# ============================================== configuración

def test_no_se_firma_con_la_llave_de_ejemplo():
    """El fallo más grave posible: firmar tokens con una llave que está en el repo."""
    assert settings.SECRET_KEY != LLAVE_PLACEHOLDER
    assert len(settings.SECRET_KEY) >= 32


def test_cors_no_abre_a_cualquiera_con_credenciales():
    from app.main import _origenes_abiertos

    # O la lista es concreta, o si alguien pone "*" se apagan las credenciales.
    assert not _origenes_abiertos or "*" in settings.CORS_ORIGINS
    assert "*" not in settings.CORS_ORIGINS


# ============================================== fuerza bruta

def test_el_login_se_bloquea_tras_varios_fallos(client):
    for _ in range(settings.LOGIN_INTENTOS):
        assert client.post("/api/v1/auth/login-json", json=CREDENCIALES_MALAS).status_code == 401

    r = client.post("/api/v1/auth/login-json", json=CREDENCIALES_MALAS)
    assert r.status_code == 429
    assert "Demasiados intentos" in r.json()["detalle"]


def test_el_bloqueo_tambien_tapa_la_contrasena_correcta(client):
    """Si no, bastaría con seguir probando hasta acertar."""
    for _ in range(settings.LOGIN_INTENTOS):
        client.post("/api/v1/auth/login-json", json=CREDENCIALES_MALAS)

    r = client.post(
        "/api/v1/auth/login-json", json={"email": "admin@test.com", "password": "admin123"}
    )
    assert r.status_code == 429


def test_un_login_correcto_no_gasta_intentos(client):
    for _ in range(5):
        r = client.post(
            "/api/v1/auth/login-json", json={"email": "admin@test.com", "password": "admin123"}
        )
        assert r.status_code == 200


# ============================================== tokens

def test_token_firmado_con_otra_llave_no_sirve(client):
    ajeno = jwt.encode(
        {"sub": "1", "rol": "ADMIN", "exp": 9999999999}, "llave-del-atacante", algorithm="HS256"
    )
    r = client.get("/api/v1/auth/yo", headers={"Authorization": f"Bearer {ajeno}"})
    assert r.status_code == 401


def test_token_sin_firma_no_sirve(client):
    """El clásico 'alg: none'."""
    sin_firma = jwt.encode({"sub": "1", "rol": "ADMIN"}, key="", algorithm="none")
    r = client.get("/api/v1/auth/yo", headers={"Authorization": f"Bearer {sin_firma}"})
    assert r.status_code == 401


def test_token_con_sub_manipulado_da_401_no_500(client):
    raro = jwt.encode(
        {"sub": "'; DROP TABLE usuarios; --", "rol": "ADMIN", "exp": 9999999999},
        settings.SECRET_KEY, algorithm="HS256",
    )
    r = client.get("/api/v1/auth/yo", headers={"Authorization": f"Bearer {raro}"})
    assert r.status_code == 401


def test_token_expirado_se_rechaza(client):
    vencido = jwt.encode(
        {"sub": "1", "rol": "ADMIN", "exp": 1000000000}, settings.SECRET_KEY, algorithm="HS256"
    )
    r = client.get("/api/v1/auth/yo", headers={"Authorization": f"Bearer {vencido}"})
    assert r.status_code == 401


def test_el_rol_del_token_no_manda_sobre_la_base(client):
    """Un cliente que se fabrica un token diciendo ADMIN sigue siendo cliente."""
    token = jwt.encode(
        {"sub": "3", "rol": "ADMIN", "exp": 9999999999}, settings.SECRET_KEY, algorithm="HS256"
    )
    cabeceras = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/v1/auth/yo", headers=cabeceras).json()["rol"] == "CLIENTE"
    r = client.post(
        "/api/v1/productos",
        json={"nombre": "Pirata", "precio": "10.00", "categoria_id": 1},
        headers=cabeceras,
    )
    assert r.status_code == 403


# ============================================== escalada de privilegios

def test_nadie_se_registra_como_admin(client):
    r = client.post(
        "/api/v1/auth/registro",
        json={"nombre": "Listo", "email": "listo@test.com", "password": "clave12345",
              "rol": "ADMIN"},
    )
    assert r.status_code == 201
    assert r.json()["rol"] == "CLIENTE"


def test_contrasena_corta_rechazada(client):
    r = client.post(
        "/api/v1/auth/registro",
        json={"nombre": "Corto", "email": "corto@test.com", "password": "1234567"},
    )
    assert r.status_code == 422


# ============================================== fuga de datos

def test_las_ordenes_no_exponen_correos(client, mesero):
    orden = client.post(
        "/api/v1/ordenes", json={"items": [{"producto_id": 1, "cantidad": 1}]}, headers=mesero
    ).json()
    assert "email" not in orden["mesero"]
    assert set(orden["mesero"]) == {"id", "nombre", "rol"}


def test_la_respuesta_nunca_trae_el_hash(client, admin):
    perfil = client.get("/api/v1/auth/yo", headers=admin).json()
    assert "hashed_password" not in perfil and "password" not in perfil


def test_el_login_no_revela_que_correos_existen(client):
    inexistente = client.post(
        "/api/v1/auth/login-json", json={"email": "nadie@test.com", "password": "loQueSea123"}
    )
    existente = client.post("/api/v1/auth/login-json", json=CREDENCIALES_MALAS)
    assert inexistente.status_code == existente.status_code == 401
    assert inexistente.json()["detalle"] == existente.json()["detalle"]


# ============================================== cabeceras

@pytest.mark.parametrize(
    "cabecera,esperado",
    [
        ("X-Content-Type-Options", "nosniff"),
        ("X-Frame-Options", "DENY"),
        ("Referrer-Policy", "same-origin"),
        ("Cross-Origin-Opener-Policy", "same-origin"),
    ],
)
def test_cabeceras_de_seguridad(client, cabecera, esperado):
    assert client.get("/api/v1/salud").headers[cabecera] == esperado


def test_csp_bloquea_scripts_externos_y_iframes(client):
    csp = client.get("/api/v1/salud").headers["Content-Security-Policy"]
    assert "script-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "object-src 'none'" in csp


def test_la_app_no_anade_cabecera_server(client):
    """uvicorn añade la suya en la capa de protocolo: se quita con --no-server-header."""
    assert "server" not in {k.lower() for k in client.get("/api/v1/salud").headers}


# ============================================== cuentas de demostración

def test_salud_declara_si_es_entorno_de_demo(client):
    """El front usa esta bandera para decidir si ofrece las cuentas de prueba."""
    cuerpo = client.get("/api/v1/salud").json()
    assert cuerpo["demo"] is not settings.es_produccion


def test_en_produccion_no_se_ofrecen_cuentas_de_prueba(client, monkeypatch):
    monkeypatch.setattr(settings, "ENTORNO", "produccion")
    assert client.get("/api/v1/salud").json()["demo"] is False
