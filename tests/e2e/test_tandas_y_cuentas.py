"""Pedir más en una mesa abierta, y dividir la cuenta."""
from playwright.sync_api import Page, expect

PASTOR, REFRESCO = 4, 9   # ids del menú de ejemplo


def abrir(page: Page, servidor, orden_id):
    page.goto(f"{servidor}/app/#/ordenes/{orden_id}")


def test_una_mesa_en_marcha_admite_mas_platillos(entrar, api, servidor):
    mesero = api("mesero")
    orden = mesero.post("/ordenes", json={
        "tipo": "LOCAL", "mesa": 31, "items": [{"producto_id": PASTOR, "cantidad": 1}],
    }).json()
    mesero.patch(f"/ordenes/{orden['id']}/estado", json={"estado": "EN_PREPARACION"})

    page = entrar("mesero")
    abrir(page, servidor, orden["id"])

    # Con la cocina trabajando, la mesa sigue abierta.
    expect(page.locator(".banner")).to_contain_text("Mesa abierta")
    page.locator('.banner a[href*="menu?orden="]').click()

    expect(page.locator(".banner")).to_contain_text(orden["numero"])
    page.locator(".producto .agregar:not([disabled])").nth(3).click()
    page.get_by_role("button", name=f"Agregar a {orden['numero']}").click()

    # Lo nuevo entra en una tanda aparte y la orden retrocede.
    expect(page.locator(".tanda")).to_have_count(2)
    expect(page.locator(".orden-cabecera .insignia").first).to_have_text("Pendiente")
    estados = page.locator(".item-linea .insignia")
    expect(estados.nth(0)).to_have_text("En preparación")
    expect(estados.nth(1)).to_have_text("Por preparar")


def test_la_cocina_ve_cada_tanda_como_comanda_aparte(entrar, api, servidor):
    mesero = api("mesero")
    orden = mesero.post("/ordenes", json={
        "tipo": "LOCAL", "mesa": 32, "items": [{"producto_id": PASTOR, "cantidad": 1}],
    }).json()
    for estado in ("EN_PREPARACION", "LISTA", "ENTREGADA"):
        mesero.patch(f"/ordenes/{orden['id']}/estado", json={"estado": estado})
    # Ya entregada, la mesa pide postre.
    mesero.post(f"/ordenes/{orden['id']}/items",
                json={"producto_id": REFRESCO, "cantidad": 1})

    page = entrar("mesero")
    page.goto(f"{servidor}/app/#/cocina")

    comanda = page.locator(".comanda", has_text=orden["numero"])
    expect(comanda).to_have_count(1)          # solo la tanda pendiente
    expect(comanda).to_contain_text("Tanda 2")


def test_dividir_la_mesa_y_cobrar_solo_una_cuenta(entrar, api, servidor):
    orden = api("mesero").post("/ordenes", json={
        "tipo": "LOCAL", "mesa": 33,
        "items": [{"producto_id": PASTOR, "cantidad": 1},
                  {"producto_id": REFRESCO, "cantidad": 1}],
    }).json()

    page = entrar("mesero")
    abrir(page, servidor, orden["id"])

    page.locator("[data-cuenta-item]").nth(1).select_option("2")
    expect(page.locator(".aviso")).to_contain_text("cuenta 2")
    expect(page.locator(".cuenta")).to_have_count(2)

    page.locator('[data-cobrar-cuenta="1"]').click()
    modal = page.locator(".modal")
    expect(modal.locator("h2")).to_have_text("Cobrar cuenta 1")

    # La propina por porcentaje se calcula sobre lo que paga esa cuenta.
    monto = float(modal.locator("#monto").input_value())
    modal.locator('[data-pct="15"]').click()
    expect(modal.locator("#propina")).to_have_value(f"{monto * 0.15:.2f}")
    expect(modal.locator("#ayuda-propina")).to_contain_text("15%")

    modal.get_by_role("button", name="Registrar pago").click()

    expect(page.locator(".cuenta--pagada")).to_have_count(1)
    # La mesa completa sigue debiendo.
    expect(page.locator(".orden-cabecera .insignia", has_text="Saldo")).to_be_visible()


def test_el_ticket_de_una_cuenta_solo_trae_lo_suyo(entrar, api, servidor):
    mesero = api("mesero")
    orden = mesero.post("/ordenes", json={
        "tipo": "LOCAL", "mesa": 34,
        "items": [{"producto_id": PASTOR, "cantidad": 1},
                  {"producto_id": REFRESCO, "cantidad": 1, "cuenta": 2}],
    }).json()

    page = entrar("mesero")
    abrir(page, servidor, orden["id"])
    page.locator('[data-ticket-cuenta="2"]').click()

    ticket = page.locator(".ticket")
    expect(ticket).to_contain_text("Cuenta 2 de 2")
    expect(ticket.locator(".ticket__linea")).to_have_count(1)
