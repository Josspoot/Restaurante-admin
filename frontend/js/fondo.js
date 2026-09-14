/**
 * Telón decorativo de la vista del comensal.
 *
 * Son manchas de color y platillos muy tenues detrás del contenido: dan
 * ambiente sin competir con lo que se lee. Van en una capa aparte, fija y sin
 * capturar el ratón, para no tocar la maquetación de nada.
 *
 * Solo se pinta para el cliente: al personal le estorbaría.
 */
import { ilustracion } from "./ilustraciones.js";

// Posiciones fijas, no aleatorias: así el fondo no "salta" entre recargas.
// Se reparten por los bordes para dejar libre la columna central de lectura.
const MANCHAS = [
  { arriba: "-8%", izq: "-6%", tam: "46vw", color: "var(--amarillo-sol)", retraso: "0s" },
  { arriba: "18%", izq: "72%", tam: "38vw", color: "var(--rojo-borde)", retraso: "-8s" },
  { arriba: "62%", izq: "-12%", tam: "42vw", color: "var(--rojo-claro)", retraso: "-16s" },
  { arriba: "78%", izq: "66%", tam: "40vw", color: "var(--amarillo-pale)", retraso: "-4s" },
];

const PLATILLOS = [
  { nombre: "Tacos al pastor", arriba: "8%", izq: "4%", giro: "-14deg", tam: "150px", retraso: "0s" },
  { nombre: "Cerveza artesanal", arriba: "22%", izq: "86%", giro: "12deg", tam: "120px", retraso: "-5s" },
  { nombre: "Guacamole con totopos", arriba: "48%", izq: "90%", giro: "-8deg", tam: "130px", retraso: "-11s" },
  { nombre: "Churros con cajeta", arriba: "58%", izq: "2%", giro: "16deg", tam: "140px", retraso: "-7s" },
  { nombre: "Flan napolitano", arriba: "84%", izq: "80%", giro: "-10deg", tam: "125px", retraso: "-14s" },
  { nombre: "Sopa de tortilla", arriba: "88%", izq: "10%", giro: "9deg", tam: "135px", retraso: "-3s" },
];

export function pintarFondo(activo) {
  const capa = document.getElementById("fondo-vivo");
  if (!capa) return;

  capa.hidden = !activo;
  if (!activo) {
    capa.innerHTML = "";
    return;
  }
  if (capa.childElementCount) return; // ya estaba pintado

  capa.innerHTML = [
    ...MANCHAS.map(
      (m) => `<span class="fondo-vivo__mancha" style="
        top:${m.arriba}; left:${m.izq}; width:${m.tam}; height:${m.tam};
        background:${m.color}; animation-delay:${m.retraso}"></span>`
    ),
    ...PLATILLOS.map(
      (p) => `<span class="fondo-vivo__plato" style="
        top:${p.arriba}; left:${p.izq}; width:${p.tam};
        --giro:${p.giro}; animation-delay:${p.retraso}">${ilustracion(p.nombre)}</span>`
    ),
  ].join("");
}
