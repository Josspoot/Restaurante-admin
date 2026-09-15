"""Terminar la mesa, y los avisos que recibe el mesero."""
from playwright.sync_api import expect

PASTOR = 4


def test_no_se_cierra_hasta_entregar_y_cobrar(entrar, api, servidor):
    mesero = api("mesero")
    orden = mesero.post("/ordenes", json={
        "tipo": "LOCAL", "mesa": 41, "items": [{"producto_id": PASTOR, "cantidad": 1}],
    }).json()

    page = entrar("mesero")
    page.goto(f"{servidor}/app/#/ordenes/{orden['id']}")

    expect(page.locator(".requisito")).to_have_count(2)
    expect(page.locator("#cerrar-mesa")).to_be_disabled()

    # Entregada pero sin cobrar: sigue sin poder cerrarse.
    for estado in ("EN_PREPARACION", "LISTA", "ENTREGADA"):
        mesero.patch(f"/ordenes/{orden['id']}/estado", json={"estado": estado})
    page.reload()
    expect(page.locator(".requisito--ok")).to_have_count(1)
    expect(page.locator(".requisito--falta")).to_contain_text("por cobrar")
    expect(page.locator("#cerrar-mesa")).to_be_disabled()

    mesero.post(f"/ordenes/{orden['id']}/pagos", json={"metodo": "EFECTIVO"})
    page.reload()
    expect(page.locator(".requisito--ok")).to_have_count(2)
    expect(page.locator("#cerrar-mesa")).to_be_enabled()


def test_al_cerrar_la_mesa_deja_de_admitir_cambios(entrar, api, servidor):
    mesero = api("mesero")
    orden = mesero.post("/ordenes", json={
        "tipo": "LOCAL", "mesa": 42, "items": [{"producto_id": PASTOR, "cantidad": 1}],
    }).json()
    for estado in ("EN_PREPARACION", "LISTA", "ENTREGADA"):
        mesero.patch(f"/ordenes/{orden['id']}/estado", json={"estado": estado})
    mesero.post(f"/ordenes/{orden['id']}/pagos", json={"metodo": "EFECTIVO"})

    page = entrar("mesero")
    page.goto(f"{servidor}/app/#/ordenes/{orden['id']}")
    page.locator("#cerrar-mesa").click()
    page.locator("[data-si]").click()

    expect(page.locator(".cierre--hecho")).to_contain_text("Mesa cerrada")
    expect(page.locator(".cierre__detalle").first).to_contain_text("Ana Mesera")
    # Solo queda ver el ticket.
    expect(page.locator("[data-estado], [data-cuenta-item], #cobrar, #cerrar-mesa")).to_have_count(0)
    expect(page.locator("#reabrir")).to_have_count(0)   # un mesero no reabre


def test_un_admin_si_puede_reabrir(entrar, api, servidor):
    mesero = api("mesero")
    orden = mesero.post("/ordenes", json={
        "tipo": "LOCAL", "mesa": 43, "items": [{"producto_id": PASTOR, "cantidad": 1}],
    }).json()
    for estado in ("EN_PREPARACION", "LISTA", "ENTREGADA"):
        mesero.patch(f"/ordenes/{orden['id']}/estado", json={"estado": estado})
    mesero.post(f"/ordenes/{orden['id']}/pagos", json={"metodo": "EFECTIVO"})
    mesero.post(f"/ordenes/{orden['id']}/cerrar")

    page = entrar("admin")
    page.goto(f"{servidor}/app/#/ordenes/{orden['id']}")
    expect(page.locator("#reabrir")).to_be_visible()


def test_la_lista_marca_las_mesas_cerradas(entrar, api, servidor):
    mesero = api("mesero")
    orden = mesero.post("/ordenes", json={
        "tipo": "LOCAL", "mesa": 44, "items": [{"producto_id": PASTOR, "cantidad": 1}],
    }).json()
    for estado in ("EN_PREPARACION", "LISTA", "ENTREGADA"):
        mesero.patch(f"/ordenes/{orden['id']}/estado", json={"estado": estado})
    mesero.post(f"/ordenes/{orden['id']}/pagos", json={"metodo": "EFECTIVO"})
    mesero.post(f"/ordenes/{orden['id']}/cerrar")

    page = entrar("mesero")
    page.goto(f"{servidor}/app/#/ordenes")
    fila = page.locator("tr", has_text=orden["numero"])
    expect(fila.locator(".insignia--cerrada")).to_be_visible()
    expect(fila.locator(".candado svg")).to_be_visible()


def test_al_mesero_le_avisan_lo_que_esta_listo(entrar, api, servidor):
    mesero = api("mesero")
    orden = mesero.post("/ordenes", json={
        "tipo": "LOCAL", "mesa": 45, "items": [{"producto_id": PASTOR, "cantidad": 1}],
    }).json()
    for estado in ("EN_PREPARACION", "LISTA"):
        mesero.patch(f"/ordenes/{orden['id']}/estado", json={"estado": estado})

    page = entrar("mesero")   # el sondeo corre al cargar
    expect(page.locator(".campana__punto")).to_be_visible()

    page.locator("#campana").click()
    fila = page.locator(".aviso-fila", has_text=orden["numero"])
    expect(fila).to_be_visible()

    fila.get_by_role("button", name="Marcar entregada").click()
    expect(page.locator(".aviso-fila", has_text=orden["numero"])).to_have_count(0)
