"""Recorrido del personal: entrar, armar una comanda, cobrarla y ver el ticket."""
import re

from playwright.sync_api import Page, expect


def test_sin_sesion_se_pide_entrar(page: Page, servidor):
    page.goto(f"{servidor}/app/")
    expect(page.locator(".login__caja")).to_be_visible()
    expect(page.locator("#cabecera")).to_be_hidden()


def test_la_marca_es_un_svg_no_un_emoji(page: Page, servidor):
    """La del encabezado está oculta sin sesión; la visible es la de la portada."""
    page.goto(f"{servidor}/app/")
    expect(page.locator(".login__lema .marca__icono svg")).to_be_visible()


def test_el_mesero_entra_y_aterriza_en_ordenes(entrar):
    page = entrar("mesero")
    expect(page).to_have_url(re.compile(r"#/ordenes$"))
    expect(page.locator(".usuario__rol")).to_have_text("MESERO")
    nav = page.locator("#nav a")
    expect(nav).to_have_text(["Menú", "Órdenes", "Cocina"])


def test_el_mesero_arma_y_envia_una_comanda(entrar):
    page = entrar("mesero")
    page.get_by_role("link", name="Menú").click()

    expect(page.locator(".producto").first).to_be_visible()
    page.locator(".producto .agregar:not([disabled])").first.click()

    # El carrito aparece solo cuando tiene algo.
    expect(page.locator("#carrito .linea")).to_have_count(1)
    expect(page.locator("#nav a[data-conteo]")).to_have_attribute("data-conteo", "1")

    page.locator("#mesa").fill("12")
    page.get_by_role("button", name="Enviar a cocina").click()

    expect(page.locator("h1")).to_contain_text("ORD-")
    expect(page.locator(".paso")).to_have_count(4)
    # Enviarla vacía el carrito.
    expect(page.locator("#nav a[data-conteo]")).to_have_count(0)


def test_el_boton_mas_sube_la_cantidad(entrar):
    page = entrar("mesero")
    page.get_by_role("link", name="Menú").click()
    page.locator(".producto .agregar:not([disabled])").first.click()

    expect(page.locator(".contador span")).to_have_text("1")
    page.locator("[data-mas]").first.click()
    expect(page.locator(".contador span")).to_have_text("2")


def test_el_cobro_salda_la_orden_y_emite_el_ticket(entrar, api):
    orden = api("mesero").post("/ordenes", json={
        "tipo": "LOCAL", "mesa": 21, "items": [{"producto_id": 1, "cantidad": 2}],
    }).json()

    page = entrar("mesero")
    page.goto(f"{page.url.split('#')[0]}#/ordenes/{orden['id']}")

    expect(page.get_by_text(f"Saldo")).to_be_visible()
    page.get_by_role("button", name="Cobrar").click()

    modal = page.locator(".modal")
    expect(modal.locator("#monto")).to_have_value(orden["total"])
    modal.get_by_role("button", name="Registrar pago").click()

    expect(page.locator(".insignia", has_text="Pagada")).to_be_visible()

    page.get_by_role("button", name="Ver ticket").click()
    ticket = page.locator(".ticket")
    expect(ticket).to_contain_text("TOTAL")
    expect(ticket).to_contain_text("PAGADO")


def test_un_mesero_no_entra_a_administrar(entrar):
    page = entrar("mesero")
    page.evaluate("location.hash = '#/admin'")
    # El router lo rebota y avisa.
    expect(page.locator(".aviso")).to_contain_text("permiso")
    expect(page).not_to_have_url(re.compile(r"#/admin$"))


def test_un_admin_si_administra_el_menu(entrar):
    page = entrar("admin")
    page.get_by_role("link", name="Administrar").click()
    expect(page.locator(".tabla tbody tr").first).to_be_visible()


def test_en_movil_la_navegacion_vive_tras_la_hamburguesa(entrar, page: Page):
    page.set_viewport_size({"width": 390, "height": 844})
    entrar("mesero")

    # Los enlaces existen pero están plegados hasta abrir el menú.
    expect(page.locator("#hamburguesa")).to_be_visible()
    expect(page.get_by_role("link", name="Menú")).to_be_hidden()

    page.locator("#hamburguesa").click()
    page.get_by_role("link", name="Menú").click()
    expect(page.locator(".producto").first).to_be_visible()

    assert page.evaluate(
        "document.documentElement.scrollWidth <= window.innerWidth + 1"
    ), "la página se desborda a lo ancho en móvil"
