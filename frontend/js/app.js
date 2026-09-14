/**
 * Arranque de la aplicacion: define las rutas y mantiene la cabecera al dia.
 */
import { sesion } from "./sesion.js";
import { definirRutas, iniciarRouter, ir, resolver } from "./router.js";
import { carrito } from "./carrito.js";
import { iniciarAvisador, detenerAvisador } from "./avisador.js";
import { esc } from "./ui.js";
import { icono } from "./iconos.js";
import { pintarFondo } from "./fondo.js";

import { vistaLogin } from "./vistas/login.js";
import { vistaMenu } from "./vistas/menu.js";
import { vistaOrdenes } from "./vistas/ordenes.js";
import { vistaOrdenDetalle } from "./vistas/orden_detalle.js";
import { vistaCocina } from "./vistas/cocina.js";
import { vistaAdmin } from "./vistas/admin.js";

const PERSONAL = ["ADMIN", "MESERO"];

const RUTAS = [
  { path: "/login", vista: vistaLogin, publica: true },
  { path: "/menu", vista: vistaMenu },
  { path: "/ordenes", vista: vistaOrdenes },
  { path: "/ordenes/:id", vista: vistaOrdenDetalle },
  { path: "/cocina", vista: vistaCocina, roles: PERSONAL },
  { path: "/admin", vista: vistaAdmin, roles: ["ADMIN"] },
];

const ENLACES = [
  { href: "#/menu", texto: "Menú" },
  { href: "#/ordenes", texto: "Órdenes" },
  { href: "#/cocina", texto: "Cocina", roles: PERSONAL },
  { href: "#/admin", texto: "Administrar", roles: ["ADMIN"] },
];

function pintarCabecera(rutaActiva) {
  const cabecera = document.getElementById("cabecera");
  const nav = document.getElementById("nav");
  const caja = document.getElementById("sesion");

  const pie = document.getElementById("pie");
  cabecera.hidden = !sesion.activa;
  pie.hidden = !sesion.activa;
  // El telón decorativo es solo para el comensal.
  pintarFondo(sesion.activa && !sesion.esPersonal);
  if (!sesion.activa) return;

  // El pie es estático salvo el año y el logotipo, que se rellenan una vez.
  const pieIcono = document.getElementById("pie-icono");
  if (pieIcono && !pieIcono.childElementCount) {
    pieIcono.innerHTML = icono("marca", { tam: 19 });
    document.getElementById("pie-anio").textContent = new Date().getFullYear();
  }

  nav.innerHTML = ENLACES.filter((e) => !e.roles || e.roles.includes(sesion.rol))
    .map((e) => {
      const activo = rutaActiva?.path?.startsWith(e.href.slice(1)) ? " activo" : "";
      const conteo = e.href === "#/menu" && carrito.piezas ? ` data-conteo="${carrito.piezas}"` : "";
      return `<a href="${e.href}" class="${activo.trim()}"${conteo}>${e.texto}</a>`;
    })
    .join("");

  const u = sesion.usuario;
  const iniciales = u.nombre.split(" ").map((p) => p[0]).slice(0, 2).join("").toUpperCase();
  caja.innerHTML = `
    <div class="usuario">
      <div class="usuario__avatar">${esc(iniciales)}</div>
      <div class="usuario__datos">
        <span class="usuario__nombre">${esc(u.nombre)}</span>
        <span class="usuario__rol">${esc(u.rol)}</span>
      </div>
    </div>
    <button class="btn btn--fantasma btn--sm" id="salir">Salir</button>`;

  document.getElementById("salir").addEventListener("click", () => {
    sesion.cerrar();
    detenerAvisador();
    ir("/login");
  });

  nav.classList.remove("abierto");
  document.getElementById("hamburguesa").setAttribute("aria-expanded", "false");
}

document.getElementById("hamburguesa").addEventListener("click", (e) => {
  const nav = document.getElementById("nav");
  const abierto = nav.classList.toggle("abierto");
  e.currentTarget.setAttribute("aria-expanded", String(abierto));
});

/**
 * Onda al pulsar, delegada para toda la aplicacion.
 *
 * Los controles se repintan constantemente, asi que enganchar el efecto en
 * cada uno seria imposible de mantener: se escucha una sola vez en el
 * documento y se dibuja desde el punto exacto del clic.
 */
document.addEventListener("pointerdown", (evento) => {
  const control = evento.target.closest(".btn, .chip, .agregar, .campana");
  if (!control || control.disabled || control.dataset.ocupado !== undefined) return;

  const caja = control.getBoundingClientRect();
  const lado = Math.max(caja.width, caja.height);
  const onda = document.createElement("span");
  onda.className = "onda";
  onda.style.width = onda.style.height = `${lado}px`;
  onda.style.left = `${evento.clientX - caja.left - lado / 2}px`;
  onda.style.top = `${evento.clientY - caja.top - lado / 2}px`;
  control.append(onda);
  onda.addEventListener("animationend", () => onda.remove(), { once: true });
});

// El contador del carrito vive en la cabecera: se repinta cuando cambia.
carrito.alCambiar(() => pintarCabecera({ path: location.hash.slice(1) }));

let rolAnterior = null;

definirRutas(RUTAS, (ruta) => {
  pintarCabecera(ruta);
  // El avisador se arranca al entrar y se apaga al salir o cambiar de rol.
  if (sesion.rol !== rolAnterior) {
    rolAnterior = sesion.rol;
    sesion.activa ? iniciarAvisador() : detenerAvisador();
  }
});
iniciarRouter();

export { resolver };
