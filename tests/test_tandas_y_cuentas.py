"""Pruebas de las tres funciones nuevas: tandas, cuentas divididas y propinas."""
PASTOR, AGOTADO, REFRESCO = 1, 2, 3


def nueva_orden(client, mesero, items=None, tipo="LOCAL"):
    r = client.post(
        "/api/v1/ordenes",
        json={"tipo": tipo, "mesa": 4, "items": items or [{"producto_id": PASTOR, "cantidad": 1}]},
        headers=mesero,
    )
    assert r.status_code == 201, r.text
    return r.json()


def avanzar(client, mesero, orden_id, estado):
    return client.patch(
        f"/api/v1/ordenes/{orden_id}/estado", json={"estado": estado}, headers=mesero
    )


# ============================================================ tandas


def test_local_admite_platillos_con_la_cocina_trabajando(client, mesero):
    orden = nueva_orden(client, mesero)
    avanzar(client, mesero, orden["id"], "EN_PREPARACION")

    r = client.post(
        f"/api/v1/ordenes/{orden['id']}/items",
        json={"producto_id": REFRESCO, "cantidad": 2},
        headers=mesero,
    )
    assert r.status_code == 200, r.text
    actualizada = r.json()

    # El platillo nuevo abre la tanda 2 y entra sin cocinar.
    nuevo = next(i for i in actualizada["items"] if i["producto_id"] == REFRESCO)
    viejo = next(i for i in actualizada["items"] if i["producto_id"] == PASTOR)
    assert nuevo["tanda"] == 2 and nuevo["estado"] == "PENDIENTE"
    assert viejo["tanda"] == 1 and viejo["estado"] == "EN_PREPARACION"

    # La orden retrocede porque vuelve a haber algo sin preparar...
    assert actualizada["estado"] == "PENDIENTE"
    # ...pero todo se sigue cobrando junto en la misma mesa.
    assert actualizada["mesa"] == 4
    assert actualizada["total"] == "232.00"  # (100 + 2*50) * 1.16


def test_mientras_siga_pendiente_se_agrega_a_la_misma_tanda(client, mesero):
    orden = nueva_orden(client, mesero)
    r = client.post(
        f"/api/v1/ordenes/{orden['id']}/items",
        json={"producto_id": REFRESCO, "cantidad": 1},
        headers=mesero,
    ).json()
    assert {i["tanda"] for i in r["items"]} == {1}


def test_la_cocina_ve_cada_tanda_por_separado(client, mesero):
    orden = nueva_orden(client, mesero)
    avanzar(client, mesero, orden["id"], "EN_PREPARACION")
    avanzar(client, mesero, orden["id"], "LISTA")
    avanzar(client, mesero, orden["id"], "ENTREGADA")

    # Ya entregada, la mesa pide postre.
    client.post(
        f"/api/v1/ordenes/{orden['id']}/items",
        json={"producto_id": REFRESCO, "cantidad": 1},
        headers=mesero,
    )

    comandas = client.get("/api/v1/ordenes/cocina", headers=mesero).json()
    # Solo aparece la tanda pendiente, no la que ya se sirvio.
    assert len(comandas) == 1
    assert comandas[0]["tanda"] == 2
    assert comandas[0]["mesa"] == 4
    assert [i["producto_id"] for i in comandas[0]["items"]] == [REFRESCO]


def test_una_tanda_avanza_sin_arrastrar_a_la_otra(client, mesero):
    orden = nueva_orden(client, mesero)
    avanzar(client, mesero, orden["id"], "EN_PREPARACION")
    client.post(
        f"/api/v1/ordenes/{orden['id']}/items",
        json={"producto_id": REFRESCO, "cantidad": 1},
        headers=mesero,
    )
    url = f"/api/v1/ordenes/{orden['id']}/tandas/2/estado"

    # No se puede saltar pasos dentro de una tanda.
    assert client.patch(url, json={"estado": "LISTA"}, headers=mesero).status_code == 409

    r = client.patch(url, json={"estado": "EN_PREPARACION"}, headers=mesero).json()
    tandas = {t["numero"]: t["estado"] for t in
              client.get(f"/api/v1/ordenes/{orden['id']}/tandas", headers=mesero).json()}
    assert tandas == {1: "EN_PREPARACION", 2: "EN_PREPARACION"}
    assert r["estado"] == "EN_PREPARACION"


def test_no_se_quita_lo_que_ya_esta_en_cocina(client, mesero):
    orden = nueva_orden(
        client, mesero,
        items=[{"producto_id": PASTOR, "cantidad": 1}, {"producto_id": REFRESCO, "cantidad": 1}],
    )
    avanzar(client, mesero, orden["id"], "EN_PREPARACION")
    item_id = orden["items"][0]["id"]
    r = client.delete(f"/api/v1/ordenes/{orden['id']}/items/{item_id}", headers=mesero)
    assert r.status_code == 409
    assert "ya esta en cocina" in r.json()["detalle"]


# =========================================================== cuentas


def test_dividir_la_mesa_en_dos_cuentas(client, mesero):
    orden = nueva_orden(
        client, mesero,
        items=[
            {"producto_id": PASTOR, "cantidad": 1},                # 100 -> cuenta 1
            {"producto_id": REFRESCO, "cantidad": 2, "cuenta": 2},  # 100 -> cuenta 2
        ],
    )
    cuentas = client.get(f"/api/v1/ordenes/{orden['id']}/cuentas", headers=mesero).json()
    assert [c["numero"] for c in cuentas] == [1, 2]
    assert cuentas[0]["total"] == "116.00"
    assert cuentas[1]["total"] == "116.00"
    # Lo que suman las cuentas es exactamente el total de la orden.
    assert orden["total"] == "232.00"


def test_mover_un_platillo_de_cuenta(client, mesero):
    orden = nueva_orden(
        client, mesero,
        items=[{"producto_id": PASTOR, "cantidad": 1}, {"producto_id": REFRESCO, "cantidad": 1}],
    )
    item_id = next(i["id"] for i in orden["items"] if i["producto_id"] == REFRESCO)

    r = client.patch(
        f"/api/v1/ordenes/{orden['id']}/items/{item_id}/cuenta",
        json={"cuenta": 2}, headers=mesero,
    ).json()
    assert {i["cuenta"] for i in r["items"]} == {1, 2}

    cuentas = client.get(f"/api/v1/ordenes/{orden['id']}/cuentas", headers=mesero).json()
    assert cuentas[0]["total"] == "116.00"
    assert cuentas[1]["total"] == "58.00"


def test_cobrar_una_cuenta_deja_la_otra_pendiente(client, mesero):
    orden = nueva_orden(
        client, mesero,
        items=[
            {"producto_id": PASTOR, "cantidad": 1},
            {"producto_id": REFRESCO, "cantidad": 1, "cuenta": 2},
        ],
    )
    pagos = f"/api/v1/ordenes/{orden['id']}/pagos"

    # Con la mesa dividida hay que decir que cuenta se cobra.
    r = client.post(pagos, json={"metodo": "EFECTIVO", "monto": "50.00"}, headers=mesero)
    assert r.status_code == 409
    assert "indica cuál estás cobrando" in r.json()["detalle"]

    # Una cuenta no puede pagar mas de lo suyo aunque la mesa deba mas.
    r = client.post(
        pagos, json={"metodo": "EFECTIVO", "monto": "100.00", "cuenta": 2}, headers=mesero
    )
    assert r.status_code == 409
    assert "excede el saldo de la cuenta 2" in r.json()["detalle"]

    # Sin monto se cobra el saldo completo de esa cuenta.
    r = client.post(pagos, json={"metodo": "TARJETA", "cuenta": 1}, headers=mesero).json()
    cuentas = {c["numero"]: c for c in
               client.get(f"/api/v1/ordenes/{orden['id']}/cuentas", headers=mesero).json()}
    assert cuentas[1]["pagada"] is True and cuentas[1]["saldo"] == "0.00"
    assert cuentas[2]["pagada"] is False and cuentas[2]["saldo"] == "58.00"
    assert r["pagada"] is False  # la mesa completa todavia debe


def test_no_se_mueve_un_platillo_de_una_cuenta_ya_pagada(client, mesero):
    orden = nueva_orden(
        client, mesero,
        items=[
            {"producto_id": PASTOR, "cantidad": 1},
            {"producto_id": REFRESCO, "cantidad": 1, "cuenta": 2},
        ],
    )
    client.post(
        f"/api/v1/ordenes/{orden['id']}/pagos",
        json={"metodo": "EFECTIVO", "cuenta": 1}, headers=mesero,
    )
    item_id = next(i["id"] for i in orden["items"] if i["cuenta"] == 1)
    r = client.patch(
        f"/api/v1/ordenes/{orden['id']}/items/{item_id}/cuenta",
        json={"cuenta": 2}, headers=mesero,
    )
    assert r.status_code == 409
    assert "ya tiene pagos" in r.json()["detalle"]


def test_factura_de_una_sola_cuenta(client, mesero):
    orden = nueva_orden(
        client, mesero,
        items=[
            {"producto_id": PASTOR, "cantidad": 1},
            {"producto_id": REFRESCO, "cantidad": 1, "cuenta": 2},
        ],
    )
    completa = client.get(f"/api/v1/ordenes/{orden['id']}/factura", headers=mesero).json()
    assert len(completa["lineas"]) == 2
    assert completa["total_cuentas"] == 2 and completa["cuenta"] is None

    parcial = client.get(
        f"/api/v1/ordenes/{orden['id']}/factura?cuenta=2", headers=mesero
    ).json()
    assert [l["descripcion"] for l in parcial["lineas"]] == ["Refresco"]
    assert parcial["cuenta"] == 2 and parcial["total"] == "58.00"


# =========================================================== propinas


def test_propina_por_porcentaje(client, mesero):
    orden = nueva_orden(client, mesero)  # total 116.00
    r = client.post(
        f"/api/v1/ordenes/{orden['id']}/pagos",
        json={"metodo": "TARJETA", "propina_porcentaje": "15"},
        headers=mesero,
    ).json()
    pago = r["pagos"][0]
    assert pago["monto"] == "116.00"
    assert pago["propina"] == "17.40"          # 15% de 116.00
    assert pago["propina_porcentaje"] == "15.00"
    assert r["propina_total"] == "17.40"


def test_propina_por_importe_sigue_funcionando(client, mesero):
    orden = nueva_orden(client, mesero)
    r = client.post(
        f"/api/v1/ordenes/{orden['id']}/pagos",
        json={"metodo": "EFECTIVO", "monto": "116.00", "propina": "25.00"},
        headers=mesero,
    ).json()
    assert r["pagos"][0]["propina"] == "25.00"
    assert r["pagos"][0]["propina_porcentaje"] is None


def test_no_se_puede_mandar_propina_de_las_dos_formas(client, mesero):
    orden = nueva_orden(client, mesero)
    r = client.post(
        f"/api/v1/ordenes/{orden['id']}/pagos",
        json={"metodo": "TARJETA", "propina": "10.00", "propina_porcentaje": "10"},
        headers=mesero,
    )
    assert r.status_code == 422


def test_propina_por_cuenta_se_calcula_sobre_lo_que_paga_cada_quien(client, mesero):
    orden = nueva_orden(
        client, mesero,
        items=[
            {"producto_id": PASTOR, "cantidad": 1},                 # cuenta 1: 116.00
            {"producto_id": REFRESCO, "cantidad": 1, "cuenta": 2},  # cuenta 2:  58.00
        ],
    )
    pagos = f"/api/v1/ordenes/{orden['id']}/pagos"
    client.post(pagos, json={"metodo": "TARJETA", "cuenta": 1, "propina_porcentaje": "10"}, headers=mesero)
    r = client.post(pagos, json={"metodo": "EFECTIVO", "cuenta": 2, "propina_porcentaje": "10"}, headers=mesero).json()

    propinas = {p["cuenta"]: p["propina"] for p in r["pagos"]}
    assert propinas == {1: "11.60", 2: "5.80"}   # 10% de cada cuenta, no del total
    assert r["pagada"] is True


# =========================================================== datos de entrega


def test_un_pedido_para_llevar_exige_a_quien_buscar(client, mesero):
    """En una mesa basta el número; fuera del local hace falta el contacto."""
    r = client.post(
        "/api/v1/ordenes",
        json={"tipo": "PARA_LLEVAR", "items": [{"producto_id": PASTOR, "cantidad": 1}]},
        headers=mesero,
    )
    assert r.status_code == 422
    # Es validación de entrada, así que llega en el formato de FastAPI.
    detalle = r.json()["detail"][0]["msg"]
    assert "nombre" in detalle and "teléfono" in detalle and "método de pago" in detalle


def test_el_domicilio_solo_se_exige_a_domicilio(client, mesero):
    """Quien recoge viene al restaurante: su dirección no aporta nada."""
    contacto = {
        "contacto_nombre": "Ana Ruiz",
        "contacto_telefono": "9991234567",
        "metodo_pago_preferido": "EFECTIVO",
        "items": [{"producto_id": PASTOR, "cantidad": 1}],
    }
    assert client.post(
        "/api/v1/ordenes", json={"tipo": "PARA_LLEVAR", **contacto}, headers=mesero
    ).status_code == 201

    r = client.post("/api/v1/ordenes", json={"tipo": "DOMICILIO", **contacto}, headers=mesero)
    assert r.status_code == 422
    assert "domicilio" in r.json()["detail"][0]["msg"]


def test_se_guardan_y_se_devuelven_los_datos_de_entrega(client, mesero):
    orden = client.post(
        "/api/v1/ordenes",
        json={
            "tipo": "DOMICILIO",
            "contacto_nombre": "Ana Ruiz",
            "contacto_telefono": "9991234567",
            "contacto_direccion": "Calle 60 #123, Centro",
            "metodo_pago_preferido": "TARJETA",
            "items": [{"producto_id": PASTOR, "cantidad": 1}],
        },
        headers=mesero,
    ).json()

    assert orden["es_para_llevar"] is True
    assert orden["contacto_nombre"] == "Ana Ruiz"
    assert orden["contacto_direccion"] == "Calle 60 #123, Centro"
    assert orden["metodo_pago_preferido"] == "TARJETA"

    # El método es una intención, no un cobro: la orden sigue debiendo.
    assert orden["pagada"] is False
    assert orden["total_pagado"] == "0.00"
    assert orden["pagos"] == []


def test_comer_aqui_no_pide_nada_de_eso(client, mesero):
    orden = client.post(
        "/api/v1/ordenes",
        json={"tipo": "LOCAL", "mesa": 3, "items": [{"producto_id": PASTOR, "cantidad": 1}]},
        headers=mesero,
    ).json()
    assert orden["es_para_llevar"] is False
    assert orden["contacto_nombre"] is None and orden["metodo_pago_preferido"] is None


def test_el_cliente_tambien_debe_dar_sus_datos(client, cliente):
    r = client.post(
        "/api/v1/ordenes",
        json={"tipo": "DOMICILIO", "items": [{"producto_id": PASTOR, "cantidad": 1}]},
        headers=cliente,
    )
    assert r.status_code == 422
