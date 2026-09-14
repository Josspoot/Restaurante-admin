/**
 * Menú en su versión para el comensal.
 *
 * El personal sigue usando la rejilla compacta de siempre: quien toma
 * comandas todo el día necesita densidad, no una portada. Esta vista es lo
 * contrario — entra por los ojos, presenta la carta y acompaña el pedido.
 */
import { api } from "../api.js";
import { carrito } from "../carrito.js";
import { ir } from "../router.js";
import { icono } from "../iconos.js";
import { ilustracion } from "../ilustraciones.js";
import { avisar, cargando, dinero, esc, vacio } from "../ui.js";

const IVA = 0.16;            // solo para la vista previa; el total lo calcula el backend
const MS_POR_DIAPOSITIVA = 3000;
const MAX_DESTACADOS = 5;

const sinMovimiento = () =>
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;

export async function vistaMenuCliente(contenedor, { consulta } = {}) {
  contenedor.innerHTML = cargando();

  // #/menu?orden=5 llega desde "Agregar platillos" en una orden abierta: los
  // platillos se suman a esa mesa en vez de abrir un pedido nuevo.
  let ordenDestino = null;
  const destinoId = consulta?.get("orden");
  if (destinoId) {
    try {
      const orden = await api.orden(destinoId);
      if (orden.ampliable) ordenDestino = orden;
      else avisar(`La orden ${orden.numero} ya no admite platillos`);
    } catch (e) {
      avisar(e.message);
    }
  }

  let categorias = [];
  let productos = [];
  try {
    [categorias, productos] = await Promise.all([
      api.categorias(true),
      api.productos({ disponible: true, limit: 200 }),
    ]);
  } catch (e) {
    contenedor.innerHTML = vacio("alerta", "No se pudo cargar el menú", e.message);
    return;
  }

  if (!productos.length) {
    contenedor.innerHTML = vacio("carta", "El menú está vacío", "Vuelve en un rato.");
    return;
  }

  // Recursos que hay que soltar al cambiar de vista.
  const limpiadores = [];
  const alSalir = () => {
    limpiadores.forEach((fn) => fn());
    window.removeEventListener("hashchange", alSalir);
  };
  window.addEventListener("hashchange", alSalir);

  const destacados = elegirDestacados(productos, categorias);

  contenedor.innerHTML = `
    ${ordenDestino ? avisoDestino(ordenDestino) : ""}
    ${portada(destacados)}
    ${carta(productos, categorias)}
    ${botonTicket()}`;

  montarPortada(destacados, limpiadores);
  montarRevelado(limpiadores);
  montarAgregar();
  montarTicket(limpiadores, ordenDestino);
}

/** Un platillo por categoría, para que la portada no repita el mismo tipo. */
function elegirDestacados(productos, categorias) {
  const porCategoria = new Map();
  for (const p of productos) {
    if (!porCategoria.has(p.categoria.id)) porCategoria.set(p.categoria.id, p);
  }
  const orden = categorias.map((c) => c.id).filter((id) => porCategoria.has(id));
  const elegidos = orden.map((id) => porCategoria.get(id));
  return (elegidos.length ? elegidos : productos).slice(0, MAX_DESTACADOS);
}

const avisoDestino = (orden) => `
  <div class="banner">
    ${icono("mesa", { tam: 18 })}
    <span>Estos platillos se suman a <strong>${esc(orden.numero)}</strong>${
      orden.mesa ? ` · mesa ${orden.mesa}` : ""
    }, y todo se cobra junto.</span>
    <span class="banner__acciones">
      <a class="btn btn--fantasma btn--sm" href="#/ordenes/${orden.id}">Ver mi orden</a>
      <a class="btn btn--sm" href="#/menu">Pedido nuevo</a>
    </span>
  </div>`;

// ================================================================== portada

const portada = (destacados) => `
  <section class="portada" id="portada" aria-roledescription="carrusel" aria-label="Platillos destacados">
    <div class="portada__marco">
      <div class="portada__pista" id="pista">
        ${destacados.map(diapositiva).join("")}
      </div>

      <button class="portada__flecha portada__flecha--izq" data-mover="-1" aria-label="Anterior">
        ${icono("flechaIzq", { tam: 18 })}
      </button>
      <button class="portada__flecha portada__flecha--der" data-mover="1" aria-label="Siguiente">
        ${icono("flechaIzq", { tam: 18 })}
      </button>

      <div class="portada__puntos" id="puntos" role="tablist">
        ${destacados
          .map(
            (p, i) => `<button class="punto ${i === 0 ? "punto--activo" : ""}" data-ir="${i}"
                         role="tab" aria-label="Ver ${esc(p.nombre)}"></button>`
          )
          .join("")}
      </div>
    </div>

    <p class="portada__pista-scroll" id="pista-scroll">
      Desliza para ver la carta completa
      <span class="portada__flecha-abajo"></span>
    </p>
  </section>`;

const diapositiva = (p) => `
  <article class="diapo">
    <div class="diapo__arte">${ilustracion(p.nombre)}</div>
    <div class="diapo__texto">
      <span class="diapo__categoria">${esc(p.categoria.nombre)}</span>
      <h2 class="diapo__nombre">${esc(p.nombre)}</h2>
      <p class="diapo__desc">${esc(p.descripcion ?? "")}</p>
      <div class="diapo__pie">
        <span class="diapo__precio">${dinero(p.precio)}</span>
        <button class="btn" data-agregar="${p.id}">Agregar</button>
      </div>
    </div>
  </article>`;

function montarPortada(destacados, limpiadores) {
  const pista = document.getElementById("pista");
  const puntos = [...document.querySelectorAll("[data-ir]")];
  const portadaEl = document.getElementById("portada");
  let actual = 0;
  let temporizador = null;

  const mostrar = (i) => {
    actual = (i + destacados.length) % destacados.length;
    pista.style.transform = `translateX(-${actual * 100}%)`;
    puntos.forEach((p, n) => p.classList.toggle("punto--activo", n === actual));
  };

  const arrancar = () => {
    if (sinMovimiento() || destacados.length < 2) return;
    detener();
    temporizador = setInterval(() => mostrar(actual + 1), MS_POR_DIAPOSITIVA);
  };
  const detener = () => clearInterval(temporizador);

  document.querySelectorAll("[data-mover]").forEach((b) =>
    b.addEventListener("click", () => {
      mostrar(actual + Number(b.dataset.mover));
      arrancar(); // reinicia la cuenta tras una acción manual
    })
  );
  puntos.forEach((p) =>
    p.addEventListener("click", () => {
      mostrar(Number(p.dataset.ir));
      arrancar();
    })
  );

  // Parar mientras el cursor está encima o el foco dentro: nada más molesto
  // que una portada que cambia justo cuando vas a pulsar.
  portadaEl.addEventListener("pointerenter", detener);
  portadaEl.addEventListener("pointerleave", arrancar);
  portadaEl.addEventListener("focusin", detener);
  portadaEl.addEventListener("focusout", arrancar);

  // Y también cuando la pestaña no se ve, para no gastar batería.
  const alCambiarVisibilidad = () => (document.hidden ? detener() : arrancar());
  document.addEventListener("visibilitychange", alCambiarVisibilidad);

  // La portada se desvanece conforme se baja: deja el protagonismo a la carta.
  let pendiente = false;
  const alHacerScroll = () => {
    if (pendiente) return;
    pendiente = true;
    requestAnimationFrame(() => {
      pendiente = false;
      const alto = portadaEl.offsetHeight || 1;
      const avance = Math.min(1, Math.max(0, window.scrollY / alto));
      portadaEl.style.setProperty("--salida", avance.toFixed(3));
    });
  };
  window.addEventListener("scroll", alHacerScroll, { passive: true });

  arrancar();
  limpiadores.push(() => {
    detener();
    document.removeEventListener("visibilitychange", alCambiarVisibilidad);
    window.removeEventListener("scroll", alHacerScroll);
  });
}

// ==================================================================== carta

function carta(productos, categorias) {
  const conProductos = categorias.filter((c) => productos.some((p) => p.categoria.id === c.id));
  const grupos = conProductos.length
    ? conProductos.map((c) => [c.nombre, productos.filter((p) => p.categoria.id === c.id)])
    : [["Menú", productos]];

  return `
    <div class="carta" id="carta">
      ${grupos
        .map(
          ([nombre, lista]) => `
          <section class="carta__grupo">
            <h2 class="carta__titulo revelable">${esc(nombre)}</h2>
            <div class="carta__rejilla">
              ${lista.map((p, i) => tarjetaPlatillo(p, i)).join("")}
            </div>
          </section>`
        )
        .join("")}
    </div>`;
}

const tarjetaPlatillo = (p, i) => `
  <article class="platillo revelable" style="--retraso:${Math.min(i, 5) * 60}ms">
    <div class="platillo__arte" data-arte="${p.id}">${ilustracion(p.nombre)}</div>
    <div class="platillo__cuerpo">
      <h3 class="platillo__nombre">${esc(p.nombre)}</h3>
      <p class="platillo__desc">${esc(p.descripcion ?? "")}</p>
      <div class="platillo__pie">
        <span class="platillo__precio">${dinero(p.precio)}</span>
        <button class="agregar" data-agregar="${p.id}" aria-label="Agregar ${esc(p.nombre)}">
          ${icono("mas", { tam: 18 })}
        </button>
      </div>
    </div>
  </article>`;

/** Las tarjetas entran cuando aparecen en pantalla, no todas de golpe. */
function montarRevelado(limpiadores) {
  const objetivos = document.querySelectorAll(".revelable");
  if (sinMovimiento() || !("IntersectionObserver" in window)) {
    objetivos.forEach((n) => n.classList.add("revelado"));
    return;
  }
  const observador = new IntersectionObserver(
    (entradas) => {
      for (const entrada of entradas) {
        if (!entrada.isIntersecting) continue;
        entrada.target.classList.add("revelado");
        observador.unobserve(entrada.target); // se revela una sola vez
      }
    },
    { rootMargin: "0px 0px -12% 0px", threshold: 0.1 }
  );
  objetivos.forEach((n) => observador.observe(n));
  limpiadores.push(() => observador.disconnect());
}

// =================================================================== ticket

const botonTicket = () => `
  <button class="ticket-flotante" id="ticket-flotante" aria-label="Ver mi ticket">
    ${icono("recibo", { tam: 22 })}
    <span class="ticket-flotante__conteo" id="ticket-conteo" hidden>0</span>
  </button>
  <div class="ticket-panel" id="ticket-panel" hidden aria-label="Mi ticket"></div>`;

function montarAgregar() {
  document.querySelectorAll("[data-agregar]").forEach((boton) =>
    boton.addEventListener("click", async () => {
      const id = Number(boton.dataset.agregar);
      let producto;
      try {
        producto = await api.producto(id);
      } catch (e) {
        return avisar(e.message);
      }
      const arte = document.querySelector(`[data-arte="${id}"]`) ?? boton;
      volarAlTicket(arte);
      carrito.agregar(producto);
    })
  );
}

/**
 * El platillo "vuela" desde su tarjeta hasta el ticket.
 *
 * Es una copia suelta en posición fija: así se puede animar por encima de
 * todo sin alterar la maquetación de la tarjeta original.
 */
function volarAlTicket(origen) {
  const destino = document.getElementById("ticket-flotante");
  if (!destino || sinMovimiento() || !origen.animate) return latir(destino);

  const desde = origen.getBoundingClientRect();
  const hasta = destino.getBoundingClientRect();

  const copia = document.createElement("div");
  copia.className = "volador";
  copia.innerHTML = origen.innerHTML;
  Object.assign(copia.style, {
    left: `${desde.left}px`,
    top: `${desde.top}px`,
    width: `${desde.width}px`,
    height: `${desde.height}px`,
  });
  document.body.append(copia);

  const dx = hasta.left + hasta.width / 2 - (desde.left + desde.width / 2);
  const dy = hasta.top + hasta.height / 2 - (desde.top + desde.height / 2);

  const animacion = copia.animate(
    [
      { transform: "translate(0,0) scale(1)", opacity: 1 },
      { transform: `translate(${dx * 0.55}px, ${dy * 0.35 - 70}px) scale(.7)`, opacity: .95, offset: .55 },
      { transform: `translate(${dx}px, ${dy}px) scale(.12)`, opacity: 0 },
    ],
    { duration: 720, easing: "cubic-bezier(.45,0,.2,1)" }
  );
  animacion.onfinish = () => {
    copia.remove();
    latir(destino);
  };
}

function latir(nodo) {
  nodo.classList.remove("ticket-flotante--late");
  void nodo.offsetWidth; // reinicia la animación
  nodo.classList.add("ticket-flotante--late");
}

function montarTicket(limpiadores, ordenDestino) {
  const boton = document.getElementById("ticket-flotante");
  const panel = document.getElementById("ticket-panel");
  const conteo = document.getElementById("ticket-conteo");
  let abierto = false;

  const pintarConteo = () => {
    const piezas = carrito.piezas;
    conteo.hidden = piezas === 0;
    conteo.textContent = piezas;
    boton.classList.toggle("ticket-flotante--lleno", piezas > 0);
  };

  const pintarPanel = () => {
    if (!abierto) return;
    const lineas = carrito.lineas;
    const subtotal = carrito.subtotal;

    panel.innerHTML = `
      <div class="ticket-panel__cabecera">
        <h2>Mi ticket</h2>
        <button class="modal__cerrar" id="ticket-cerrar" aria-label="Cerrar">
          ${icono("cerrar", { tam: 18 })}
        </button>
      </div>

      ${
        lineas.length
          ? `${
              ordenDestino
                ? `<p class="ticket-panel__destino">Se agregará a ${esc(ordenDestino.numero)}</p>`
                : ""
            }
             <div class="ticket-panel__lineas">
               ${lineas.map(lineaTicket).join("")}
             </div>

             <div class="totales">
               <div class="totales__fila"><span>Subtotal</span><span>${dinero(subtotal)}</span></div>
               <div class="totales__fila"><span>IVA 16%</span><span>${dinero(subtotal * IVA)}</span></div>
               <div class="totales__fila totales__fila--total">
                 <span>Total</span><span>${dinero(subtotal * (1 + IVA))}</span>
               </div>
             </div>

             ${
               ordenDestino
                 ? ""
                 : `<div class="rejilla-campos" style="margin-top:18px">
                      <div class="campo">
                        <label for="tipo">¿Cómo lo quieres?</label>
                        <select id="tipo">
                          <option value="LOCAL">Comer aquí</option>
                          <option value="PARA_LLEVAR">Para llevar</option>
                        </select>
                      </div>
                      <div class="campo">
                        <label for="mesa">Mesa <span style="font-weight:400">(opcional)</span></label>
                        <input id="mesa" type="number" min="1" max="200" placeholder="Nº">
                      </div>
                    </div>
                    <div class="campo">
                      <label for="notas">Notas para la cocina</label>
                      <textarea id="notas" placeholder="Alergias, sin cebolla, etc."></textarea>
                    </div>`
             }

             <button class="btn btn--bloque" id="ticket-enviar">${
               ordenDestino ? `Agregar a ${esc(ordenDestino.numero)}` : "Enviar mi pedido"
             }</button>
             <button class="btn--texto" id="ticket-vaciar"
                     style="border:none;cursor:pointer;width:100%;margin-top:8px">Vaciar</button>`
          : vacio("recibo", "Tu ticket está vacío", "Agrega platillos desde la carta.")
      }`;

    document.getElementById("ticket-cerrar").addEventListener("click", cerrar);
    if (!lineas.length) return;

    panel.querySelectorAll("[data-mas],[data-menos],[data-quitar]").forEach((b) =>
      b.addEventListener("click", () => {
        const id = Number(b.dataset.mas ?? b.dataset.menos ?? b.dataset.quitar);
        if (b.dataset.quitar) carrito.quitar(id);
        else carrito.cambiarCantidad(id, b.dataset.mas ? 1 : -1);
      })
    );
    document.getElementById("ticket-vaciar").addEventListener("click", () => carrito.vaciar());
    document.getElementById("ticket-enviar").addEventListener("click", enviar);
  };

  const lineaTicket = (l) => `
    <div class="linea">
      <span class="linea__nombre">${esc(l.nombre)}</span>
      <span class="linea__importe">${dinero(Number(l.precio) * l.cantidad)}</span>
      <div class="linea__control">
        <div class="contador">
          <button data-menos="${l.producto_id}" aria-label="Quitar uno">${icono("menos", { tam: 14 })}</button>
          <span>${l.cantidad}</span>
          <button data-mas="${l.producto_id}" aria-label="Agregar uno">${icono("mas", { tam: 14 })}</button>
        </div>
        <button class="btn--texto" data-quitar="${l.producto_id}"
                style="border:none;cursor:pointer;font-size:.8rem">Quitar</button>
      </div>
    </div>`;

  async function enviar() {
    const boton = document.getElementById("ticket-enviar");
    const textoOriginal = boton.textContent;
    boton.disabled = true;
    boton.textContent = "Enviando…";
    try {
      let orden;
      if (ordenDestino) {
        // Uno por uno: el backend los agrupa en la misma tanda.
        for (const item of carrito.aItems()) {
          orden = await api.agregarItem(ordenDestino.id, item);
        }
      } else {
        const mesa = document.getElementById("mesa").value;
        orden = await api.crearOrden({
          tipo: document.getElementById("tipo").value,
          mesa: mesa ? Number(mesa) : null,
          notas: document.getElementById("notas").value.trim() || null,
          items: carrito.aItems(),
        });
      }
      carrito.vaciar();
      cerrar();
      avisar(
        ordenDestino ? `Platillos agregados a ${orden.numero}` : `Pedido ${orden.numero} enviado a cocina`,
        "ok"
      );
      ir(`/ordenes/${orden.id}`);
    } catch (e) {
      avisar(e.message);
      boton.disabled = false;
      boton.textContent = textoOriginal;
    }
  }

  const abrir = () => {
    abierto = true;
    panel.hidden = false;
    pintarPanel();
    requestAnimationFrame(() => panel.classList.add("ticket-panel--abierto"));
  };
  const cerrar = () => {
    abierto = false;
    panel.classList.remove("ticket-panel--abierto");
    setTimeout(() => (panel.hidden = !abierto), 220);
  };

  boton.addEventListener("click", () => (abierto ? cerrar() : abrir()));

  const alTeclado = (e) => e.key === "Escape" && abierto && cerrar();
  document.addEventListener("keydown", alTeclado);

  const dejarDeEscuchar = carrito.alCambiar(() => {
    pintarConteo();
    pintarPanel();
  });

  pintarConteo();
  limpiadores.push(() => {
    dejarDeEscuchar();
    document.removeEventListener("keydown", alTeclado);
  });
}
