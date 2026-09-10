import { api } from "../api.js";
import { sesion } from "../sesion.js";
import {
  ETIQUETA_ESTADO, ETIQUETA_METODO, ETIQUETA_TIPO,
  avisar, cargando, confirmar, dinero, esc, fechaHora, hora,
  insigniaEstado, insigniaItem, modal,
} from "../ui.js";
import { icono } from "../iconos.js";

// Mismo grafo de estados que aplica el backend: la interfaz solo ofrece
// los botones que el servidor va a aceptar.
const TRANSICIONES = {
  PENDIENTE: ["EN_PREPARACION", "CANCELADA"],
  EN_PREPARACION: ["LISTA", "CANCELADA"],
  LISTA: ["ENTREGADA", "CANCELADA"],
  ENTREGADA: [],
  CANCELADA: [],
};

const FLUJO = ["PENDIENTE", "EN_PREPARACION", "LISTA", "ENTREGADA"];
const PORCENTAJES_PROPINA = [10, 15, 20];

export async function vistaOrdenDetalle(contenedor, { id }) {
  contenedor.innerHTML = cargando();

  let orden;
  let cuentas = [];

  async function recargar() {
    [orden, cuentas] = await Promise.all([api.orden(id), api.cuentas(id)]);
  }

  try {
    await recargar();
  } catch (e) {
    contenedor.innerHTML = `<div class="vacio">
        <div class="vacio__icono">${icono("alerta", { tam: 34 })}</div>
        <h3>No se pudo abrir la orden</h3><p>${esc(e.message)}</p>
        <p style="margin-top:16px"><a class="btn btn--fantasma" href="#/ordenes">Volver a órdenes</a></p>
      </div>`;
    return;
  }

  /** Vuelve a pedir los datos al servidor y repinta. */
  async function refrescar() {
    await recargar();
    pintar();
  }

  // -------------------------------------------------------------- estructura

  function pintar() {
    const dividida = cuentas.length > 1;
    contenedor.innerHTML = `
      <p style="margin-bottom:16px">
        <a class="btn--texto" href="#/ordenes" style="padding-left:0;display:inline-flex;align-items:center;gap:6px">${icono("flechaIzq", { tam: 16 })} Órdenes</a>
      </p>

      <div class="orden-cabecera">
        <div>
          <h1>${esc(orden.numero)}</h1>
          <div class="orden-cabecera__meta">
            ${dato("Tipo", ETIQUETA_TIPO[orden.tipo] ?? orden.tipo)}
            ${dato("Mesa", orden.mesa ?? "—")}
            ${dato("Cliente", orden.cliente?.nombre ?? "Público general")}
            ${orden.mesero ? dato("Atendió", orden.mesero.nombre) : ""}
            ${dato("Abierta", fechaHora(orden.creado_en))}
            ${dato("Cuentas", dividida ? `${cuentas.length} (dividida)` : "1")}
          </div>
        </div>
        <div style="text-align:right">
          ${insigniaEstado(orden.estado)}
          ${orden.cerrada ? `<span class="insignia insignia--cerrada">Mesa cerrada</span>` : ""}
          <div style="font-size:1.7rem;font-weight:700;margin-top:8px">${dinero(orden.total)}</div>
          ${
            orden.estado === "CANCELADA"
              ? ""
              : orden.pagada
                ? `<span class="insignia insignia--pagada">Pagada</span>`
                : `<span class="insignia insignia--saldo">Saldo ${dinero(orden.saldo)}</span>`
          }
        </div>
      </div>

      ${orden.estado === "CANCELADA" ? "" : pasosFlujo()}
      ${orden.ampliable && orden.estado !== "PENDIENTE" ? avisoAmpliable() : ""}

      <div class="columnas">
        <div class="tarjeta tarjeta--plana">${bloquesPorTanda()}</div>

        <aside>
          <div class="tarjeta">
            <h2 style="margin-bottom:14px">Cuenta</h2>
            <div class="totales" style="margin:0;padding:0;border:none">
              <div class="totales__fila"><span>Subtotal</span><span>${dinero(orden.subtotal)}</span></div>
              <div class="totales__fila"><span>IVA</span><span>${dinero(orden.impuestos)}</span></div>
              <div class="totales__fila totales__fila--total"><span>Total</span><span>${dinero(orden.total)}</span></div>
            </div>
            ${dividida ? tarjetasCuenta() : ""}
            ${orden.pagos.length ? listaPagos() : ""}
            <div class="acciones">${acciones(dividida)}</div>
          </div>

          ${sesion.esPersonal && orden.estado !== "CANCELADA" ? panelCierre() : ""}
        </aside>
      </div>`;

    enlazar();
  }

  const dato = (etiqueta, valor) => `
    <div class="dato">
      <span class="dato__etiqueta">${esc(etiqueta)}</span>
      <span class="dato__valor">${esc(valor)}</span>
    </div>`;

  function pasosFlujo() {
    const indiceActual = FLUJO.indexOf(orden.estado);
    return `<div class="paso-flujo">${FLUJO.map((estado, i) => {
      const clase = i < indiceActual ? "paso--hecho" : i === indiceActual ? "paso--actual" : "";
      const punto = i < indiceActual ? icono("check", { tam: 13 }) : i + 1;
      return `${i ? '<span class="paso__linea"></span>' : ""}
        <div class="paso ${clase}"><span class="paso__punto">${punto}</span>
        ${ETIQUETA_ESTADO[estado]}</div>`;
    }).join("")}</div>`;
  }

  const avisoAmpliable = () => `
    <div class="banner">
      ${icono("mesa", { tam: 18 })}
      <span>Mesa abierta: puedes seguir agregando platillos y todo se cobra junto.</span>
      <span class="banner__acciones">
        <a class="btn btn--sm" href="#/menu?orden=${orden.id}">Agregar platillos</a>
      </span>
    </div>`;

  // ---------------------------------------------------------- items por tanda

  function bloquesPorTanda() {
    const numeros = [...new Set(orden.items.map((i) => i.tanda))].sort((a, b) => a - b);
    const varias = numeros.length > 1;

    return (
      numeros
        .map((numero) => {
          const items = orden.items.filter((i) => i.tanda === numero);
          const cabecera = varias
            ? `<div class="tanda">
                 <span class="tanda__nombre">Tanda ${numero}</span>
                 ${insigniaItem(estadoDe(items))}
                 <span class="tanda__hora">${hora(items[0].creado_en ?? orden.creado_en)}</span>
               </div>`
            : "";
          return cabecera + items.map(filaItem).join("");
        })
        .join("") +
      (orden.notas
        ? `<div style="padding:16px 18px;border-top:1px solid var(--borde);
             font-size:.88rem;color:var(--tinta-suave)"><strong>Nota:</strong> ${esc(orden.notas)}</div>`
        : "")
    );
  }

  const AVANCE = { PENDIENTE: 0, EN_PREPARACION: 1, LISTA: 2, ENTREGADA: 3 };
  const estadoDe = (items) =>
    items.reduce((menos, i) => (AVANCE[i.estado] < AVANCE[menos] ? i.estado : menos), "ENTREGADA");

  function filaItem(item) {
    const puedeQuitar = item.estado === "PENDIENTE" && orden.items.length > 1 && !orden.cerrada;
    const puedeMover = sesion.esPersonal && orden.estado !== "CANCELADA" && !orden.cerrada;
    const maxCuenta = Math.max(...orden.items.map((i) => i.cuenta)) + 1;

    return `
      <div class="item-linea">
        <span class="item-linea__cant">${item.cantidad}×</span>
        <div class="item-linea__cuerpo">
          <div class="item-linea__nombre">${esc(item.nombre_producto)}</div>
          <div class="item-linea__meta">
            ${insigniaItem(item.estado)}
            ${
              puedeMover
                ? `<select class="selector-cuenta" data-cuenta-item="${item.id}"
                     title="Cuenta a la que se carga">
                     ${Array.from({ length: maxCuenta }, (_, n) => n + 1)
                       .map(
                         (n) =>
                           `<option value="${n}" ${n === item.cuenta ? "selected" : ""}>Cuenta ${n}</option>`
                       )
                       .join("")}
                   </select>`
                : `<span class="item-linea__nota">Cuenta ${item.cuenta}</span>`
            }
            ${item.notas ? `<span class="item-linea__nota">“${esc(item.notas)}”</span>` : ""}
          </div>
        </div>
        <span class="item-linea__importe">${dinero(item.subtotal)}</span>
        ${
          puedeQuitar
            ? `<button class="btn--texto" data-quitar="${item.id}"
                 style="border:none;cursor:pointer;font-size:.8rem">Quitar</button>`
            : ""
        }
      </div>`;
  }

  // ------------------------------------------------------------------ cuentas

  const tarjetasCuenta = () => `
    <div class="cuentas">
      ${cuentas
        .map(
          (c) => `<div class="cuenta ${c.pagada ? "cuenta--pagada" : ""}">
            <div class="cuenta__titulo">
              <span class="cuenta__nombre">Cuenta ${c.numero}</span>
              ${
                c.pagada
                  ? `<span class="insignia insignia--pagada insignia--sm">Pagada</span>`
                  : `<span class="insignia insignia--saldo insignia--sm">${dinero(c.saldo)}</span>`
              }
            </div>
            <div class="cuenta__items">
              ${c.items.map((i) => `${i.cantidad}× ${esc(i.nombre_producto)}`).join(" · ")}
            </div>
            <div class="cuenta__cifras">
              <span>Total</span><span class="cuenta__total">${dinero(c.total)}</span>
            </div>
            <div class="cuenta__acciones">
              ${
                !c.pagada && sesion.esPersonal && orden.estado !== "CANCELADA" && !orden.cerrada
                  ? `<button class="btn btn--amarillo btn--sm" data-cobrar-cuenta="${c.numero}">Cobrar</button>`
                  : ""
              }
              <button class="btn btn--fantasma btn--sm" data-ticket-cuenta="${c.numero}">Ticket</button>
            </div>
          </div>`
        )
        .join("")}
    </div>`;

  /**
   * Cierre de la mesa. Los requisitos se pintan a partir de lo que dice el
   * servidor: `puede_cerrarse` manda sobre el boton, no una regla copiada aqui.
   */
  function panelCierre() {
    if (orden.cerrada) {
      return `
        <div class="tarjeta cierre cierre--hecho">
          <div class="cierre__titulo">${icono("candado", { tam: 18 })} Mesa cerrada</div>
          <p class="cierre__detalle">
            ${orden.cerrada_por ? `Por ${esc(orden.cerrada_por.nombre)} · ` : ""}${fechaHora(orden.cerrada_en)}
          </p>
          ${
            sesion.esAdmin
              ? `<button class="btn btn--fantasma btn--bloque btn--sm" id="reabrir">Reabrir mesa</button>`
              : `<p class="cierre__detalle">Solo un administrador puede reabrirla.</p>`
          }
        </div>`;
    }

    const requisitos = [
      { texto: "Todos los platillos entregados", ok: orden.estado === "ENTREGADA" },
      {
        texto: orden.pagada ? "Cuenta saldada" : `Faltan ${dinero(orden.saldo)} por cobrar`,
        ok: orden.pagada,
      },
    ];

    return `
      <div class="tarjeta cierre">
        <div class="cierre__titulo">${icono("candado", { tam: 18 })} Terminar la mesa</div>
        <ul class="requisitos">
          ${requisitos
            .map(
              (r) => `<li class="requisito ${r.ok ? "requisito--ok" : "requisito--falta"}">
                ${icono(r.ok ? "check" : "reloj", { tam: 15 })}
                <span>${esc(r.texto)}</span>
              </li>`
            )
            .join("")}
        </ul>
        <button class="btn btn--bloque" id="cerrar-mesa" ${orden.puede_cerrarse ? "" : "disabled"}>
          Cerrar mesa
        </button>
        ${
          orden.puede_cerrarse
            ? `<p class="cierre__detalle">Después de esto la orden ya no admite cambios.</p>`
            : ""
        }
      </div>`;
  }

  const listaPagos = () => `
    <div style="margin-top:18px;padding-top:16px;border-top:1px solid var(--borde)">
      <p style="font-size:.78rem;text-transform:uppercase;letter-spacing:.05em;
                color:var(--tinta-tenue);margin-bottom:8px">Pagos recibidos</p>
      ${orden.pagos
        .map(
          (p) => `<div class="totales__fila">
            <span>
              ${esc(ETIQUETA_METODO[p.metodo] ?? p.metodo)}
              ${cuentas.length > 1 ? `<small>· cuenta ${p.cuenta}</small>` : ""}
              ${
                Number(p.propina) > 0
                  ? `<small>+ ${dinero(p.propina)} propina${
                      p.propina_porcentaje ? ` (${Number(p.propina_porcentaje)}%)` : ""
                    }</small>`
                  : ""
              }
            </span>
            <span>${dinero(p.monto)}</span>
          </div>`
        )
        .join("")}
    </div>`;

  function acciones(dividida) {
    const botones = [];

    if (orden.cerrada) {
      return `<button class="btn btn--fantasma" id="ver-factura">Ver ticket</button>`;
    }

    if (sesion.esPersonal) {
      for (const estado of TRANSICIONES[orden.estado]) {
        if (estado === "CANCELADA") continue;
        botones.push(
          `<button class="btn" data-estado="${estado}">Marcar ${ETIQUETA_ESTADO[estado].toLowerCase()}</button>`
        );
      }
    }
    if (sesion.esPersonal && !orden.pagada && orden.estado !== "CANCELADA" && Number(orden.total) > 0 && !dividida) {
      botones.push(`<button class="btn btn--amarillo" id="cobrar">Cobrar</button>`);
    }
    if (orden.ampliable) {
      botones.push(`<a class="btn btn--fantasma" href="#/menu?orden=${orden.id}">Agregar platillos</a>`);
    }
    botones.push(`<button class="btn btn--fantasma" id="ver-factura">Ver ticket</button>`);
    if (TRANSICIONES[orden.estado].includes("CANCELADA")) {
      botones.push(`<button class="btn--texto" id="cancelar" style="border:none;cursor:pointer">Cancelar orden</button>`);
    }
    return botones.join("");
  }

  // ----------------------------------------------------------------- eventos

  function enlazar() {
    const intentar = async (accion, exito) => {
      try {
        await accion();
        if (exito) avisar(exito, "ok");
        await refrescar();
      } catch (e) {
        avisar(e.message);
        await refrescar();
      }
    };

    contenedor.querySelectorAll("[data-estado]").forEach((boton) =>
      boton.addEventListener("click", () => {
        boton.disabled = true;
        intentar(() => api.cambiarEstado(orden.id, boton.dataset.estado));
      })
    );

    contenedor.querySelectorAll("[data-quitar]").forEach((boton) =>
      boton.addEventListener("click", () =>
        intentar(() => api.quitarItem(orden.id, Number(boton.dataset.quitar)))
      )
    );

    contenedor.querySelectorAll("[data-cuenta-item]").forEach((selector) =>
      selector.addEventListener("change", () =>
        intentar(
          () =>
            api.asignarCuenta(orden.id, Number(selector.dataset.cuentaItem), Number(selector.value)),
          `Platillo movido a la cuenta ${selector.value}`
        )
      )
    );

    contenedor.querySelectorAll("[data-cobrar-cuenta]").forEach((boton) =>
      boton.addEventListener("click", () => abrirCobro(Number(boton.dataset.cobrarCuenta)))
    );
    contenedor.querySelectorAll("[data-ticket-cuenta]").forEach((boton) =>
      boton.addEventListener("click", () => abrirFactura(Number(boton.dataset.ticketCuenta)))
    );

    document.getElementById("cobrar")?.addEventListener("click", () => abrirCobro(null));
    document.getElementById("ver-factura")?.addEventListener("click", () => abrirFactura(null));

    document.getElementById("cerrar-mesa")?.addEventListener("click", async (e) => {
      const boton = e.currentTarget;
      if (!(await confirmar(
        `¿Dar por terminada la mesa de ${orden.numero}? Después ya no se podrá modificar.`,
        { textoOk: "Cerrar mesa", peligro: false }
      ))) return;
      boton.disabled = true;
      intentar(() => api.cerrar(orden.id), "Mesa cerrada");
    });

    document.getElementById("reabrir")?.addEventListener("click", () =>
      intentar(() => api.reabrir(orden.id), "Mesa reabierta")
    );

    document.getElementById("cancelar")?.addEventListener("click", async () => {
      if (!(await confirmar(`¿Cancelar la orden ${orden.numero}? No se puede deshacer.`))) return;
      intentar(() => api.cancelar(orden.id), "Orden cancelada");
    });
  }

  // ------------------------------------------------------------------- cobro

  function abrirCobro(numeroCuenta) {
    const resumen = numeroCuenta ? cuentas.find((c) => c.numero === numeroCuenta) : null;
    const saldo = resumen ? resumen.saldo : orden.saldo;
    const titulo = resumen ? `Cobrar cuenta ${numeroCuenta}` : `Cobrar ${orden.numero}`;

    modal({
      titulo,
      contenido: `
        <p style="color:var(--tinta-suave);margin-bottom:18px">
          Saldo pendiente: <strong style="color:var(--rojo)">${dinero(saldo)}</strong>
        </p>
        <div class="campo">
          <label for="metodo">Método de pago</label>
          <select id="metodo">
            <option value="EFECTIVO">Efectivo</option>
            <option value="TARJETA">Tarjeta</option>
            <option value="TRANSFERENCIA">Transferencia</option>
          </select>
        </div>
        <div class="campo">
          <label for="monto">Monto</label>
          <input id="monto" type="number" step="0.01" min="0.01" value="${saldo}">
          <span class="campo__ayuda">Menos del saldo deja la cuenta abierta para otro pago</span>
        </div>

        <div class="campo">
          <label>Propina</label>
          <div class="propina-modos">
            ${PORCENTAJES_PROPINA.map(
              (p) => `<button type="button" class="chip" data-pct="${p}">${p}%</button>`
            ).join("")}
            <button type="button" class="chip activo" data-pct="">Importe</button>
          </div>
          <input id="propina" type="number" step="0.01" min="0" value="0.00">
          <span class="campo__ayuda" id="ayuda-propina">Escribe el importe, o elige un porcentaje del monto.</span>
        </div>

        <div class="campo" id="campo-ref" hidden>
          <label for="referencia">Referencia / autorización</label>
          <input id="referencia" placeholder="AUTH-0001">
        </div>`,
      pie: `<button class="btn btn--fantasma" data-cerrar>Cancelar</button>
            <button class="btn" data-confirmar>Registrar pago</button>`,
      alAbrir(nodo, cerrar) {
        const metodo = nodo.querySelector("#metodo");
        const campoRef = nodo.querySelector("#campo-ref");
        const monto = nodo.querySelector("#monto");
        const propina = nodo.querySelector("#propina");
        const ayuda = nodo.querySelector("#ayuda-propina");
        let porcentaje = null;

        metodo.addEventListener("change", () => {
          campoRef.hidden = metodo.value === "EFECTIVO";
        });

        // Al elegir un porcentaje, la propina se recalcula sobre el monto.
        const recalcular = () => {
          if (porcentaje === null) return;
          const importe = (Number(monto.value || 0) * porcentaje) / 100;
          propina.value = importe.toFixed(2);
          ayuda.textContent = `${porcentaje}% de ${dinero(monto.value || 0)}`;
        };

        nodo.querySelectorAll("[data-pct]").forEach((chip) =>
          chip.addEventListener("click", () => {
            nodo.querySelectorAll("[data-pct]").forEach((c) => c.classList.remove("activo"));
            chip.classList.add("activo");
            porcentaje = chip.dataset.pct ? Number(chip.dataset.pct) : null;
            if (porcentaje === null) {
              propina.readOnly = false;
              ayuda.textContent = "Escribe el importe, o elige un porcentaje del monto.";
            } else {
              propina.readOnly = true;
              recalcular();
            }
          })
        );
        monto.addEventListener("input", recalcular);

        nodo.querySelector("[data-cerrar]").addEventListener("click", cerrar);
        nodo.querySelector("[data-confirmar]").addEventListener("click", async (e) => {
          const boton = e.currentTarget;
          if (!monto.value || Number(monto.value) <= 0) return avisar("Escribe un monto válido");

          const pago = {
            metodo: metodo.value,
            monto: Number(monto.value).toFixed(2),
            cuenta: numeroCuenta,
            referencia: nodo.querySelector("#referencia").value.trim() || null,
          };
          // El backend recalcula el porcentaje; se manda uno u otro, nunca los dos.
          if (porcentaje === null) pago.propina = Number(propina.value || 0).toFixed(2);
          else pago.propina_porcentaje = porcentaje.toFixed(2);

          boton.disabled = true;
          boton.textContent = "Registrando…";
          try {
            await api.pagar(orden.id, pago);
            cerrar();
            await refrescar();
            avisar(orden.pagada ? "Cuenta saldada" : `Registrado. Falta ${dinero(orden.saldo)}`, "ok");
          } catch (err) {
            avisar(err.message);
            boton.disabled = false;
            boton.textContent = "Registrar pago";
          }
        });
      },
    });
  }

  // ----------------------------------------------------------------- factura

  async function abrirFactura(numeroCuenta) {
    let factura;
    try {
      factura = await api.factura(orden.id, numeroCuenta);
    } catch (e) {
      return avisar(e.message);
    }

    modal({
      titulo: numeroCuenta ? `Ticket · cuenta ${numeroCuenta}` : "Ticket",
      contenido: `
        <div class="ticket">
          <div class="ticket__marca">
            <h3>SABOR</h3>
            <div>${esc(factura.orden_numero)}</div>
            <div>${fechaHora(factura.fecha)}</div>
            ${
              factura.cuenta
                ? `<div>Cuenta ${factura.cuenta} de ${factura.total_cuentas}</div>`
                : factura.total_cuentas > 1
                  ? `<div>${factura.total_cuentas} cuentas</div>`
                  : ""
            }
          </div>
          <hr class="ticket__sep">
          <div class="ticket__fila"><span>Mesa</span><span>${factura.mesa ?? "—"}</span></div>
          <div class="ticket__fila"><span>Atendió</span><span>${esc(factura.atendio ?? "—")}</span></div>
          <div class="ticket__fila"><span>Cliente</span><span>${esc(factura.cliente ?? "—")}</span></div>
          <hr class="ticket__sep">
          ${factura.lineas
            .map(
              (l) => `<div class="ticket__linea">
                <span>${l.cantidad}×</span>
                <span>${esc(l.descripcion)}</span>
                <span>${dinero(l.importe)}</span>
              </div>`
            )
            .join("")}
          <hr class="ticket__sep">
          <div class="ticket__fila"><span>Subtotal</span><span>${dinero(factura.subtotal)}</span></div>
          <div class="ticket__fila">
            <span>IVA ${(Number(factura.tasa_iva) * 100).toFixed(0)}%</span>
            <span>${dinero(factura.impuestos)}</span>
          </div>
          <div class="ticket__fila ticket__fila--fuerte"><span>TOTAL</span><span>${dinero(factura.total)}</span></div>
          ${
            factura.pagos.length
              ? `<hr class="ticket__sep">
                 ${factura.pagos
                   .map(
                     (p) => `<div class="ticket__fila"><span>${esc(ETIQUETA_METODO[p.metodo] ?? p.metodo)}</span>
                       <span>${dinero(p.monto)}</span></div>`
                   )
                   .join("")}
                 ${
                   Number(factura.propina_total) > 0
                     ? `<div class="ticket__fila"><span>Propina</span><span>${dinero(factura.propina_total)}</span></div>`
                     : ""
                 }
                 <div class="ticket__fila ticket__fila--fuerte">
                   <span>${factura.pagada ? "PAGADO" : "SALDO"}</span>
                   <span>${dinero(factura.pagada ? factura.total_pagado : factura.saldo)}</span>
                 </div>`
              : `<hr class="ticket__sep"><div class="ticket__fila ticket__fila--fuerte">
                   <span>PENDIENTE DE PAGO</span><span>${dinero(factura.saldo)}</span></div>`
          }
          <div class="ticket__pie">¡Gracias por su visita!</div>
        </div>`,
      pie: `<button class="btn btn--fantasma" data-cerrar>Cerrar</button>
            <button class="btn" data-imprimir>Imprimir</button>`,
      alAbrir(nodo, cerrar) {
        nodo.querySelector("[data-cerrar]").addEventListener("click", cerrar);
        nodo.querySelector("[data-imprimir]").addEventListener("click", () => window.print());
      },
    });
  }

  // Se pinta al final: arriba solo hay declaraciones que esta funcion necesita.
  pintar();
}
