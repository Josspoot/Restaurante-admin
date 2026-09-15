"""La vista del comensal: portada, carta, vuelo al ticket y pie de página."""
import re

from playwright.sync_api import Page, expect


def menu_del_cliente(entrar):
    page = entrar("cliente")
    page.get_by_role("link", name="Menú").click()
    expect(page.locator("#portada")).to_be_visible()
    return page


def test_la_portada_presenta_platillos_con_ilustracion(entrar):
    page = menu_del_cliente(entrar)

    expect(page.locator(".diapo").first).to_be_visible()
    assert page.locator(".diapo").count() > 1
    expect(page.locator(".diapo__arte .ilustracion").first).to_be_visible()
    expect(page.locator(".diapo__desc").first).not_to_be_empty()
    expect(page.locator(".diapo__precio").first).to_contain_text("$")


def test_la_portada_avanza_sola_y_se_detiene_con_el_cursor(entrar, page: Page):
    menu_del_cliente(entrar)
    pista = page.locator("#pista")

    # Avanza sin tocar nada.
    expect(pista).to_have_attribute("style", re.compile(r"translateX\(-100%\)"), timeout=6000)

    # Con el cursor encima se queda quieto: nada peor que cambiar al ir a pulsar.
    page.locator("#portada").hover()
    quieto = pista.get_attribute("style")
    page.wait_for_timeout(4000)
    assert pista.get_attribute("style") == quieto


def test_la_carta_se_agrupa_y_entra_al_bajar(entrar, page: Page):
    menu_del_cliente(entrar)

    assert page.locator(".carta__grupo").count() > 1
    assert page.locator(".platillo").count() > 0
    expect(page.locator(".platillo__desc").first).not_to_be_empty()

    # Lo que aún no se ve, no se ha revelado.
    assert page.locator(".revelable:not(.revelado)").count() > 0
    page.mouse.wheel(0, 3000)
    expect(page.locator(".platillo.revelado").first).to_be_visible()


def test_la_portada_se_desvanece_al_bajar(entrar, page: Page):
    menu_del_cliente(entrar)
    page.mouse.wheel(0, 2000)
    page.wait_for_timeout(400)
    opacidad = page.evaluate("getComputedStyle(document.getElementById('portada')).opacity")
    assert float(opacidad) < 0.5, f"la portada sigue opaca: {opacidad}"


def test_agregar_lanza_el_platillo_al_ticket(entrar, page: Page):
    menu_del_cliente(entrar)
    page.mouse.wheel(0, 1200)

    page.locator(".platillo [data-agregar]").first.click()
    # La copia que vuela existe mientras dura la animación y luego se retira.
    expect(page.locator(".volador")).to_have_count(1)
    expect(page.locator(".volador")).to_have_count(0, timeout=4000)

    expect(page.locator("#ticket-conteo")).to_have_text("1")
    expect(page.locator("#ticket-flotante")).to_have_class(re.compile("ticket-flotante--lleno"))


def test_el_comensal_envia_su_pedido(entrar, page: Page):
    menu_del_cliente(entrar)
    page.locator(".platillo [data-agregar]").first.click()

    page.locator("#ticket-flotante").click()
    panel = page.locator("#ticket-panel")
    expect(panel.locator(".linea")).to_have_count(1)
    expect(panel.locator(".totales__fila--total")).to_contain_text("$")

    panel.get_by_role("button", name="Enviar mi pedido").click()
    expect(page).to_have_url(re.compile(r"#/ordenes/\d+$"))
    assert page.evaluate("JSON.parse(localStorage.getItem('sabor.carrito') ?? '[]').length") == 0


def test_el_comensal_no_ve_filtros_que_no_le_tocan(entrar, page: Page):
    page = entrar("cliente")
    page.goto(f"{page.url.split('#')[0]}#/ordenes")
    expect(page.locator(".filtro-fila__etiqueta")).to_have_text(["Estado"])


def test_hay_pie_de_pagina_con_contacto_y_derechos(entrar, page: Page):
    entrar("cliente")
    pie = page.locator("#pie")
    expect(pie).to_contain_text("Contacto")
    expect(pie).to_contain_text("derechos reservados")


def test_el_telon_decorativo_es_solo_del_comensal(entrar, page: Page):
    entrar("cliente")
    expect(page.locator(".fondo-vivo__mancha")).to_have_count(4)
    expect(page.locator(".fondo-vivo__plato")).to_have_count(6)

    page.locator("#salir").click()
    page.get_by_role("button", name="Mesero", exact=True).click()
    expect(page.locator("#fondo-vivo")).to_be_hidden()


def test_en_movil_la_carta_no_se_desborda(entrar, page: Page):
    page.set_viewport_size({"width": 390, "height": 844})
    page = entrar("cliente")
    page.locator("#hamburguesa").click()
    page.get_by_role("link", name="Menú").click()

    expect(page.locator(".platillo").first).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
    expect(page.locator("#ticket-flotante")).to_be_visible()
