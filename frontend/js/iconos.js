/**
 * Iconos de linea, dibujados como SVG en el propio HTML.
 *
 * Nada de emojis: se ven distinto en cada sistema operativo, no heredan el
 * color del texto y no se pueden alinear con precision. Estos toman el
 * `currentColor` de donde se pongan y escalan sin perder nitidez.
 */
const TRAZOS = {
  // Marca: un plato visto desde arriba.
  marca: '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="3.25"/>',

  alerta: '<path d="M10.3 4 2.5 17.5A2 2 0 0 0 4.2 20.5h15.6a2 2 0 0 0 1.7-3L13.7 4a2 2 0 0 0-3.4 0Z"/><path d="M12 10v3.5M12 17h.01"/>',
  check: '<path d="m4.5 12.5 5 5 10-11"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11.5v5M12 8h.01"/>',
  cerrar: '<path d="M6.5 6.5l11 11M17.5 6.5l-11 11"/>',
  flechaIzq: '<path d="M19 12H5M11 6l-6 6 6 6"/>',
  mas: '<path d="M12 5.5v13M5.5 12h13"/>',
  menos: '<path d="M5.5 12h13"/>',

  busqueda: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.7-3.7"/>',
  carta: '<rect x="5" y="3" width="14" height="18" rx="2.5"/><path d="M9 8.5h6M9 12.5h6M9 16.5h3"/>',
  carpeta: '<path d="M3 7.5A2 2 0 0 1 5 5.5h3.6l2 2H19a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/>',
  recibo: '<path d="M6 3h12v18l-3-2-3 2-3-2-3 2Z"/><path d="M9.5 8.5h5M9.5 12.5h5"/>',
  olla: '<path d="M4 9.5h16v5.5a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4Z"/><path d="M4 9.5 2 7.5M20 9.5l2-2"/><path d="M9.5 6c0-1.2 1-1.5 1-2.8M14 6c0-1.2 1-1.5 1-2.8"/>',
  campana: '<path d="M18 9.5a6 6 0 1 0-12 0c0 4.5-2 5.5-2 5.5h16s-2-1-2-5.5Z"/><path d="M10.2 18.5a2.2 2.2 0 0 0 3.6 0"/>',
  candado: '<rect x="4.5" y="10.5" width="15" height="9.5" rx="2.5"/><path d="M8 10.5V7.5a4 4 0 0 1 8 0v3"/>',
  reloj: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5.3l3.2 1.9"/>',
  tarjeta: '<rect x="2.5" y="5.5" width="19" height="13" rx="2.5"/><path d="M2.5 10h19"/>',
  mesa: '<path d="M3 9.5h18M5.5 9.5v9M18.5 9.5v9"/><path d="M4 6.5h16"/>',
};

/** Devuelve el SVG del icono como cadena, listo para meter en una plantilla. */
export function icono(nombre, { tam = 20, clase = "" } = {}) {
  const trazo = TRAZOS[nombre];
  if (!trazo) return "";
  return `<svg class="ico ${clase}" width="${tam}" height="${tam}" viewBox="0 0 24 24"
    fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"
    stroke-linejoin="round" aria-hidden="true" focusable="false">${trazo}</svg>`;
}

export const NOMBRES = Object.keys(TRAZOS);
