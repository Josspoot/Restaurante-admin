import { api } from "../api.js";
import { ir } from "../router.js";
import { ETIQUETA_ITEM, ETIQUETA_TIPO, avisar, cargando, esc, hora, vacio } from "../ui.js";

// Columnas del tablero y a que estado avanza cada comanda.
const COLUMNAS = [
  { estado: "PENDIENTE", siguiente: "EN_PREPARACION", accion: "Empezar" },
  { estado: "EN_PREPARACION", siguiente: "LISTA", accion: "Marcar lista" },
  { estado: "LISTA", siguiente: "ENTREGADA", accion: "Entregar" },
];

const REFRESCO_MS = 15000;

export async function vistaCocina(contenedor) {
  contenedor.innerHTML = `
    <div class="encabezado">
      <div>
        <h1>Cocina</h1>
        <p>Cada tanda es una comanda propia: si una mesa pide más, llega aparte.
           Se actualiza automáticamente cada 15 s.</p>
      </div>
      <button class="btn btn--fantasma" id="refrescar">Actualizar</button>
    </div>
    <div id="tablero">${cargando()}</div>`;

  const $tablero = document.getElementById("tablero");
  document.getElementById("refrescar").addEventListener("click", () => cargar());

  let temporizador = null;
  const detener = () => {
    clearInterval(temporizador);
    window.removeEventListener("hashchange", detener);
  };
  window.addEventListener("hashchange", detener);

  async function cargar() {
    let comandas;
    try {
      comandas = await api.cocina();
    } catch (e) {
      $tablero.innerHTML = vacio("alerta", "No se pudo cargar el tablero", e.message);
      return;
    }

    if (!comandas.length) {
      $tablero.innerHTML = vacio("olla", "Cocina al día", "No hay comandas activas ahora mismo.");
      return;
    }

    $tablero.innerHTML = `<div class="tablero">${COLUMNAS.map((c) =>
      columna(c, comandas.filter((x) => x.estado === c.estado))
    ).join("")}</div>`;

    $tablero.querySelectorAll("[data-avanzar]").forEach((boton) =>
      boton.addEventListener("click", async (e) => {
        e.stopPropagation();
        boton.disabled = true;
        try {
          await api.cambiarEstadoTanda(
            Number(boton.dataset.avanzar), Number(boton.dataset.tanda), boton.dataset.a
          );
          await cargar();
        } catch (err) {
          avisar(err.message);
          boton.disabled = false;
        }
      })
    );

    $tablero.querySelectorAll("[data-abrir]").forEach((tarjeta) =>
      tarjeta.addEventListener("click", () => ir(`/ordenes/${tarjeta.dataset.abrir}`))
    );
  }

  const columna = (config, comandas) => `
    <section class="columna">
      <div class="columna__titulo">
        <h3>${ETIQUETA_ITEM[config.estado]}</h3>
        <span class="columna__conteo">${comandas.length}</span>
      </div>
      <div class="columna__lista">
        ${
          comandas.length
            ? comandas.map((c) => comanda(c, config)).join("")
            : `<p style="color:var(--tinta-tenue);font-size:.86rem;padding:8px 0">Sin comandas.</p>`
        }
      </div>
    </section>`;

  const comanda = (c, config) => `
    <article class="comanda" data-abrir="${c.orden_id}" style="cursor:pointer">
      <div class="comanda__cabecera">
        <span class="comanda__numero">
          ${esc(c.numero)}${c.mesa ? ` · Mesa ${c.mesa}` : ` · ${esc(ETIQUETA_TIPO[c.tipo] ?? c.tipo)}`}
          ${c.tanda > 1 ? `<span class="insignia insignia--sm insignia--pendiente">Tanda ${c.tanda}</span>` : ""}
        </span>
        <span class="comanda__hora">${hora(c.creado_en)}</span>
      </div>
      <ul class="comanda__items">
        ${c.items
          .map(
            (i) => `<li><b>${i.cantidad}×</b> <span>${esc(i.nombre_producto)}${
              i.notas ? `<div class="comanda__nota">“${esc(i.notas)}”</div>` : ""
            }</span></li>`
          )
          .join("")}
      </ul>
      ${c.notas ? `<p class="comanda__nota" style="margin-bottom:10px">Nota: ${esc(c.notas)}</p>` : ""}
      <button class="btn btn--sm btn--bloque" data-avanzar="${c.orden_id}" data-tanda="${c.tanda}"
              data-a="${config.siguiente}">${config.accion}</button>
    </article>`;

  await cargar();
  temporizador = setInterval(cargar, REFRESCO_MS);
}
