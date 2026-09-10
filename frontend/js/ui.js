/**
 * Piezas de interfaz reutilizables: formato, avisos, modales y plantillas.
 */
import { icono } from "./iconos.js";

/** Escapa texto que viene del servidor antes de meterlo en innerHTML. */
export const esc = (valor) =>
  String(valor ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );

const formatoMoneda = new Intl.NumberFormat("es-MX", {
  style: "currency",
  currency: "MXN",
  minimumFractionDigits: 2,
});

/** La API manda el dinero como string ("417.60") para no perder precision. */
export const dinero = (valor) => formatoMoneda.format(Number(valor ?? 0));

export function hora(iso) {
  return new Date(iso).toLocaleTimeString("es-MX", { hour: "2-digit", minute: "2-digit" });
}

export function fechaHora(iso) {
  return new Date(iso).toLocaleString("es-MX", {
    day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
  });
}

export const ETIQUETA_ESTADO = {
  PENDIENTE: "Pendiente",
  EN_PREPARACION: "En preparación",
  LISTA: "Lista",
  ENTREGADA: "Entregada",
  CANCELADA: "Cancelada",
};

export const ETIQUETA_ITEM = {
  PENDIENTE: "Por preparar",
  EN_PREPARACION: "En preparación",
  LISTA: "Lista",
  ENTREGADA: "Entregada",
};

export const ETIQUETA_TIPO = {
  LOCAL: "En el local",
  PARA_LLEVAR: "Para llevar",
  DOMICILIO: "A domicilio",
};

export const ETIQUETA_METODO = {
  EFECTIVO: "Efectivo",
  TARJETA: "Tarjeta",
  TRANSFERENCIA: "Transferencia",
};

export const insigniaEstado = (estado) =>
  `<span class="insignia insignia--${estado.toLowerCase()}">${ETIQUETA_ESTADO[estado] ?? estado}</span>`;

export const insigniaItem = (estado) =>
  `<span class="insignia insignia--sm insignia--${estado.toLowerCase()}">${
    ETIQUETA_ITEM[estado] ?? estado
  }</span>`;

// ------------------------------------------------------------------ avisos

export function avisar(mensaje, tipo = "error") {
  const contenedor = document.getElementById("avisos");
  const iconos = { error: "alerta", ok: "check", info: "info" };
  const nodo = document.createElement("div");
  nodo.className = `aviso aviso--${tipo}`;
  nodo.innerHTML = `<span class="aviso__icono">${icono(iconos[tipo] ?? "info", { tam: 17 })}</span>
    <span>${esc(mensaje)}</span>`;
  contenedor.append(nodo);
  setTimeout(() => {
    nodo.style.transition = "opacity 220ms";
    nodo.style.opacity = "0";
    setTimeout(() => nodo.remove(), 220);
  }, 4200);
}

// ------------------------------------------------------------------ modal

/**
 * Abre un modal. `contenido` es HTML; `alAbrir` recibe el nodo para
 * enganchar eventos y `alCerrar` se dispara pase lo que pase (boton, clic
 * fuera o Escape). Devuelve una funcion para cerrarlo.
 */
export function modal({ titulo, contenido, pie = "", alAbrir, alCerrar }) {
  const fondo = document.createElement("div");
  fondo.className = "modal-fondo";
  fondo.innerHTML = `
    <div class="modal" role="dialog" aria-modal="true" aria-label="${esc(titulo)}">
      <div class="modal__titulo">
        <h2>${esc(titulo)}</h2>
        <button class="modal__cerrar" aria-label="Cerrar">&times;</button>
      </div>
      <div class="modal__cuerpo">${contenido}</div>
      ${pie ? `<div class="modal__pie">${pie}</div>` : ""}
    </div>`;

  let cerrado = false;
  const cerrar = () => {
    if (cerrado) return;
    cerrado = true;
    fondo.remove();
    document.removeEventListener("keydown", alTeclado);
    alCerrar?.();
  };
  const alTeclado = (e) => e.key === "Escape" && cerrar();

  fondo.querySelector(".modal__cerrar").addEventListener("click", cerrar);
  fondo.addEventListener("click", (e) => e.target === fondo && cerrar());
  document.addEventListener("keydown", alTeclado);

  document.body.append(fondo);
  alAbrir?.(fondo, cerrar);
  return cerrar;
}

export function confirmar(mensaje, { textoOk = "Confirmar", peligro = true } = {}) {
  return new Promise((resolver) => {
    let respuesta = false;
    modal({
      titulo: "Confirmar",
      contenido: `<p>${esc(mensaje)}</p>`,
      pie: `
        <button class="btn btn--fantasma" data-no>Cancelar</button>
        <button class="btn ${peligro ? "" : "btn--amarillo"}" data-si>${esc(textoOk)}</button>`,
      alAbrir(nodo, cerrar) {
        nodo.querySelector("[data-si]").addEventListener("click", () => {
          respuesta = true;
          cerrar();
        });
        nodo.querySelector("[data-no]").addEventListener("click", cerrar);
      },
      // Cualquier forma de cerrar (Escape, clic fuera, boton) resuelve la promesa.
      alCerrar: () => resolver(respuesta),
    });
  });
}

// ------------------------------------------------------------- plantillas

export const cargando = () => `<div class="cargando"><div class="girador"></div></div>`;

/** Estado vacio. `nombre` es una clave de iconos.js, no un emoji. */
export const vacio = (nombre, titulo, texto = "") => `
  <div class="vacio">
    <div class="vacio__icono">${icono(nombre, { tam: 34 })}</div>
    <h3>${esc(titulo)}</h3>
    ${texto ? `<p>${esc(texto)}</p>` : ""}
  </div>`;
