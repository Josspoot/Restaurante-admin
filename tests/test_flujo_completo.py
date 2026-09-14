"""Prueba de extremo a extremo: del menu al ticket pagado."""
from tests.conftest import token


def test_salud(client):
    assert client.get("/api/v1/salud").json()["estado"] == "ok"


def test_menu_es_publico(client):
    r = client.get("/api/v1/productos")
    assert r.status_code == 200
    assert len(r.json()) == 3


def test_crear_producto_exige_admin(client, cliente):
    payload = {"nombre": "Pirata", "precio": "90.00", "categoria_id": 1}
    assert client.post("/api/v1/productos", json=payload).status_code == 401
    assert client.post("/api/v1/productos", json=payload, headers=cliente).status_code == 403


def test_registro_y_login(client):
    r = client.post(
        "/api/v1/auth/registro",
        json={"nombre": "Nuevo", "email": "nuevo@test.com", "password": "secreto123"},
    )
    assert r.status_code == 201
    assert r.json()["rol"] == "CLIENTE"  # nadie se autoasigna ADMIN
    assert client.post(
        "/api/v1/auth/registro",
        json={"nombre": "Otro", "email": "nuevo@test.com", "password": "secreto123"},
    ).status_code == 409
    headers = token(client, "nuevo@test.com", "secreto123")
    assert client.get("/api/v1/auth/yo", headers=headers).json()["email"] == "nuevo@test.com"


def test_totales_con_iva(client, mesero):
    r = client.post(
        "/api/v1/ordenes",
        json={"tipo": "LOCAL", "mesa": 5, "items": [{"producto_id": 1, "cantidad": 3}]},
        headers=mesero,
    )
    assert r.status_code == 201, r.text
    orden = r.json()
    assert orden["subtotal"] == "300.00"
    assert orden["impuestos"] == "48.00"   # 300 * 0.16
    assert orden["total"] == "348.00"
    assert orden["estado"] == "PENDIENTE"
    assert orden["numero"].startswith("ORD-")


def test_no_se_ordena_producto_agotado(client, mesero):
    r = client.post(
        "/api/v1/ordenes",
        json={"items": [{"producto_id": 2, "cantidad": 1}]},
        headers=mesero,
    )
    assert r.status_code == 409
    assert "no está disponible" in r.json()["detalle"]


def test_transiciones_de_estado(client, mesero):
    orden = client.post(
        "/api/v1/ordenes", json={"items": [{"producto_id": 1, "cantidad": 1}]}, headers=mesero
    ).json()
    url = f"/api/v1/ordenes/{orden['id']}/estado"

    # No se puede saltar de PENDIENTE directo a ENTREGADA
    assert client.patch(url, json={"estado": "ENTREGADA"}, headers=mesero).status_code == 409

    for estado in ["EN_PREPARACION", "LISTA", "ENTREGADA"]:
        assert client.patch(url, json={"estado": estado}, headers=mesero).status_code == 200

    # Una orden entregada es terminal
    assert client.patch(url, json={"estado": "CANCELADA"}, headers=mesero).status_code == 409


def test_para_llevar_se_cierra_al_entrar_a_cocina(client, mesero):
    """Para llevar y domicilio se congelan en cuanto la comanda sale a cocina."""
    orden = client.post(
        "/api/v1/ordenes",
        json={
            "tipo": "PARA_LLEVAR",
            "contacto_nombre": "Ana",
            "contacto_telefono": "9991234567",
            "metodo_pago_preferido": "EFECTIVO",
            "items": [{"producto_id": 1, "cantidad": 1}],
        },
        headers=mesero,
    ).json()
    assert orden["ampliable"] is True  # mientras siga pendiente, si

    client.patch(
        f"/api/v1/ordenes/{orden['id']}/estado", json={"estado": "EN_PREPARACION"}, headers=mesero
    )
    r = client.post(
        f"/api/v1/ordenes/{orden['id']}/items",
        json={"producto_id": 1, "cantidad": 1},
        headers=mesero,
    )
    assert r.status_code == 409
    assert "solo admite cambios mientras está pendiente" in r.json()["detalle"]


def test_cliente_no_ve_ordenes_ajenas(client, mesero, cliente):
    orden = client.post(
        "/api/v1/ordenes", json={"items": [{"producto_id": 1, "cantidad": 1}]}, headers=mesero
    ).json()
    assert client.get(f"/api/v1/ordenes/{orden['id']}", headers=cliente).status_code == 403
    assert client.get("/api/v1/ordenes", headers=cliente).json() == []


def test_pago_parcial_y_factura(client, mesero):
    orden = client.post(
        "/api/v1/ordenes",
        json={"mesa": 3, "items": [{"producto_id": 1, "cantidad": 2}]},
        headers=mesero,
    ).json()
    assert orden["total"] == "232.00"
    pagos_url = f"/api/v1/ordenes/{orden['id']}/pagos"

    # Cobrar de mas se rechaza
    assert client.post(
        pagos_url, json={"metodo": "EFECTIVO", "monto": "500.00"}, headers=mesero
    ).status_code == 409

    r = client.post(pagos_url, json={"metodo": "EFECTIVO", "monto": "100.00"}, headers=mesero)
    assert r.json()["saldo"] == "132.00"
    assert r.json()["pagada"] is False

    r = client.post(
        pagos_url,
        json={"metodo": "TARJETA", "monto": "132.00", "propina": "30.00", "referencia": "AUTH-99"},
        headers=mesero,
    )
    assert r.json()["pagada"] is True

    factura = client.get(f"/api/v1/ordenes/{orden['id']}/factura", headers=mesero).json()
    assert factura["saldo"] == "0.00"
    assert factura["propina_total"] == "30.00"
    assert factura["lineas"][0]["descripcion"] == "Pastor"
    assert len(factura["pagos"]) == 2


def test_no_se_cancela_orden_con_pagos(client, mesero):
    orden = client.post(
        "/api/v1/ordenes", json={"items": [{"producto_id": 1, "cantidad": 1}]}, headers=mesero
    ).json()
    client.post(
        f"/api/v1/ordenes/{orden['id']}/pagos",
        json={"metodo": "EFECTIVO", "monto": "10.00"},
        headers=mesero,
    )
    r = client.post(f"/api/v1/ordenes/{orden['id']}/cancelar", headers=mesero)
    assert r.status_code == 409
    assert "reembolsarlos" in r.json()["detalle"]


def test_agregar_item_acumula_cantidad(client, mesero):
    orden = client.post(
        "/api/v1/ordenes", json={"items": [{"producto_id": 1, "cantidad": 1}]}, headers=mesero
    ).json()
    r = client.post(
        f"/api/v1/ordenes/{orden['id']}/items",
        json={"producto_id": 1, "cantidad": 2},
        headers=mesero,
    ).json()
    assert len(r["items"]) == 1
    assert r["items"][0]["cantidad"] == 3
    assert r["total"] == "348.00"


def test_no_se_vacia_la_orden(client, mesero):
    orden = client.post(
        "/api/v1/ordenes", json={"items": [{"producto_id": 1, "cantidad": 1}]}, headers=mesero
    ).json()
    item_id = orden["items"][0]["id"]
    r = client.delete(f"/api/v1/ordenes/{orden['id']}/items/{item_id}", headers=mesero)
    assert r.status_code == 409
