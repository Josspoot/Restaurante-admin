"""Cierre de mesa, filtros de cobro y avisos al mesero."""
PASTOR, AGOTADO, REFRESCO = 1, 2, 3


def nueva_orden(client, headers, items=None, tipo="LOCAL", mesa=4):
    r = client.post(
        "/api/v1/ordenes",
        json={"tipo": tipo, "mesa": mesa, "items": items or [{"producto_id": PASTOR, "cantidad": 1}]},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


def entregar(client, mesero, orden_id):
    for estado in ["EN_PREPARACION", "LISTA", "ENTREGADA"]:
        r = client.patch(
            f"/api/v1/ordenes/{orden_id}/estado", json={"estado": estado}, headers=mesero
        )
        assert r.status_code == 200, r.text
    return r.json()


def cobrar_todo(client, mesero, orden_id):
    return client.post(
        f"/api/v1/ordenes/{orden_id}/pagos", json={"metodo": "EFECTIVO"}, headers=mesero
    ).json()


# ==================================================== cerrar la mesa


def test_no_se_cierra_sin_entregar_ni_cobrar(client, mesero):
    orden = nueva_orden(client, mesero)
    assert orden["puede_cerrarse"] is False
    assert orden["pendientes_para_cerrar"] == [
        "Faltan platillos por entregar",
        "Faltan $116.00 por cobrar",
    ]

    r = client.post(f"/api/v1/ordenes/{orden['id']}/cerrar", headers=mesero)
    assert r.status_code == 409
    assert "todavía no se puede cerrar" in r.json()["detalle"].lower()


def test_entregada_pero_sin_pagar_no_se_cierra(client, mesero):
    """El caso que importa: la comida ya se sirvió pero la cuenta sigue abierta."""
    orden = nueva_orden(client, mesero)
    entregada = entregar(client, mesero, orden["id"])

    assert entregada["estado"] == "ENTREGADA"
    assert entregada["pagada"] is False
    assert entregada["pendientes_para_cerrar"] == ["Faltan $116.00 por cobrar"]

    r = client.post(f"/api/v1/ordenes/{orden['id']}/cerrar", headers=mesero)
    assert r.status_code == 409


def test_cerrar_cuando_ya_no_falta_nada(client, mesero):
    orden = nueva_orden(client, mesero)
    entregar(client, mesero, orden["id"])
    cobrar_todo(client, mesero, orden["id"])

    r = client.post(f"/api/v1/ordenes/{orden['id']}/cerrar", headers=mesero)
    assert r.status_code == 200, r.text
    cerrada = r.json()
    assert cerrada["cerrada"] is True
    assert cerrada["cerrada_en"] is not None
    assert cerrada["cerrada_por"]["nombre"] == "Mesero"
    assert cerrada["pendientes_para_cerrar"] == []
    assert cerrada["ampliable"] is False

    # Cerrar dos veces no tiene sentido.
    assert client.post(f"/api/v1/ordenes/{orden['id']}/cerrar", headers=mesero).status_code == 409


def test_una_mesa_cerrada_ya_no_se_toca(client, mesero):
    orden = nueva_orden(client, mesero)
    entregar(client, mesero, orden["id"])
    cobrar_todo(client, mesero, orden["id"])
    client.post(f"/api/v1/ordenes/{orden['id']}/cerrar", headers=mesero)

    agregar = client.post(
        f"/api/v1/ordenes/{orden['id']}/items",
        json={"producto_id": REFRESCO, "cantidad": 1}, headers=mesero,
    )
    assert agregar.status_code == 409
    assert "está cerrada" in agregar.json()["detalle"]

    cobro = client.post(
        f"/api/v1/ordenes/{orden['id']}/pagos", json={"metodo": "EFECTIVO", "monto": "1.00"},
        headers=mesero,
    )
    assert cobro.status_code == 409


def test_solo_admin_reabre_una_mesa(client, mesero, admin):
    orden = nueva_orden(client, mesero)
    entregar(client, mesero, orden["id"])
    cobrar_todo(client, mesero, orden["id"])
    client.post(f"/api/v1/ordenes/{orden['id']}/cerrar", headers=mesero)

    assert client.post(f"/api/v1/ordenes/{orden['id']}/reabrir", headers=mesero).status_code == 403

    r = client.post(f"/api/v1/ordenes/{orden['id']}/reabrir", headers=admin)
    assert r.status_code == 200
    assert r.json()["cerrada"] is False
    assert r.json()["ampliable"] is True


def test_no_se_cierra_una_orden_cancelada(client, mesero):
    orden = nueva_orden(client, mesero)
    client.post(f"/api/v1/ordenes/{orden['id']}/cancelar", headers=mesero)
    r = client.post(f"/api/v1/ordenes/{orden['id']}/cerrar", headers=mesero)
    assert r.status_code == 409
    assert "cancelada" in r.json()["detalle"].lower()


# ==================================================== filtros de cobro


def test_filtrar_pagadas_y_por_cobrar(client, mesero):
    sin_pagar = nueva_orden(client, mesero, mesa=1)
    entregar(client, mesero, sin_pagar["id"])          # entregada pero sin cobrar

    pagada = nueva_orden(client, mesero, mesa=2)
    cobrar_todo(client, mesero, pagada["id"])

    por_cobrar = client.get("/api/v1/ordenes?pagada=false", headers=mesero).json()
    saldadas = client.get("/api/v1/ordenes?pagada=true", headers=mesero).json()

    assert [o["id"] for o in por_cobrar] == [sin_pagar["id"]]
    assert [o["id"] for o in saldadas] == [pagada["id"]]
    # El estado de cocina y el de cobro son independientes.
    assert por_cobrar[0]["estado"] == "ENTREGADA" and por_cobrar[0]["pagada"] is False


def test_filtrar_mesas_cerradas(client, mesero):
    abierta = nueva_orden(client, mesero, mesa=1)
    cerrada = nueva_orden(client, mesero, mesa=2)
    entregar(client, mesero, cerrada["id"])
    cobrar_todo(client, mesero, cerrada["id"])
    client.post(f"/api/v1/ordenes/{cerrada['id']}/cerrar", headers=mesero)

    assert [o["id"] for o in client.get("/api/v1/ordenes?cerrada=true", headers=mesero).json()] == [cerrada["id"]]
    assert [o["id"] for o in client.get("/api/v1/ordenes?cerrada=false", headers=mesero).json()] == [abierta["id"]]


# ==================================================== avisos al mesero


def test_el_mesero_solo_recibe_avisos_de_sus_ordenes(client, mesero, admin):
    suya = nueva_orden(client, mesero, mesa=1)
    ajena = nueva_orden(client, admin, mesa=2)

    for orden in (suya, ajena):
        for estado in ["EN_PREPARACION", "LISTA"]:
            client.patch(
                f"/api/v1/ordenes/{orden['id']}/estado", json={"estado": estado}, headers=admin
            )

    avisos = client.get("/api/v1/ordenes/avisos", headers=mesero).json()
    assert [a["orden_id"] for a in avisos] == [suya["id"]]
    assert avisos[0]["estado"] == "LISTA" and avisos[0]["mesa"] == 1

    # El admin ve todo lo que esta listo.
    assert len(client.get("/api/v1/ordenes/avisos", headers=admin).json()) == 2


def test_el_aviso_desaparece_al_entregar(client, mesero):
    orden = nueva_orden(client, mesero)
    for estado in ["EN_PREPARACION", "LISTA"]:
        client.patch(f"/api/v1/ordenes/{orden['id']}/estado", json={"estado": estado}, headers=mesero)
    assert len(client.get("/api/v1/ordenes/avisos", headers=mesero).json()) == 1

    client.patch(f"/api/v1/ordenes/{orden['id']}/estado", json={"estado": "ENTREGADA"}, headers=mesero)
    assert client.get("/api/v1/ordenes/avisos", headers=mesero).json() == []


def test_el_aviso_es_por_tanda(client, mesero):
    """Si la segunda ronda esta lista, avisa aunque la orden vaya atrasada."""
    orden = nueva_orden(client, mesero)
    entregar(client, mesero, orden["id"])
    client.post(
        f"/api/v1/ordenes/{orden['id']}/items",
        json={"producto_id": REFRESCO, "cantidad": 1}, headers=mesero,
    )
    for estado in ["EN_PREPARACION", "LISTA"]:
        client.patch(f"/api/v1/ordenes/{orden['id']}/tandas/2/estado", json={"estado": estado}, headers=mesero)

    avisos = client.get("/api/v1/ordenes/avisos", headers=mesero).json()
    assert len(avisos) == 1
    assert avisos[0]["tanda"] == 2
    assert [i["nombre_producto"] for i in avisos[0]["items"]] == ["Refresco"]


def test_un_cliente_no_tiene_avisos(client, cliente):
    assert client.get("/api/v1/ordenes/avisos", headers=cliente).status_code == 403
