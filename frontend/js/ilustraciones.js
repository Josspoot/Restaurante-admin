/**
 * Ilustraciones de los platillos, dibujadas como SVG.
 *
 * No son fotografías: la política de seguridad solo admite imágenes del propio
 * origen, y cargar fotos reales exigiría abrir la CSP a dominios externos o
 * subir archivos pesados. Con SVG el menú pesa unos pocos kilobytes, se ve
 * nítido en cualquier pantalla y encaja con la paleta de la aplicación.
 *
 * Cada platillo se asocia por su nombre, así que los que dé de alta el
 * administrador también reciben una ilustración razonable.
 */

const PALETA = {
  masa: "#f3b95f",
  masaOscura: "#d99a3e",
  carne: "#a4161a",
  carneClara: "#d62828",
  verde: "#6a994e",
  verdeClaro: "#8fbf6a",
  crema: "#fff3dc",
  cafe: "#6f4518",
  cafeClaro: "#9c6b3f",
  liquido: "#ffb703",
  espuma: "#fffaf0",
  hoja: "#4f772d",
};

const FONDOS = {
  calido: "#fff1cf",
  rosado: "#fce3df",
  verdoso: "#e8f1de",
  arena: "#f7ead6",
};

/** Envuelve el dibujo en un lienzo con fondo redondeado. */
const lienzo = (fondo, contenido) => `
  <rect width="160" height="120" rx="16" fill="${fondo}"/>
  ${contenido}`;

const vapor = (x) => `
  <path d="M${x} 34 q6 -8 0 -16 q-6 -8 0 -14" stroke="${PALETA.crema}" stroke-width="3"
        fill="none" stroke-linecap="round" opacity=".75"/>`;

const DIBUJOS = {
  taco: lienzo(FONDOS.calido, `
    <path d="M36 54 Q80 106 124 54" stroke="${PALETA.masa}" stroke-width="18"
          fill="none" stroke-linecap="round"/>
    <path d="M36 54 Q80 106 124 54" stroke="${PALETA.masaOscura}" stroke-width="18"
          fill="none" stroke-linecap="round" opacity=".25"
          stroke-dasharray="2 26" stroke-dashoffset="8"/>
    <path d="M44 50 Q80 92 116 50" stroke="${PALETA.carne}" stroke-width="11"
          fill="none" stroke-linecap="round"/>
    <circle cx="60" cy="56" r="4.5" fill="${PALETA.verde}"/>
    <circle cx="80" cy="66" r="4.5" fill="${PALETA.crema}"/>
    <circle cx="100" cy="56" r="4.5" fill="${PALETA.liquido}"/>`),

  carne: lienzo(FONDOS.rosado, `
    <ellipse cx="80" cy="68" rx="46" ry="27" fill="${PALETA.carne}"/>
    <ellipse cx="80" cy="64" rx="38" ry="21" fill="${PALETA.carneClara}"/>
    <path d="M56 58 L74 76 M74 54 L92 72 M92 56 L106 70" stroke="${PALETA.carne}"
          stroke-width="4" stroke-linecap="round" opacity=".8"/>
    <path d="M40 40 q10 -10 22 -4" stroke="${PALETA.hoja}" stroke-width="5"
          fill="none" stroke-linecap="round"/>`),

  enchilada: lienzo(FONDOS.rosado, `
    <ellipse cx="80" cy="74" rx="52" ry="24" fill="${PALETA.crema}"/>
    <rect x="42" y="50" width="76" height="14" rx="7" fill="${PALETA.masa}"/>
    <rect x="42" y="66" width="76" height="14" rx="7" fill="${PALETA.masa}"/>
    <path d="M46 57 h68 M46 73 h68" stroke="${PALETA.verde}" stroke-width="6"
          stroke-linecap="round" opacity=".85"/>
    <circle cx="62" cy="86" r="4" fill="${PALETA.espuma}"/>
    <circle cx="80" cy="88" r="4" fill="${PALETA.espuma}"/>
    <circle cx="98" cy="86" r="4" fill="${PALETA.espuma}"/>`),

  sopa: lienzo(FONDOS.calido, `
    ${vapor(70)} ${vapor(90)}
    <path d="M32 62 a48 48 0 0 0 96 0 Z" fill="${PALETA.carneClara}"/>
    <ellipse cx="80" cy="62" rx="48" ry="11" fill="${PALETA.crema}"/>
    <ellipse cx="80" cy="62" rx="40" ry="8" fill="${PALETA.liquido}"/>
    <path d="M62 60 l10 4 M84 58 l12 5" stroke="${PALETA.masa}" stroke-width="4"
          stroke-linecap="round"/>`),

  queso: lienzo(FONDOS.arena, `
    <path d="M34 58 a46 46 0 0 0 92 0 Z" fill="${PALETA.cafe}"/>
    <ellipse cx="80" cy="58" rx="46" ry="10" fill="${PALETA.cafeClaro}"/>
    <ellipse cx="80" cy="57" rx="37" ry="7.5" fill="${PALETA.liquido}"/>
    <path d="M58 58 q8 10 16 0 q8 10 16 0 q8 10 14 0" stroke="${PALETA.masa}"
          stroke-width="4" fill="none" stroke-linecap="round"/>
    <path d="M26 58 h10 M124 58 h10" stroke="${PALETA.cafe}" stroke-width="6"
          stroke-linecap="round"/>`),

  guacamole: lienzo(FONDOS.verdoso, `
    <path d="M40 64 a40 34 0 0 0 80 0 Z" fill="${PALETA.crema}"/>
    <path d="M64 70 L72 34 L80 70 Z" fill="${PALETA.masa}"/>
    <path d="M88 70 L97 40 L104 70 Z" fill="${PALETA.masaOscura}"/>
    <ellipse cx="80" cy="64" rx="40" ry="9" fill="${PALETA.verde}"/>
    <ellipse cx="80" cy="62" rx="31" ry="6" fill="${PALETA.verdeClaro}"/>`),

  bebida: lienzo(FONDOS.calido, `
    <path d="M60 32 h40 l-6 62 a6 6 0 0 1 -6 5 h-16 a6 6 0 0 1 -6 -5 Z"
          fill="${PALETA.espuma}" opacity=".9"/>
    <path d="M63 48 h34 l-5 46 a6 6 0 0 1 -6 5 h-12 a6 6 0 0 1 -6 -5 Z"
          fill="${PALETA.liquido}"/>
    <rect x="86" y="18" width="6" height="30" rx="3" fill="${PALETA.carneClara}"
          transform="rotate(12 89 33)"/>
    <rect x="70" y="54" width="11" height="11" rx="3" fill="${PALETA.espuma}" opacity=".8"/>
    <rect x="82" y="70" width="10" height="10" rx="3" fill="${PALETA.espuma}" opacity=".8"/>`),

  cerveza: lienzo(FONDOS.arena, `
    <rect x="52" y="40" width="48" height="60" rx="8" fill="${PALETA.liquido}"/>
    <path d="M52 52 h48 v-6 a8 8 0 0 0 -8 -8 h-32 a8 8 0 0 0 -8 8 Z" fill="${PALETA.espuma}"/>
    <ellipse cx="64" cy="40" rx="11" ry="8" fill="${PALETA.espuma}"/>
    <ellipse cx="84" cy="37" rx="13" ry="9" fill="${PALETA.espuma}"/>
    <path d="M100 56 a14 14 0 0 1 0 26" stroke="${PALETA.masaOscura}" stroke-width="7"
          fill="none" stroke-linecap="round"/>
    <path d="M62 62 v28 M74 64 v24" stroke="${PALETA.espuma}" stroke-width="3"
          stroke-linecap="round" opacity=".55"/>`),

  cafe: lienzo(FONDOS.calido, `
    ${vapor(72)} ${vapor(92)}
    <ellipse cx="77" cy="96" rx="40" ry="9" fill="${PALETA.masa}" opacity=".45"/>
    <ellipse cx="77" cy="94" rx="34" ry="7" fill="${PALETA.espuma}"/>
    <path d="M104 58 a13 13 0 0 1 0 20" stroke="${PALETA.masa}" stroke-width="7"
          fill="none" stroke-linecap="round"/>
    <path d="M52 52 h50 v20 a25 25 0 0 1 -50 0 Z" fill="${PALETA.espuma}"/>
    <ellipse cx="77" cy="52" rx="25" ry="7" fill="${PALETA.cafe}"/>
    <ellipse cx="77" cy="52" rx="18" ry="4.5" fill="${PALETA.cafeClaro}"/>`),

  flan: lienzo(FONDOS.arena, `
    <ellipse cx="80" cy="92" rx="46" ry="10" fill="${PALETA.crema}"/>
    <path d="M50 88 q0 -34 30 -34 q30 0 30 34 Z" fill="${PALETA.liquido}"/>
    <path d="M50 88 q0 -34 30 -34 q30 0 30 34 Z" fill="${PALETA.espuma}" opacity=".35"/>
    <path d="M56 70 q24 14 48 0" stroke="${PALETA.cafeClaro}" stroke-width="5"
          fill="none" stroke-linecap="round"/>
    <circle cx="80" cy="50" r="5" fill="${PALETA.carneClara}"/>`),

  churros: lienzo(FONDOS.arena, `
    <path d="M46 92 L66 34 M66 94 L86 36 M86 92 L106 34" stroke="${PALETA.masa}"
          stroke-width="11" stroke-linecap="round"/>
    <path d="M46 92 L66 34 M66 94 L86 36 M86 92 L106 34" stroke="${PALETA.masaOscura}"
          stroke-width="11" stroke-linecap="round" stroke-dasharray="1 9" opacity=".45"/>
    <path d="M100 80 a17 17 0 0 0 34 0 Z" fill="${PALETA.crema}"/>
    <ellipse cx="117" cy="80" rx="17" ry="4.5" fill="${PALETA.cafe}"/>
    <ellipse cx="117" cy="79" rx="12" ry="3" fill="${PALETA.cafeClaro}"/>`),

  plato: lienzo(FONDOS.calido, `
    <ellipse cx="80" cy="62" rx="48" ry="30" fill="${PALETA.crema}"/>
    <ellipse cx="80" cy="62" rx="32" ry="19" fill="${PALETA.liquido}" opacity=".55"/>
    <ellipse cx="80" cy="62" rx="16" ry="9" fill="${PALETA.carneClara}" opacity=".7"/>`),
};

/** Nombre del platillo -> dibujo. El orden importa: gana la primera que case. */
const REGLAS = [
  [/taco|pastor|barbacoa|birria/i, "taco"],
  [/arrachera|carne|bistec|costilla|res|cochinita|pibil|cerdo/i, "carne"],
  [/enchilada|burrito|quesadilla|chilaquil|tortilla de harina/i, "enchilada"],
  [/sopa|caldo|crema|pozole|consom/i, "sopa"],
  [/queso|fundido|chorizo/i, "queso"],
  [/guacamole|aguacate|totopo|ensalada|nopal/i, "guacamole"],
  [/cerveza|michelada|tarro/i, "cerveza"],
  [/caf[eé]|t[eé]\b|chocolate caliente|capuchino/i, "cafe"],
  [/agua|limonada|refresco|jugo|horchata|jamaica|malteada|smoothie/i, "bebida"],
  [/flan|gelatina|pastel|cheesecake|helado|postre/i, "flan"],
  [/churro|buñuelo|dona|galleta/i, "churros"],
];

/** Devuelve la clave del dibujo que corresponde a un platillo. */
export function claveIlustracion(nombre = "") {
  for (const [patron, clave] of REGLAS) {
    if (patron.test(nombre)) return clave;
  }
  return "plato";
}

/**
 * SVG del platillo, listo para insertar. `clase` permite animarlo desde CSS.
 */
export function ilustracion(nombre, { clase = "" } = {}) {
  return `<svg class="ilustracion ${clase}" viewBox="0 0 160 120"
    preserveAspectRatio="xMidYMid slice" role="img" aria-hidden="true"
    focusable="false">${DIBUJOS[claveIlustracion(nombre)]}</svg>`;
}

export const CLAVES = Object.keys(DIBUJOS);
