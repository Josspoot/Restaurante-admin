import { api } from "../api.js";
import { avisar, cargando, confirmar, dinero, esc, modal, vacio } from "../ui.js";

export async function vistaAdmin(contenedor) {
  contenedor.innerHTML = `
    <div class="encabezado">
      <div>
        <h1>Administrar</h1>
        <p>Da de alta platillos, ajusta precios y organiza el menú.</p>
      </div>
      <div style="display:flex;gap:10px">
        <button class="btn btn--fantasma" id="nueva-categoria">Nueva categoría</button>
        <button class="btn" id="nuevo-producto">Nuevo platillo</button>
      </div>
    </div>

    <div class="chips" id="pestanas" style="margin-bottom:20px">
      <button class="chip activo" data-tab="productos">Platillos</button>
      <button class="chip" data-tab="categorias">Categorías</button>
    </div>

    <div id="panel">${cargando()}</div>`;

  const $panel = document.getElementById("panel");
  let pestana = "productos";
  let categorias = [];

  document.getElementById("pestanas").addEventListener("click", (e) => {
    const boton = e.target.closest("[data-tab]");
    if (!boton) return;
    pestana = boton.dataset.tab;
    contenedor
      .querySelectorAll("[data-tab]")
      .forEach((b) => b.classList.toggle("activo", b === boton));
    cargar();
  });

  document.getElementById("nuevo-producto").addEventListener("click", () => formProducto());
  document.getElementById("nueva-categoria").addEventListener("click", () => formCategoria());

  async function cargar() {
    $panel.innerHTML = cargando();
    try {
      categorias = await api.categorias();
      $panel.innerHTML = pestana === "productos" ? await tablaProductos() : tablaCategorias();
      enlazar();
    } catch (e) {
      $panel.innerHTML = vacio("alerta", "No se pudo cargar", e.message);
    }
  }

  // ------------------------------------------------------------- productos

  async function tablaProductos() {
    const productos = await api.productos({ limit: 200 });
    if (!productos.length)
      return vacio("carta", "El menú está vacío", "Empieza dando de alta un platillo.");

    return `
      <div class="tarjeta tarjeta--plana">
        <table class="tabla">
          <thead>
            <tr><th>Platillo</th><th>Categoría</th><th class="num">Precio</th>
                <th>Estado</th><th class="num">Acciones</th></tr>
          </thead>
          <tbody>
            ${productos
              .map(
                (p) => `<tr>
                  <td>
                    <strong>${esc(p.nombre)}</strong>
                    ${p.descripcion ? `<div style="font-size:.8rem;color:var(--tinta-tenue)">${esc(p.descripcion)}</div>` : ""}
                  </td>
                  <td>${esc(p.categoria.nombre)}</td>
                  <td class="num">${dinero(p.precio)}</td>
                  <td>
                    <span class="insignia insignia--${p.disponible ? "lista" : "cancelada"}">
                      ${p.disponible ? "Disponible" : "Agotado"}
                    </span>
                  </td>
                  <td class="num" style="white-space:nowrap">
                    <button class="btn--texto" data-toggle="${p.id}" data-valor="${!p.disponible}"
                            style="border:none;cursor:pointer;font-size:.82rem">
                      ${p.disponible ? "Agotar" : "Reactivar"}
                    </button>
                    <button class="btn--texto" data-editar="${p.id}"
                            style="border:none;cursor:pointer;font-size:.82rem">Editar</button>
                    <button class="btn--texto" data-borrar="${p.id}" data-nombre="${esc(p.nombre)}"
                            style="border:none;cursor:pointer;font-size:.82rem">Borrar</button>
                  </td>
                </tr>`
              )
              .join("")}
          </tbody>
        </table>
      </div>`;
  }

  const tablaCategorias = () => {
    if (!categorias.length) return vacio("carpeta", "Sin categorías", "Crea la primera para agrupar el menú.");
    return `
      <div class="tarjeta tarjeta--plana">
        <table class="tabla">
          <thead><tr><th>Categoría</th><th>Descripción</th><th>Estado</th><th class="num">Acciones</th></tr></thead>
          <tbody>
            ${categorias
              .map(
                (c) => `<tr>
                  <td><strong>${esc(c.nombre)}</strong></td>
                  <td style="color:var(--tinta-suave)">${esc(c.descripcion ?? "—")}</td>
                  <td><span class="insignia insignia--${c.activa ? "lista" : "entregada"}">
                    ${c.activa ? "Activa" : "Oculta"}</span></td>
                  <td class="num" style="white-space:nowrap">
                    <button class="btn--texto" data-cat-toggle="${c.id}" data-valor="${!c.activa}"
                            style="border:none;cursor:pointer;font-size:.82rem">
                      ${c.activa ? "Ocultar" : "Mostrar"}
                    </button>
                    <button class="btn--texto" data-cat-editar="${c.id}"
                            style="border:none;cursor:pointer;font-size:.82rem">Editar</button>
                    <button class="btn--texto" data-cat-borrar="${c.id}" data-nombre="${esc(c.nombre)}"
                            style="border:none;cursor:pointer;font-size:.82rem">Borrar</button>
                  </td>
                </tr>`
              )
              .join("")}
          </tbody>
        </table>
      </div>`;
  };

  // ---------------------------------------------------------------- eventos

  function enlazar() {
    const accion = async (fn, mensaje) => {
      try {
        await fn();
        if (mensaje) avisar(mensaje, "ok");
        await cargar();
      } catch (e) {
        avisar(e.message);
        await cargar();
      }
    };

    $panel.querySelectorAll("[data-toggle]").forEach((b) =>
      b.addEventListener("click", () =>
        accion(() =>
          api.editarProducto(Number(b.dataset.toggle), { disponible: b.dataset.valor === "true" })
        )
      )
    );
    $panel.querySelectorAll("[data-editar]").forEach((b) =>
      b.addEventListener("click", async () => formProducto(await api.producto(Number(b.dataset.editar))))
    );
    $panel.querySelectorAll("[data-borrar]").forEach((b) =>
      b.addEventListener("click", async () => {
        if (!(await confirmar(`¿Borrar "${b.dataset.nombre}" del menú?`))) return;
        accion(() => api.borrarProducto(Number(b.dataset.borrar)), "Platillo eliminado");
      })
    );

    $panel.querySelectorAll("[data-cat-toggle]").forEach((b) =>
      b.addEventListener("click", () =>
        accion(() =>
          api.editarCategoria(Number(b.dataset.catToggle), { activa: b.dataset.valor === "true" })
        )
      )
    );
    $panel.querySelectorAll("[data-cat-editar]").forEach((b) =>
      b.addEventListener("click", () =>
        formCategoria(categorias.find((c) => c.id === Number(b.dataset.catEditar)))
      )
    );
    $panel.querySelectorAll("[data-cat-borrar]").forEach((b) =>
      b.addEventListener("click", async () => {
        if (!(await confirmar(`¿Borrar la categoría "${b.dataset.nombre}"?`))) return;
        accion(() => api.borrarCategoria(Number(b.dataset.catBorrar)), "Categoría eliminada");
      })
    );
  }

  // --------------------------------------------------------------- formularios

  function formProducto(producto = null) {
    const editando = Boolean(producto);
    modal({
      titulo: editando ? "Editar platillo" : "Nuevo platillo",
      contenido: `
        <div class="campo">
          <label for="p-nombre">Nombre</label>
          <input id="p-nombre" value="${esc(producto?.nombre ?? "")}" placeholder="Tacos al pastor">
        </div>
        <div class="campo">
          <label for="p-desc">Descripción</label>
          <textarea id="p-desc" placeholder="Ingredientes, porción…">${esc(producto?.descripcion ?? "")}</textarea>
        </div>
        <div class="rejilla-campos">
          <div class="campo">
            <label for="p-precio">Precio</label>
            <input id="p-precio" type="number" step="0.01" min="0.01" value="${producto?.precio ?? ""}">
          </div>
          <div class="campo">
            <label for="p-cat">Categoría</label>
            <select id="p-cat">
              ${categorias
                .map(
                  (c) =>
                    `<option value="${c.id}" ${producto?.categoria.id === c.id ? "selected" : ""}>${esc(c.nombre)}</option>`
                )
                .join("")}
            </select>
          </div>
        </div>`,
      pie: `<button class="btn btn--fantasma" data-cerrar>Cancelar</button>
            <button class="btn" data-guardar>${editando ? "Guardar" : "Crear"}</button>`,
      alAbrir(nodo, cerrar) {
        nodo.querySelector("[data-cerrar]").addEventListener("click", cerrar);
        nodo.querySelector("[data-guardar]").addEventListener("click", async (e) => {
          const boton = e.currentTarget;
          const datos = {
            nombre: nodo.querySelector("#p-nombre").value.trim(),
            descripcion: nodo.querySelector("#p-desc").value.trim() || null,
            precio: Number(nodo.querySelector("#p-precio").value).toFixed(2),
            categoria_id: Number(nodo.querySelector("#p-cat").value),
          };
          if (datos.nombre.length < 2) return avisar("Escribe el nombre del platillo");
          if (!(Number(datos.precio) > 0)) return avisar("El precio debe ser mayor a cero");

          boton.disabled = true;
          try {
            if (editando) await api.editarProducto(producto.id, datos);
            else await api.crearProducto({ ...datos, disponible: true });
            cerrar();
            avisar(editando ? "Platillo actualizado" : "Platillo creado", "ok");
            await cargar();
          } catch (err) {
            avisar(err.message);
            boton.disabled = false;
          }
        });
      },
    });
  }

  function formCategoria(categoria = null) {
    const editando = Boolean(categoria);
    modal({
      titulo: editando ? "Editar categoría" : "Nueva categoría",
      contenido: `
        <div class="campo">
          <label for="c-nombre">Nombre</label>
          <input id="c-nombre" value="${esc(categoria?.nombre ?? "")}" placeholder="Postres">
        </div>
        <div class="campo">
          <label for="c-desc">Descripción</label>
          <input id="c-desc" value="${esc(categoria?.descripcion ?? "")}" placeholder="El cierre perfecto">
        </div>`,
      pie: `<button class="btn btn--fantasma" data-cerrar>Cancelar</button>
            <button class="btn" data-guardar>${editando ? "Guardar" : "Crear"}</button>`,
      alAbrir(nodo, cerrar) {
        nodo.querySelector("[data-cerrar]").addEventListener("click", cerrar);
        nodo.querySelector("[data-guardar]").addEventListener("click", async (e) => {
          const boton = e.currentTarget;
          const datos = {
            nombre: nodo.querySelector("#c-nombre").value.trim(),
            descripcion: nodo.querySelector("#c-desc").value.trim() || null,
          };
          if (datos.nombre.length < 2) return avisar("Escribe el nombre de la categoría");

          boton.disabled = true;
          try {
            if (editando) await api.editarCategoria(categoria.id, datos);
            else await api.crearCategoria(datos);
            cerrar();
            avisar(editando ? "Categoría actualizada" : "Categoría creada", "ok");
            await cargar();
          } catch (err) {
            avisar(err.message);
            boton.disabled = false;
          }
        });
      },
    });
  }

  await cargar();
}
