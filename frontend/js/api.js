/**
 * Cliente HTTP de la API. Unico lugar del front que sabe hacer fetch.
 */
import { sesion } from "./sesion.js";

function baseUrl() {
  if (window.API_BASE) return window.API_BASE;
  // Si el front lo sirve el propio FastAPI, la API vive en el mismo origen.
  if (location.protocol.startsWith("http")) return `${location.origin}/api/v1`;
  return "http://127.0.0.1:8000/api/v1";
}

export class ErrorApi extends Error {
  constructor(mensaje, estado, cuerpo) {
    super(mensaje);
    this.estado = estado;
    this.cuerpo = cuerpo;
  }
}

async function pedir(ruta, { metodo = "GET", cuerpo, publico = false } = {}) {
  const cabeceras = {};
  if (cuerpo !== undefined) cabeceras["Content-Type"] = "application/json";
  if (!publico && sesion.token) cabeceras["Authorization"] = `Bearer ${sesion.token}`;

  let respuesta;
  try {
    respuesta = await fetch(baseUrl() + ruta, {
      method: metodo,
      headers: cabeceras,
      body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo),
    });
  } catch {
    throw new ErrorApi("No se pudo conectar con el servidor. ¿Está corriendo la API?", 0);
  }

  if (respuesta.status === 204) return null;

  const datos = await respuesta.json().catch(() => null);

  if (!respuesta.ok) {
    // El token murio: cerramos sesion y mandamos al login.
    if (respuesta.status === 401 && sesion.token) {
      sesion.cerrar();
      location.hash = "#/login";
    }
    throw new ErrorApi(mensajeDeError(datos, respuesta.status), respuesta.status, datos);
  }
  return datos;
}

/** Traduce el cuerpo de error de FastAPI a una frase legible. */
function mensajeDeError(datos, estado) {
  if (!datos) return `Error ${estado}`;
  if (typeof datos.detalle === "string") return datos.detalle;          // error de dominio
  if (typeof datos.detail === "string") return datos.detail;            // HTTPException
  if (Array.isArray(datos.detail)) {                                    // validacion 422
    return datos.detail
      .map((e) => `${e.loc?.slice(1).join(".") ?? "campo"}: ${e.msg}`)
      .join(" · ");
  }
  return `Error ${estado}`;
}

/**
 * Codifica un id antes de meterlo en la ruta.
 *
 * Sin esto, un valor como "../../auth/yo" en el hash cambiaría el endpoint al
 * que se llama. No es un agujero grave porque todo va al mismo origen y con el
 * mismo token, pero llamar a una ruta distinta de la esperada nunca es correcto.
 */
const seg = (valor) => encodeURIComponent(String(valor));

const qs = (obj) => {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(obj)) {
    if (v !== undefined && v !== null && v !== "") p.set(k, v);
  }
  const s = p.toString();
  return s ? `?${s}` : "";
};

export const api = {
  /** Estado del servidor. Público: no necesita token. */
  salud: () => pedir("/salud", { publico: true }),

  // --- autenticacion ---
  login: (email, password) =>
    pedir("/auth/login-json", { metodo: "POST", cuerpo: { email, password }, publico: true }),
  registro: (datos) => pedir("/auth/registro", { metodo: "POST", cuerpo: datos, publico: true }),
  yo: () => pedir("/auth/yo"),
  crearUsuario: (datos) => pedir("/auth/usuarios", { metodo: "POST", cuerpo: datos }),

  // --- menu ---
  categorias: (soloActivas = false) => pedir(`/categorias${qs({ solo_activas: soloActivas })}`),
  crearCategoria: (datos) => pedir("/categorias", { metodo: "POST", cuerpo: datos }),
  editarCategoria: (id, datos) => pedir(`/categorias/${seg(id)}`, { metodo: "PATCH", cuerpo: datos }),
  borrarCategoria: (id) => pedir(`/categorias/${seg(id)}`, { metodo: "DELETE" }),

  productos: (filtros = {}) => pedir(`/productos${qs(filtros)}`),
  producto: (id) => pedir(`/productos/${seg(id)}`),
  crearProducto: (datos) => pedir("/productos", { metodo: "POST", cuerpo: datos }),
  editarProducto: (id, datos) => pedir(`/productos/${seg(id)}`, { metodo: "PATCH", cuerpo: datos }),
  borrarProducto: (id) => pedir(`/productos/${seg(id)}`, { metodo: "DELETE" }),

  // --- ordenes ---
  ordenes: (filtros = {}) => pedir(`/ordenes${qs(filtros)}`),
  orden: (id) => pedir(`/ordenes/${seg(id)}`),
  crearOrden: (datos) => pedir("/ordenes", { metodo: "POST", cuerpo: datos }),
  agregarItem: (id, item) => pedir(`/ordenes/${seg(id)}/items`, { metodo: "POST", cuerpo: item }),
  quitarItem: (id, itemId) => pedir(`/ordenes/${seg(id)}/items/${seg(itemId)}`, { metodo: "DELETE" }),
  cambiarEstado: (id, estado) => pedir(`/ordenes/${seg(id)}/estado`, { metodo: "PATCH", cuerpo: { estado } }),
  cancelar: (id) => pedir(`/ordenes/${seg(id)}/cancelar`, { metodo: "POST" }),
  cerrar: (id) => pedir(`/ordenes/${seg(id)}/cerrar`, { metodo: "POST" }),
  reabrir: (id) => pedir(`/ordenes/${seg(id)}/reabrir`, { metodo: "POST" }),
  avisos: () => pedir("/ordenes/avisos"),
  pagar: (id, pago) => pedir(`/ordenes/${seg(id)}/pagos`, { metodo: "POST", cuerpo: pago }),
  factura: (id, cuenta = null) => pedir(`/ordenes/${seg(id)}/factura${qs({ cuenta })}`),

  // --- tandas y cuentas ---
  cocina: () => pedir("/ordenes/cocina"),
  tandas: (id) => pedir(`/ordenes/${seg(id)}/tandas`),
  cambiarEstadoTanda: (id, tanda, estado) =>
    pedir(`/ordenes/${seg(id)}/tandas/${seg(tanda)}/estado`, { metodo: "PATCH", cuerpo: { estado } }),
  cuentas: (id) => pedir(`/ordenes/${seg(id)}/cuentas`),
  asignarCuenta: (id, itemId, cuenta) =>
    pedir(`/ordenes/${seg(id)}/items/${seg(itemId)}/cuenta`, { metodo: "PATCH", cuerpo: { cuenta } }),
};
