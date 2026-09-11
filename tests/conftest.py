"""Configuracion de pruebas: cada test corre contra una BD SQLite temporal."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.core.limitador import limitador_cuenta, limitador_login, limitador_registro
from app.core.security import hashear_password
from app.main import app
from app.models import Categoria, Producto, RolUsuario, Usuario


@pytest.fixture(autouse=True)
def _limitadores_limpios():
    """Los limitadores son globales: sin esto una prueba dejaría bloqueada a la siguiente."""
    limitador_login.reiniciar()
    limitador_cuenta.reiniciar()
    limitador_registro.reiniciar()
    yield


@pytest.fixture
def client(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path/'test.db'}", connect_args={"check_same_thread": False}
    )
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    db = Session()
    for nombre, email, pwd, rol in [
        ("Admin", "admin@test.com", "admin123", RolUsuario.ADMIN),
        ("Mesero", "mesero@test.com", "mesero123", RolUsuario.MESERO),
        ("Cliente", "cliente@test.com", "cliente123", RolUsuario.CLIENTE),
    ]:
        db.add(Usuario(nombre=nombre, email=email, hashed_password=hashear_password(pwd), rol=rol))
    categoria = Categoria(nombre="Tacos", descripcion="De todo")
    categoria.productos.append(Producto(nombre="Pastor", precio="100.00"))
    categoria.productos.append(Producto(nombre="Agotado", precio="50.00", disponible=False))
    categoria.productos.append(Producto(nombre="Refresco", precio="50.00"))
    db.add(categoria)
    db.commit()
    db.close()


    def override():
        sesion = Session()
        try:
            yield sesion
        finally:
            sesion.close()

    app.dependency_overrides[get_db] = override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def token(client, email, password):
    r = client.post("/api/v1/auth/login-json", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def admin(client):
    return token(client, "admin@test.com", "admin123")


@pytest.fixture
def mesero(client):
    return token(client, "mesero@test.com", "mesero123")


@pytest.fixture
def cliente(client):
    return token(client, "cliente@test.com", "cliente123")
