"""Un pedido que sale del restaurante pide a quién buscar."""
from playwright.sync_api import Page, expect


def ticket_con_un_platillo(entrar):
    page = entrar("cliente")
    page.get_by_role("link", name="Menú").click()
    page.locator(".platillo [data-agregar]").first.click()
    page.locator("#ticket-flotante").click()
    expect(page.locator("#ticket-panel .linea")).to_have_count(1)
    return page


def test_comer_aqui_solo_pide_la_mesa(entrar):
    page = ticket_con_un_platillo(entrar)
    expect(page.locator("#mesa")).to_be_visible()
    expect(page.locator(".entrega")).to_have_count(0)


def test_para_llevar_pide_contacto_pero_no_domicilio(entrar):
    page = ticket_con_un_platillo(entrar)
    page.locator("#tipo").select_option("PARA_LLEVAR")

    expect(page.locator("#nombre")).to_be_visible()
    expect(page.locator("#telefono")).to_be_visible()
    expect(page.locator("#metodo")).to_be_visible()
    # Quien recoge viene al restaurante: su dirección no aporta nada.
    expect(page.locator("#direccion")).to_have_count(0)
    expect(page.locator(".entrega")).to_contain_text("Lo recoges en el restaurante")


def test_a_domicilio_si_pide_la_direccion(entrar):
    page = ticket_con_un_platillo(entrar)
    page.locator("#tipo").select_option("DOMICILIO")
    expect(page.locator("#direccion")).to_be_visible()


def test_sin_datos_lo_rechaza_con_un_mensaje_legible(entrar):
    page = ticket_con_un_platillo(entrar)
    page.locator("#tipo").select_option("PARA_LLEVAR")
    page.get_by_role("button", name="Enviar mi pedido").click()

    aviso = page.locator(".aviso")
    expect(aviso).to_contain_text("falta")
    expect(aviso).not_to_contain_text("Value error")   # ruido de la librería


def test_lo_escrito_sobrevive_a_un_cambio_en_el_carrito(entrar):
    page = ticket_con_un_platillo(entrar)
    page.locator("#tipo").select_option("PARA_LLEVAR")
    page.locator("#nombre").fill("Ana Ruiz")
    page.locator("#notas").fill("Sin cebolla")

    # Cambiar la cantidad repinta el panel entero.
    page.locator("#ticket-panel [data-mas]").first.click()
    expect(page.locator("#ticket-panel .contador span")).to_have_text("2")

    expect(page.locator("#nombre")).to_have_value("Ana Ruiz")
    expect(page.locator("#notas")).to_have_value("Sin cebolla")


def test_el_pedido_a_domicilio_guarda_y_muestra_sus_datos(entrar, page: Page):
    page = ticket_con_un_platillo(entrar)
    page.locator("#tipo").select_option("DOMICILIO")
    page.locator("#nombre").fill("Ana Ruiz")
    page.locator("#telefono").fill("9991234567")
    page.locator("#direccion").fill("Calle 60 #123, Centro")
    page.locator("#metodo").select_option("TARJETA")
    page.get_by_role("button", name="Enviar mi pedido").click()

    ficha = page.locator(".ficha-entrega")
    expect(ficha).to_contain_text("Ana Ruiz")
    expect(ficha).to_contain_text("9991234567")
    expect(ficha).to_contain_text("Calle 60 #123")
    expect(ficha).to_contain_text("Tarjeta")
    # El método es una intención: la orden sigue debiendo.
    expect(ficha).to_contain_text("el cobro se registra aparte")
    expect(page.locator(".orden-cabecera .insignia", has_text="Saldo")).to_be_visible()


def test_el_mesero_tambien_captura_esos_datos(entrar, page: Page):
    page = entrar("mesero")
    page.get_by_role("link", name="Menú").click()
    page.locator(".producto .agregar:not([disabled])").first.click()

    expect(page.locator(".entrega")).to_have_count(0)      # arranca en local
    page.locator("#tipo").select_option("DOMICILIO")

    expect(page.locator("#nombre")).to_be_visible()
    expect(page.locator("#direccion")).to_be_visible()
    expect(page.locator("#mesa")).to_be_disabled()         # ya no hay mesa
