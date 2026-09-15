"""Al comensal se le avisa cuando su pedido entra a cocina y cuando está listo."""
import pytest
from playwright.sync_api import Page, expect

PASTOR = 4


@pytest.fixture(autouse=True)
def sin_pedidos_previos(api):
    """Deja al comensal sin nada en curso antes de cada prueba.

    El servidor es de sesión y la base se comparte: si otra prueba dejó un
    pedido a medias, el aviso se convierte en el agregado ("2 novedades") y
    deja de poder comprobarse el mensaje concreto.
    """
    cliente, mesero = api("cliente"), api("mesero")
    orden_estados = ["EN_PREPARACION", "LISTA", "ENTREGADA"]
    for orden in cliente.get("/ordenes", params={"limit": 50}).json():
        if orden["estado"] in ("ENTREGADA", "CANCELADA"):
            continue
        desde = orden_estados.index(orden["estado"]) if orden["estado"] in orden_estados else -1
        for estado in orden_estados[desde + 1:]:
            mesero.patch(f"/ordenes/{orden['id']}/estado", json={"estado": estado})
    # Y sin recuerdos de avisos ya mostrados.
    yield


def pedido_del_cliente(api, mesa):
    """Crea un pedido a nombre del comensal de ejemplo."""
    cliente = api("cliente")
    return cliente.post("/ordenes", json={
        "tipo": "LOCAL", "mesa": mesa, "items": [{"producto_id": PASTOR, "cantidad": 1}],
    }).json()


def test_avisa_al_entrar_a_la_cocina(entrar, api):
    orden = pedido_del_cliente(api, 51)
    api("mesero").patch(f"/ordenes/{orden['id']}/estado", json={"estado": "EN_PREPARACION"})

    page = entrar("cliente")   # el sondeo corre al cargar
    expect(page.locator(".aviso")).to_contain_text("ya está en la cocina")
    expect(page.locator(".campana__punto")).to_be_visible()


def test_avisa_cuando_esta_listo(entrar, api):
    orden = pedido_del_cliente(api, 52)
    mesero = api("mesero")
    for estado in ("EN_PREPARACION", "LISTA"):
        mesero.patch(f"/ordenes/{orden['id']}/estado", json={"estado": estado})

    page = entrar("cliente")
    expect(page.locator(".aviso")).to_contain_text("está listo")


def test_el_panel_muestra_el_estado_pero_no_acciones_del_personal(entrar, api):
    orden = pedido_del_cliente(api, 53)
    api("mesero").patch(f"/ordenes/{orden['id']}/estado", json={"estado": "EN_PREPARACION"})

    page = entrar("cliente")
    page.locator("#campana").click()

    expect(page.locator(".panel-avisos__titulo")).to_contain_text("Mis pedidos")
    fila = page.locator(".aviso-fila", has_text=orden["numero"])
    expect(fila).to_contain_text("En preparación")
    # Marcar entregado es cosa del personal.
    expect(page.locator("[data-entregar]")).to_have_count(0)


def test_el_aviso_desaparece_al_entregarse(entrar, api, page: Page):
    orden = pedido_del_cliente(api, 54)
    mesero = api("mesero")
    for estado in ("EN_PREPARACION", "LISTA"):
        mesero.patch(f"/ordenes/{orden['id']}/estado", json={"estado": estado})

    page = entrar("cliente")
    expect(page.locator(".campana__punto")).to_be_visible()

    mesero.patch(f"/ordenes/{orden['id']}/estado", json={"estado": "ENTREGADA"})
    page.reload()
    expect(page.locator(".campana__punto")).to_have_count(0)
