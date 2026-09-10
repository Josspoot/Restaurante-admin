/**
 * Router por hash (#/ruta). Sin dependencias y sin configuracion de servidor:
 * recargar la pagina en cualquier vista siempre funciona.
 */
import { sesion } from "./sesion.js";
import { avisar, vacio } from "./ui.js";

const rutas = [];
let alCambiar = null;

export function definirRutas(definiciones, callback) {
  rutas.length = 0;
  rutas.push(...definiciones);
  alCambiar = callback;
}

function actual() {
  const hash = location.hash.replace(/^#/, "") || "/";
  const [camino, consulta] = hash.split("?");
  return {
    segmentos: camino.split("/").filter(Boolean),
    consulta: new URLSearchParams(consulta ?? ""),
  };
}

function emparejar(patron, segmentos) {
  const partes = patron.split("/").filter(Boolean);
  if (partes.length !== segmentos.length) return null;
  const params = {};
  for (let i = 0; i < partes.length; i++) {
    if (partes[i].startsWith(":")) params[partes[i].slice(1)] = decodeURIComponent(segmentos[i]);
    else if (partes[i] !== segmentos[i]) return null;
  }
  return params;
}

export function ir(ruta) {
  location.hash = ruta.startsWith("#") ? ruta : `#${ruta}`;
}

export async function resolver() {
  const { segmentos, consulta } = actual();
  const contenedor = document.getElementById("vista");

  for (const ruta of rutas) {
    const params = emparejar(ruta.path, segmentos);
    if (!params) continue;

    // Guardas de acceso: sesion y rol.
    if (!ruta.publica && !sesion.activa) return ir("/login");
    if (ruta.roles && !ruta.roles.includes(sesion.rol)) {
      avisar("No tienes permiso para entrar a esa sección");
      return ir(sesion.esPersonal ? "/ordenes" : "/menu");
    }

    alCambiar?.(ruta);
    window.scrollTo({ top: 0 });
    try {
      await ruta.vista(contenedor, { ...params, consulta });
    } catch (e) {
      // Sin este console.error un fallo de la vista queda invisible al depurar.
      console.error(`Fallo la vista ${ruta.path}:`, e);
      contenedor.innerHTML = vacio("alerta", "Algo salió mal", e.message);
    }
    return;
  }

  ir(sesion.activa ? (sesion.esPersonal ? "/ordenes" : "/menu") : "/login");
}

export function iniciarRouter() {
  window.addEventListener("hashchange", resolver);
  resolver();
}
