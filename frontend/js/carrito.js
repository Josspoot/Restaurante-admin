/**
 * Carrito de la orden en construccion. Vive en localStorage para que no se
 * pierda al recargar, y avisa a quien lo escuche cuando cambia.
 */
const CLAVE = "sabor.carrito";
const oyentes = new Set();

function leer() {
  try {
    return JSON.parse(localStorage.getItem(CLAVE) ?? "[]");
  } catch {
    return [];
  }
}

function escribir(lineas) {
  try {
    localStorage.setItem(CLAVE, JSON.stringify(lineas));
  } catch {
    /* modo privado */
  }
  oyentes.forEach((fn) => fn(lineas));
}

export const carrito = {
  get lineas() {
    return leer();
  },

  /** Total de piezas, para el contador de la cabecera. */
  get piezas() {
    return leer().reduce((suma, l) => suma + l.cantidad, 0);
  },

  /** Subtotal sin impuestos; el total real siempre lo calcula el backend. */
  get subtotal() {
    return leer().reduce((suma, l) => suma + Number(l.precio) * l.cantidad, 0);
  },

  agregar(producto, cantidad = 1) {
    const lineas = leer();
    const existente = lineas.find((l) => l.producto_id === producto.id && !l.notas);
    if (existente) existente.cantidad += cantidad;
    else
      lineas.push({
        producto_id: producto.id,
        nombre: producto.nombre,
        precio: producto.precio,
        cantidad,
        notas: "",
      });
    escribir(lineas);
  },

  cambiarCantidad(productoId, delta) {
    const lineas = leer();
    const linea = lineas.find((l) => l.producto_id === productoId);
    if (!linea) return;
    linea.cantidad += delta;
    escribir(linea.cantidad <= 0 ? lineas.filter((l) => l !== linea) : lineas);
  },

  anotar(productoId, notas) {
    const lineas = leer();
    const linea = lineas.find((l) => l.producto_id === productoId);
    if (linea) {
      linea.notas = notas;
      escribir(lineas);
    }
  },

  quitar(productoId) {
    escribir(leer().filter((l) => l.producto_id !== productoId));
  },

  vaciar() {
    escribir([]);
  },

  /** Convierte el carrito al formato que espera POST /ordenes. */
  aItems() {
    return leer().map((l) => ({
      producto_id: l.producto_id,
      cantidad: l.cantidad,
      notas: l.notas || null,
    }));
  },

  alCambiar(fn) {
    oyentes.add(fn);
    return () => oyentes.delete(fn);
  },
};
