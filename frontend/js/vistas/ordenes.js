import { api } from "../api.js";
import { sesion } from "../sesion.js";
import { ir } from "../router.js";
import { icono } from "../iconos.js";
import {
  ETIQUETA_ESTADO, ETIQUETA_TIPO, cargando, dinero, esc, fechaHora, insigniaEstado, vacio,
} from "../ui.js";

// Tres ejes independientes: cómo va en cocina, si ya se cobró y si la mesa se cerró.
// Una orden puede estar entregada y seguir sin pagarse, por eso van por separado.
const FILTROS = [
  {
    clave: "estado",
    etiqueta: "Estado",
    opciones: [
      { valor: "", texto: "Todas" },
      ...["PENDIENTE", "EN_PREPARACION", "LISTA", "ENTREGADA", "CANCELADA"].map((e) => ({
        valor: e, texto: ETIQUETA_ESTADO[e],
      })),
    ],
  },
  {
    clave: "pagada",
    etiqueta: "Cobro",
    opciones: [
      { valor: "", texto: "Todas" },
      { valor: "false", texto: "Por cobrar" },
      { valor: "true", texto: "Pagadas" },
    ],
  },
  {
    clave: "cerrada",
    etiqueta: "Mesa",
    opciones: [
      { valor: "", texto: "Todas" },
      { valor: "false", texto: "Abiertas" },
      { valor: "true", texto: "Cerradas" },
    ],
  },
];

export async function vistaOrdenes(contenedor, { consulta }) {
  const activos = {
    estado: consulta.get("estado") ?? "",
    pagada: consulta.get("pagada") ?? "",
    cerrada: consulta.get("cerrada") ?? "",
  };

  contenedor.innerHTML = `
    <div class="encabezado">
      <div>
        <h1>Órdenes</h1>
        <p>${sesion.esPersonal ? "Todas las comandas del turno." : "Tu historial de pedidos."}</p>
      </div>
      <a class="btn" href="#/menu">Nueva orden</a>
    </div>

    <div class="filtros" id="filtros"></div>
    <div id="resumen"></div>
    <div id="lista">${cargando()}</div>`;

  const $filtros = document.getElementById("filtros");
  const $resumen = document.getElementById("resumen");
  const $lista = document.getElementById("lista");

  function pintarFiltros() {
    $filtros.innerHTML = FILTROS.map(
      (grupo) => `
        <div class="filtro-fila">
          <span class="filtro-fila__etiqueta">${grupo.etiqueta}</span>
          <div class="chips">
            ${grupo.opciones
              .map(
                (o) => `<button class="chip ${activos[grupo.clave] === o.valor ? "activo" : ""}"
                          data-grupo="${grupo.clave}" data-valor="${o.valor}">${o.texto}</button>`
              )
              .join("")}
          </div>
        </div>`
    ).join("");
  }

  $filtros.addEventListener("click", (e) => {
    const boton = e.target.closest("[data-grupo]");
    if (!boton) return;
    activos[boton.dataset.grupo] = boton.dataset.valor;
    pintarFiltros();
    cargar();
  });

  async function cargar() {
    $lista.innerHTML = cargando();
    $resumen.innerHTML = "";

    let ordenes;
    try {
      ordenes = await api.ordenes({
        estado: activos.estado,
        pagada: activos.pagada,
        cerrada: activos.cerrada,
        limit: 100,
      });
    } catch (e) {
      $lista.innerHTML = vacio("alerta", "No se pudieron cargar las órdenes", e.message);
      return;
    }

    if (!ordenes.length) {
      $lista.innerHTML = vacio(
        "carta",
        hayFiltros() ? "Nada con esos filtros" : "Todavía no hay órdenes",
        hayFiltros() ? "Prueba con otra combinación." : "Crea una desde el menú."
      );
      return;
    }

    pintarResumen(ordenes);
    $lista.innerHTML = `
      <div class="tarjeta tarjeta--plana">
        <table class="tabla">
          <thead>
            <tr>
              <th>Orden</th>
              <th>Estado</th>
              <th>Tipo</th>
              <th>Mesa</th>
              ${sesion.esPersonal ? "<th>Atendió</th>" : ""}
              <th>Hora</th>
              <th class="num">Total</th>
              <th class="num">Cobro</th>
            </tr>
          </thead>
          <tbody>${ordenes.map(fila).join("")}</tbody>
        </table>
      </div>`;

    $lista.querySelectorAll("[data-id]").forEach((tr) =>
      tr.addEventListener("click", () => ir(`/ordenes/${tr.dataset.id}`))
    );
  }

  const hayFiltros = () => Object.values(activos).some(Boolean);

  /** Cuánto dinero sigue en la calle: es el dato que un encargado busca primero. */
  function pintarResumen(ordenes) {
    if (!sesion.esPersonal) return;
    const vivas = ordenes.filter((o) => o.estado !== "CANCELADA");
    const porCobrar = vivas.filter((o) => !o.pagada);
    const saldo = porCobrar.reduce((suma, o) => suma + Number(o.saldo), 0);
    const cerradas = vivas.filter((o) => o.cerrada).length;

    $resumen.innerHTML = `
      <div class="resumen">
        ${cifra("Órdenes", vivas.length)}
        ${cifra("Por cobrar", porCobrar.length, porCobrar.length ? "alerta" : null)}
        ${cifra("Saldo pendiente", dinero(saldo), saldo > 0 ? "alerta" : null)}
        ${cifra("Mesas cerradas", cerradas)}
      </div>`;
  }

  const cifra = (etiqueta, valor, tono = null) => `
    <div class="resumen__celda ${tono ? `resumen__celda--${tono}` : ""}">
      <span class="resumen__etiqueta">${etiqueta}</span>
      <span class="resumen__valor">${valor}</span>
    </div>`;

  const fila = (o) => `
    <tr class="clicable ${o.cerrada ? "fila--cerrada" : ""}" data-id="${o.id}">
      <td>
        <span class="celda-orden">
          ${o.cerrada ? `<span class="candado" title="Mesa cerrada">${icono("candado", { tam: 14 })}</span>` : ""}
          <strong>${esc(o.numero)}</strong>
        </span>
      </td>
      <td>${insigniaEstado(o.estado)}</td>
      <td>${esc(ETIQUETA_TIPO[o.tipo] ?? o.tipo)}</td>
      <td>${o.mesa ?? "—"}</td>
      ${sesion.esPersonal ? `<td>${esc(o.mesero?.nombre ?? "—")}</td>` : ""}
      <td>${fechaHora(o.creado_en)}</td>
      <td class="num"><strong>${dinero(o.total)}</strong></td>
      <td class="num">${estadoCobro(o)}</td>
    </tr>`;

  function estadoCobro(o) {
    if (o.estado === "CANCELADA") return "—";
    if (o.cerrada) return `<span class="insignia insignia--cerrada">Cerrada</span>`;
    if (o.pagada) return `<span class="insignia insignia--pagada">Pagada</span>`;
    return `<span class="insignia insignia--saldo">${dinero(o.saldo)}</span>`;
  }

  pintarFiltros();
  await cargar();
}
