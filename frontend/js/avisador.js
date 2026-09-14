/**
 * Avisos en la cabecera, con dos caras según quién mira.
 *
 * - Al mesero le interesa lo que la cocina ya sacó y sigue sin llevarse.
 * - Al comensal le interesa su propio pedido: cuándo entra a la cocina y
 *   cuándo está listo.
 *
 * Los dos casos se normalizan a la misma forma para que el panel se pinte una
 * sola vez. Va por sondeo en lugar de WebSockets: es un aviso que tolera medio
 * minuto de retraso y no justifica mantener un canal abierto.
 */
import { api } from "./api.js";
import { sesion } from "./sesion.js";
import { ir, resolver } from "./router.js";
import { icono } from "./iconos.js";
import { ETIQUETA_ESTADO, avisar, esc, hora, insigniaEstado } from "./ui.js";

const INTERVALO_MS = 20000;
const CLAVE_VISTOS = "sabor.avisos.vistos";

// Estados del pedido que merecen un aviso al comensal, con su mensaje.
const AVISOS_CLIENTE = {
  EN_PREPARACION: (n) => `Tu pedido ${n} ya está en la cocina`,
  LISTA: (n) => `¡Tu pedido ${n} está listo!`,
};

let temporizador = null;
let avisos = [];
let abierto = false;

function leerVistos() {
  try {
    return new Set(JSON.parse(localStorage.getItem(CLAVE_VISTOS) ?? "[]"));
  } catch {
    return new Set();
  }
}

function guardarVistos(conjunto) {
  try {
    localStorage.setItem(CLAVE_VISTOS, JSON.stringify([...conjunto]));
  } catch {
    /* modo privado: los avisos se repetirían, no es grave */
  }
}

// ------------------------------------------------------------------ sondeo

/** Tandas listas que el mesero todavía no ha llevado a la mesa. */
async function recogerDePersonal() {
  const comandas = await api.avisos();
  return comandas.map((c) => ({
    // La clave incluye la tanda: una ronda nueva es un aviso nuevo.
    clave: `t:${c.orden_id}-${c.tanda}`,
    orden_id: c.orden_id,
    titulo: `${c.numero}${c.mesa ? ` · Mesa ${c.mesa}` : ""}`,
    etiqueta: c.tanda > 1 ? `Tanda ${c.tanda}` : "",
    detalle: c.items.map((i) => `${i.cantidad}× ${i.nombre_producto}`).join(" · "),
    hora: c.creado_en,
    mensaje: `Lista para entregar: ${c.numero}${c.mesa ? ` · mesa ${c.mesa}` : ""}`,
    entregar: { orden: c.orden_id, tanda: c.tanda },
  }));
}

/** Pedidos propios del comensal que están en marcha. */
async function recogerDeCliente() {
  const ordenes = await api.ordenes({ limit: 20 });
  return ordenes
    .filter((o) => o.estado in AVISOS_CLIENTE)
    .map((o) => ({
      // La clave incluye el estado: avisa al entrar a cocina y otra vez al estar lista.
      clave: `o:${o.id}-${o.estado}`,
      orden_id: o.id,
      titulo: o.numero,
      estado: o.estado,
      detalle: `${o.items.length} platillo${o.items.length === 1 ? "" : "s"} · ${
        ETIQUETA_ESTADO[o.estado]
      }`,
      hora: o.actualizado_en,
      mensaje: AVISOS_CLIENTE[o.estado](o.numero),
    }));
}

async function consultar() {
  if (!sesion.activa) return;

  let recibidos;
  try {
    recibidos = sesion.esPersonal ? await recogerDePersonal() : await recogerDeCliente();
  } catch {
    return; // un fallo de red no debe romper la cabecera; se reintenta solo
  }

  const vistos = leerVistos();
  const actuales = new Set(recibidos.map((a) => a.clave));
  const nuevos = recibidos.filter((a) => !vistos.has(a.clave));

  avisos = recibidos;
  pintar();

  if (nuevos.length === 1) {
    avisar(nuevos[0].mensaje, "ok");
  } else if (nuevos.length > 1) {
    avisar(
      sesion.esPersonal
        ? `${nuevos.length} órdenes listas para entregar`
        : `${nuevos.length} novedades en tus pedidos`,
      "ok"
    );
  }
  if (nuevos.length) sacudir();

  // Solo se recuerda lo que sigue vigente: si vuelve a ocurrir, avisa de nuevo.
  guardarVistos(new Set([...vistos, ...actuales].filter((k) => actuales.has(k))));
}

function sacudir() {
  const campana = document.getElementById("campana");
  if (!campana) return;
  campana.classList.remove("campana--suena");
  void campana.offsetWidth; // reinicia la animación
  campana.classList.add("campana--suena");
}

// ------------------------------------------------------------------ pintado

function pintar() {
  const caja = document.getElementById("avisador");
  if (!caja) return;

  if (!sesion.activa) {
    caja.innerHTML = "";
    return;
  }

  const etiqueta = sesion.esPersonal
    ? `${avisos.length} órdenes listas para entregar`
    : `${avisos.length} novedades en tus pedidos`;

  caja.innerHTML = `
    <button class="campana ${avisos.length ? "campana--activa" : ""}" id="campana"
            aria-label="${etiqueta}" aria-expanded="${abierto}">
      ${icono("campana", { tam: 19 })}
      ${avisos.length ? `<span class="campana__punto">${avisos.length}</span>` : ""}
    </button>
    ${abierto ? panel() : ""}`;

  document.getElementById("campana").addEventListener("click", (e) => {
    e.stopPropagation();
    abierto = !abierto;
    pintar();
  });

  if (!abierto) return;

  caja.querySelectorAll("[data-abrir-orden]").forEach((fila) =>
    fila.addEventListener("click", () => {
      abierto = false;
      pintar();
      ir(`/ordenes/${fila.dataset.abrirOrden}`);
    })
  );

  caja.querySelectorAll("[data-entregar]").forEach((boton) =>
    boton.addEventListener("click", async (e) => {
      e.stopPropagation();
      boton.disabled = true;
      try {
        await api.cambiarEstadoTanda(
          Number(boton.dataset.entregar), Number(boton.dataset.tanda), "ENTREGADA"
        );
        await consultar();
        // Si tiene esa misma orden abierta detrás, quedaría desfasada.
        await resolver();
      } catch (err) {
        avisar(err.message);
        boton.disabled = false;
      }
    })
  );
}

const panel = () => `
  <div class="panel-avisos" role="dialog" aria-label="Avisos">
    <div class="panel-avisos__titulo">
      <span>${sesion.esPersonal ? "Listas para entregar" : "Mis pedidos"}</span>
      <span class="panel-avisos__conteo">${avisos.length}</span>
    </div>
    ${
      avisos.length
        ? avisos.map(fila).join("")
        : `<p class="panel-avisos__vacio">${
            sesion.esPersonal
              ? "Nada pendiente de llevar a la mesa."
              : "No tienes pedidos en curso."
          }</p>`
    }
  </div>`;

const fila = (a) => `
  <div class="aviso-fila" data-abrir-orden="${a.orden_id}">
    <div class="aviso-fila__cabecera">
      <strong>${esc(a.titulo)}</strong>
      ${a.estado ? insigniaEstado(a.estado) : ""}
      ${a.etiqueta ? `<span class="insignia insignia--sm insignia--pendiente">${esc(a.etiqueta)}</span>` : ""}
      <span class="aviso-fila__hora">${hora(a.hora)}</span>
    </div>
    <div class="aviso-fila__items">${esc(a.detalle)}</div>
    ${
      a.entregar
        ? `<button class="btn btn--sm" data-entregar="${a.entregar.orden}"
             data-tanda="${a.entregar.tanda}">Marcar entregada</button>`
        : ""
    }
  </div>`;

// ------------------------------------------------------------------ control

export function iniciarAvisador() {
  detenerAvisador();
  if (!sesion.activa) {
    pintar();
    return;
  }
  consultar();
  temporizador = setInterval(consultar, INTERVALO_MS);
}

export function detenerAvisador() {
  clearInterval(temporizador);
  temporizador = null;
  avisos = [];
  abierto = false;
}

// Un clic fuera cierra el panel.
document.addEventListener("click", (e) => {
  if (abierto && !e.target.closest("#avisador")) {
    abierto = false;
    pintar();
  }
});
