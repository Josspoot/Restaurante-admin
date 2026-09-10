/**
 * Avisos para el mesero: cuando la cocina deja lista una tanda suya, se lo
 * decimos sin que tenga que estar mirando el tablero.
 *
 * Va por sondeo cada 20 s en lugar de WebSockets: no hace falta un canal
 * abierto para un aviso que tolera medio minuto de retraso.
 */
import { api } from "./api.js";
import { sesion } from "./sesion.js";
import { ir, resolver } from "./router.js";
import { icono } from "./iconos.js";
import { avisar, esc, hora } from "./ui.js";

const INTERVALO_MS = 20000;
const CLAVE_VISTOS = "sabor.avisos.vistos";

let temporizador = null;
let avisos = [];
let abierto = false;

const clave = (a) => `${a.orden_id}-${a.tanda}`;

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
    /* modo privado: los avisos se repetirian, no es grave */
  }
}

// ------------------------------------------------------------------ sondeo

async function consultar() {
  if (!sesion.esPersonal) return;

  let recibidos;
  try {
    recibidos = await api.avisos();
  } catch {
    return; // un fallo de red no debe romper la cabecera; se reintenta solo
  }

  const vistos = leerVistos();
  const actuales = new Set(recibidos.map(clave));
  const nuevos = recibidos.filter((a) => !vistos.has(clave(a)));

  avisos = recibidos;
  pintar();

  if (nuevos.length === 1) {
    const a = nuevos[0];
    avisar(`Lista para entregar: ${a.numero}${a.mesa ? ` · mesa ${a.mesa}` : ""}`, "ok");
  } else if (nuevos.length > 1) {
    avisar(`${nuevos.length} órdenes listas para entregar`, "ok");
  }
  if (nuevos.length) sacudir();

  // Solo se recuerda lo que sigue listo: si se entrega y vuelve a pedirse, avisa de nuevo.
  guardarVistos(new Set([...vistos, ...actuales].filter((k) => actuales.has(k))));
}

function sacudir() {
  const campana = document.getElementById("campana");
  if (!campana) return;
  campana.classList.remove("campana--suena");
  void campana.offsetWidth; // reinicia la animacion
  campana.classList.add("campana--suena");
}

// ------------------------------------------------------------------ pintado

function pintar() {
  const caja = document.getElementById("avisador");
  if (!caja) return;

  if (!sesion.esPersonal) {
    caja.innerHTML = "";
    return;
  }

  caja.innerHTML = `
    <button class="campana ${avisos.length ? "campana--activa" : ""}" id="campana"
            aria-label="${avisos.length} órdenes listas para entregar"
            aria-expanded="${abierto}">
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
        // Si el mesero tiene esa misma orden abierta detrás, quedaría desfasada.
        await resolver();
      } catch (err) {
        avisar(err.message);
        boton.disabled = false;
      }
    })
  );
}

const panel = () => `
  <div class="panel-avisos" role="dialog" aria-label="Órdenes listas">
    <div class="panel-avisos__titulo">
      <span>Listas para entregar</span>
      <span class="panel-avisos__conteo">${avisos.length}</span>
    </div>
    ${
      avisos.length
        ? avisos
            .map(
              (a) => `<div class="aviso-fila" data-abrir-orden="${a.orden_id}">
                <div class="aviso-fila__cabecera">
                  <strong>${esc(a.numero)}</strong>
                  ${a.mesa ? `<span class="aviso-fila__mesa">Mesa ${a.mesa}</span>` : ""}
                  ${a.tanda > 1 ? `<span class="insignia insignia--sm insignia--pendiente">Tanda ${a.tanda}</span>` : ""}
                  <span class="aviso-fila__hora">${hora(a.creado_en)}</span>
                </div>
                <div class="aviso-fila__items">
                  ${a.items.map((i) => `${i.cantidad}× ${esc(i.nombre_producto)}`).join(" · ")}
                </div>
                <button class="btn btn--sm" data-entregar="${a.orden_id}" data-tanda="${a.tanda}">
                  Marcar entregada
                </button>
              </div>`
            )
            .join("")
        : `<p class="panel-avisos__vacio">Nada pendiente de llevar a la mesa.</p>`
    }
  </div>`;

// ------------------------------------------------------------------ control

export function iniciarAvisador() {
  detenerAvisador();
  if (!sesion.esPersonal) {
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
