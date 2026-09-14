import { api } from "../api.js";
import { carrito } from "../carrito.js";
import { sesion } from "../sesion.js";
import { ir } from "../router.js";
import { avisar, cargando, dinero, esc, vacio } from "../ui.js";
import { vistaMenuCliente } from "./menu_cliente.js";
import { icono } from "../iconos.js";

const IVA = 0.16; // solo para la vista previa; el total real lo calcula el backend

const bannerDestino = (orden) => `
  <div class="banner">
    ${icono("mesa", { tam: 18 })}
    <span>Agregando a <strong>${esc(orden.numero)}</strong>${
      orden.mesa ? ` · mesa ${orden.mesa}` : ""
    }. Entra como una tanda nueva y se cobra todo junto.</span>
    <span class="banner__acciones">
      <a class="btn btn--fantasma btn--sm" href="#/ordenes/${orden.id}">Ver la orden</a>
      <a class="btn btn--sm" href="#/menu">Orden nueva</a>
    </span>
  </div>`;

export async function vistaMenu(contenedor, opciones) {
  // El comensal ve la portada y la carta ilustrada; el personal conserva la
  // rejilla compacta, que es lo que necesita quien toma comandas todo el día.
  if (!sesion.esPersonal) return vistaMenuCliente(contenedor, opciones);
  return vistaMenuPersonal(contenedor, opciones);
}

async function vistaMenuPersonal(contenedor, { consulta }) {
  // #/menu?orden=5 -> en vez de crear una orden nueva, se le agregan platillos
  // a una mesa que ya esta abierta.
  const ordenDestinoId = consulta.get("orden");
  let ordenDestino = null;
  if (ordenDestinoId) {
    try {
      ordenDestino = await api.orden(ordenDestinoId);
      if (!ordenDestino.ampliable) {
        avisar(`La orden ${ordenDestino.numero} ya no admite platillos`);
        ordenDestino = null;
      }
    } catch (e) {
      avisar(e.message);
    }
  }

  contenedor.innerHTML = `
    ${ordenDestino ? bannerDestino(ordenDestino) : ""}
    <div class="encabezado">
      <div>
        <h1>Menú</h1>
        <p>${
          ordenDestino
            ? `Los platillos se suman a ${esc(ordenDestino.numero)}.`
            : "Arma la comanda y envíala a la cocina."
        }</p>
      </div>
      <div class="campo" style="margin:0;min-width:240px">
        <input id="buscador" type="search" placeholder="Buscar platillo…" aria-label="Buscar platillo">
      </div>
    </div>

    <div class="columnas">
      <div>
        <div class="chips" id="filtros" style="margin-bottom:20px"></div>
        <div id="productos">${cargando()}</div>
      </div>
      <aside id="carrito"></aside>
    </div>`;

  const pedido = {
    tipo: "LOCAL", mesa: "", nombre: "", telefono: "", direccion: "",
    metodo: "EFECTIVO", notas: "",
  };

  const $productos = document.getElementById("productos");
  const $filtros = document.getElementById("filtros");
  let categoriaActiva = null;
  let texto = "";
  let catalogo = [];

  // --- categorias ---
  let categorias = [];
  try {
    categorias = await api.categorias(true);
  } catch (e) {
    avisar(e.message);
  }

  const pintarFiltros = () => {
    $filtros.innerHTML = [
      `<button class="chip ${categoriaActiva === null ? "activo" : ""}" data-cat="">Todo</button>`,
      ...categorias.map(
        (c) =>
          `<button class="chip ${categoriaActiva === c.id ? "activo" : ""}" data-cat="${c.id}">${esc(c.nombre)}</button>`
      ),
    ].join("");
  };

  $filtros.addEventListener("click", (e) => {
    const boton = e.target.closest("[data-cat]");
    if (!boton) return;
    categoriaActiva = boton.dataset.cat ? Number(boton.dataset.cat) : null;
    pintarFiltros();
    cargarProductos();
  });

  // --- productos ---
  async function cargarProductos() {
    $productos.innerHTML = cargando();
    try {
      catalogo = await api.productos({ categoria_id: categoriaActiva, texto, limit: 200 });
    } catch (e) {
      $productos.innerHTML = vacio("alerta", "No se pudo cargar el menú", e.message);
      return;
    }
    if (!catalogo.length) {
      $productos.innerHTML = vacio("busqueda", "Sin resultados", "Prueba con otra búsqueda o categoría.");
      return;
    }
    $productos.innerHTML = `<div class="rejilla-productos">${catalogo.map(tarjeta).join("")}</div>`;
  }

  const tarjeta = (p) => `
    <article class="producto ${p.disponible ? "" : "producto--agotado"}">
      <span class="producto__cat">${esc(p.categoria.nombre)}</span>
      <h3 class="producto__nombre">${esc(p.nombre)}</h3>
      <p class="producto__desc">${esc(p.descripcion ?? "")}</p>
      <div class="producto__pie">
        <span class="producto__precio">${dinero(p.precio)}</span>
        <button class="agregar" data-add="${p.id}" ${p.disponible ? "" : "disabled"}
                aria-label="Agregar ${esc(p.nombre)}" title="${p.disponible ? "Agregar" : "No disponible"}">
          ${p.disponible ? "+" : "×"}
        </button>
      </div>
    </article>`;

  $productos.addEventListener("click", (e) => {
    const boton = e.target.closest("[data-add]");
    if (!boton) return;
    const producto = catalogo.find((p) => p.id === Number(boton.dataset.add));
    if (producto) {
      carrito.agregar(producto);
      pintarCarrito();
    }
  });

  let temporizador;
  document.getElementById("buscador").addEventListener("input", (e) => {
    texto = e.target.value.trim();
    clearTimeout(temporizador);
    temporizador = setTimeout(cargarProductos, 280);
  });

  // --- carrito ---
  const $carrito = document.getElementById("carrito");

  function pintarCarrito() {
    const lineas = carrito.lineas;
    const subtotal = carrito.subtotal;

    if (!lineas.length) {
      $carrito.innerHTML = `<div class="tarjeta carrito">
        ${vacio("recibo", "Comanda vacía", "Usa el + de un platillo para agregarlo.")}
      </div>`;
      return;
    }

    $carrito.innerHTML = `
      <div class="tarjeta carrito">
        <div class="carrito__titulo">
          <h2>Comanda</h2>
          <button class="btn--texto" id="vaciar" style="border:none;cursor:pointer">Vaciar</button>
        </div>

        <div class="carrito__lineas">
          ${lineas.map(lineaHtml).join("")}
        </div>

        <div class="totales">
          <div class="totales__fila"><span>Subtotal</span><span>${dinero(subtotal)}</span></div>
          <div class="totales__fila"><span>IVA 16%</span><span>${dinero(subtotal * IVA)}</span></div>
          <div class="totales__fila totales__fila--total">
            <span>Total</span><span>${dinero(subtotal * (1 + IVA))}</span>
          </div>
        </div>

        <div style="margin-top:20px">
          ${ordenDestino ? "" : sesion.esPersonal ? camposPersonal() : ""}
          ${
            ordenDestino
              ? ""
              : `<div class="campo">
                   <label for="notas">Notas para la cocina</label>
                   <textarea id="notas" data-campo="notas"
                     placeholder="Alergias, tiempos, etc.">${esc(pedido.notas)}</textarea>
                 </div>`
          }
          <button class="btn btn--bloque" id="enviar">${
            ordenDestino ? `Agregar a ${esc(ordenDestino.numero)}` : "Enviar a cocina"
          }</button>
        </div>
      </div>`;

    document.getElementById("vaciar").addEventListener("click", () => {
      carrito.vaciar();
      pintarCarrito();
    });

    $carrito.querySelectorAll("[data-mas],[data-menos],[data-quitar]").forEach((boton) => {
      boton.addEventListener("click", () => {
        const id = Number(boton.dataset.mas ?? boton.dataset.menos ?? boton.dataset.quitar);
        if (boton.dataset.quitar) carrito.quitar(id);
        else carrito.cambiarCantidad(id, boton.dataset.mas ? 1 : -1);
        pintarCarrito();
      });
    });

    // Cada tecleo se guarda; cambiar el tipo repinta los campos que aplican.
    $carrito.querySelectorAll("[data-campo]").forEach((campo) => {
      const guardar = () => {
        pedido[campo.dataset.campo] = campo.value;
      };
      // Los dos eventos: un <select> no siempre emite "input", y un <input>
      // de texto no emite "change" hasta perder el foco.
      campo.addEventListener("input", guardar);
      campo.addEventListener("change", guardar);
      if (campo.dataset.campo === "tipo") {
        campo.addEventListener("change", () => {
          guardar();
          pintarCarrito();
        });
      }
    });

    document.getElementById("enviar").addEventListener("click", enviarOrden);
  }

  const lineaHtml = (l) => `
    <div class="linea">
      <span class="linea__nombre">${esc(l.nombre)}</span>
      <span class="linea__importe">${dinero(Number(l.precio) * l.cantidad)}</span>
      ${l.notas ? `<span class="linea__notas">“${esc(l.notas)}”</span>` : ""}
      <div class="linea__control">
        <div class="contador">
          <button data-menos="${l.producto_id}" aria-label="Quitar uno">−</button>
          <span>${l.cantidad}</span>
          <button data-mas="${l.producto_id}" aria-label="Agregar uno">+</button>
        </div>
        <button class="btn--texto" data-quitar="${l.producto_id}"
                style="border:none;cursor:pointer;font-size:.8rem">Quitar</button>
      </div>
    </div>`;

  /**
   * Un pedido que sale del restaurante necesita a quién buscar y cómo va a
   * pagar; el backend lo exige. En una mesa basta el número.
   *
   * Lo tecleado vive en `pedido` y no en el DOM, porque el carrito repinta
   * este bloque cada vez que cambia.
   */
  /**
   * Vuelca al estado lo que haya ahora mismo en los campos.
   *
   * El estado se alimenta de los eventos del usuario, pero un valor puesto por
   * código —el autocompletado del navegador, por ejemplo— no dispara ninguno.
   * Al enviar, lo que manda es el DOM.
   */
  const sincronizarCampos = (raiz) => {
    raiz.querySelectorAll("[data-campo]").forEach((campo) => {
      pedido[campo.dataset.campo] = campo.value;
    });
  };

  const camposPersonal = () => {
    const fuera = pedido.tipo !== "LOCAL";
    return `
      <div class="rejilla-campos">
        <div class="campo">
          <label for="tipo">Tipo</label>
          <select id="tipo" data-campo="tipo">
            <option value="LOCAL" ${pedido.tipo === "LOCAL" ? "selected" : ""}>En el local</option>
            <option value="PARA_LLEVAR" ${pedido.tipo === "PARA_LLEVAR" ? "selected" : ""}>Para llevar</option>
            <option value="DOMICILIO" ${pedido.tipo === "DOMICILIO" ? "selected" : ""}>A domicilio</option>
          </select>
        </div>
        <div class="campo">
          <label for="mesa">Mesa</label>
          <input id="mesa" data-campo="mesa" type="number" min="1" max="200"
                 value="${esc(pedido.mesa)}" placeholder="Nº" ${fuera ? "disabled" : ""}>
        </div>
      </div>

      ${
        fuera
          ? `<div class="entrega">
               <p class="entrega__titulo">Datos de quien recoge</p>
               <div class="campo">
                 <label for="nombre">Nombre</label>
                 <input id="nombre" data-campo="nombre" value="${esc(pedido.nombre)}" placeholder="A nombre de">
               </div>
               <div class="campo">
                 <label for="telefono">Teléfono</label>
                 <input id="telefono" data-campo="telefono" type="tel"
                        value="${esc(pedido.telefono)}" placeholder="999 000 0000">
               </div>
               ${
                 pedido.tipo === "DOMICILIO"
                   ? `<div class="campo">
                        <label for="direccion">Domicilio</label>
                        <textarea id="direccion" data-campo="direccion"
                          placeholder="Calle, número, colonia y referencias">${esc(pedido.direccion)}</textarea>
                      </div>`
                   : ""
               }
               <div class="campo">
                 <label for="metodo">Pagará con</label>
                 <select id="metodo" data-campo="metodo">
                   <option value="EFECTIVO" ${pedido.metodo === "EFECTIVO" ? "selected" : ""}>Efectivo</option>
                   <option value="TARJETA" ${pedido.metodo === "TARJETA" ? "selected" : ""}>Tarjeta</option>
                   <option value="TRANSFERENCIA" ${pedido.metodo === "TRANSFERENCIA" ? "selected" : ""}>Transferencia</option>
                 </select>
               </div>
             </div>`
          : ""
      }`;
  };

  async function enviarOrden() {
    const boton = document.getElementById("enviar");
    const textoOriginal = boton.textContent;
    boton.disabled = true;
    boton.textContent = "Enviando…";

    try {
      const orden = ordenDestino ? await sumarADestino() : await crearNueva();
      if (!orden) return;
      carrito.vaciar();
      avisar(
        ordenDestino
          ? `Platillos agregados a ${orden.numero}`
          : `Orden ${orden.numero} enviada a cocina`,
        "ok"
      );
      ir(`/ordenes/${orden.id}`);
    } catch (e) {
      avisar(e.message);
      boton.disabled = false;
      boton.textContent = textoOriginal;
    }
  }

  async function crearNueva() {
    sincronizarCampos($carrito);
    const fuera = pedido.tipo !== "LOCAL";

    if (!fuera && !pedido.mesa) {
      avisar("Indica el número de mesa para una orden en el local");
      const boton = document.getElementById("enviar");
      boton.disabled = false;
      boton.textContent = "Enviar a cocina";
      return null;
    }
    return api.crearOrden({
      tipo: pedido.tipo,
      mesa: !fuera && pedido.mesa ? Number(pedido.mesa) : null,
      notas: pedido.notas.trim() || null,
      items: carrito.aItems(),
      contacto_nombre: fuera ? pedido.nombre.trim() || null : null,
      contacto_telefono: fuera ? pedido.telefono.trim() || null : null,
      contacto_direccion: pedido.tipo === "DOMICILIO" ? pedido.direccion.trim() || null : null,
      metodo_pago_preferido: fuera ? pedido.metodo : null,
    });
  }

  /** Los items se mandan de uno en uno; el backend los agrupa en la misma tanda. */
  async function sumarADestino() {
    let orden = ordenDestino;
    for (const item of carrito.aItems()) {
      orden = await api.agregarItem(ordenDestino.id, item);
    }
    return orden;
  }

  pintarFiltros();
  pintarCarrito();
  await cargarProductos();
}
