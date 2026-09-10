import { api } from "../api.js";
import { sesion } from "../sesion.js";
import { ir } from "../router.js";
import { avisar, esc } from "../ui.js";

const CUENTAS_DEMO = [
  { etiqueta: "Admin", email: "admin@restaurante.com", password: "admin123" },
  { etiqueta: "Mesero", email: "mesero@restaurante.com", password: "mesero123" },
  { etiqueta: "Cliente", email: "cliente@correo.com", password: "cliente123" },
];

export async function vistaLogin(contenedor) {
  if (sesion.activa) return ir(sesion.esPersonal ? "/ordenes" : "/menu");

  document.getElementById("cabecera").hidden = true;
  contenedor.style.padding = "0";
  contenedor.style.maxWidth = "none";

  contenedor.innerHTML = `
    <div class="login">
      <aside class="login__arte">
        <div class="login__lema">
          <div class="marca__icono"><svg class="ico" width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="3.25"/></svg></div>
          <h1>Sabor</h1>
          <p>Toma la comanda, sigue la cocina y cobra la cuenta desde un mismo lugar.</p>
        </div>
      </aside>

      <section class="login__panel">
        <div class="login__caja">
          <h2 id="titulo">Bienvenido de vuelta</h2>
          <p id="subtitulo">Entra con tu cuenta para continuar.</p>

          <form id="formulario" novalidate>
            <div class="campo" id="campo-nombre" hidden>
              <label for="nombre">Nombre</label>
              <input id="nombre" name="nombre" autocomplete="name" placeholder="Tu nombre completo">
            </div>
            <div class="campo">
              <label for="email">Correo</label>
              <input id="email" name="email" type="email" autocomplete="email" required
                     placeholder="tucorreo@ejemplo.com">
            </div>
            <div class="campo">
              <label for="password">Contraseña</label>
              <input id="password" name="password" type="password" autocomplete="current-password"
                     required placeholder="••••••••">
            </div>
            <button class="btn btn--bloque" id="enviar" type="submit">Entrar</button>
          </form>

          <p style="margin-top:18px;font-size:.88rem;color:var(--tinta-suave);text-align:center">
            <span id="alterno-texto">¿No tienes cuenta?</span>
            <button class="btn--texto" id="alternar" type="button"
                    style="border:none;cursor:pointer;font-weight:600">Regístrate</button>
          </p>

          <div class="demo">
            <p class="demo__titulo">Cuentas de prueba</p>
            <div class="demo__botones">
              ${CUENTAS_DEMO.map(
                (c, i) => `<button class="chip" data-demo="${i}" type="button">${esc(c.etiqueta)}</button>`
              ).join("")}
            </div>
          </div>
        </div>
      </section>
    </div>`;

  let modoRegistro = false;
  const $ = (id) => document.getElementById(id);
  const formulario = $("formulario");

  $("alternar").addEventListener("click", () => {
    modoRegistro = !modoRegistro;
    $("campo-nombre").hidden = !modoRegistro;
    $("nombre").required = modoRegistro;
    $("titulo").textContent = modoRegistro ? "Crea tu cuenta" : "Bienvenido de vuelta";
    $("subtitulo").textContent = modoRegistro
      ? "Regístrate para ordenar desde tu mesa."
      : "Entra con tu cuenta para continuar.";
    $("enviar").textContent = modoRegistro ? "Crear cuenta" : "Entrar";
    $("alterno-texto").textContent = modoRegistro ? "¿Ya tienes cuenta?" : "¿No tienes cuenta?";
    $("alternar").textContent = modoRegistro ? "Inicia sesión" : "Regístrate";
    $("password").autocomplete = modoRegistro ? "new-password" : "current-password";
  });

  contenedor.querySelectorAll("[data-demo]").forEach((boton) => {
    boton.addEventListener("click", () => {
      const cuenta = CUENTAS_DEMO[Number(boton.dataset.demo)];
      $("email").value = cuenta.email;
      $("password").value = cuenta.password;
      formulario.requestSubmit();
    });
  });

  formulario.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const boton = $("enviar");
    const email = $("email").value.trim();
    const password = $("password").value;

    if (!email || !password) return avisar("Escribe tu correo y contraseña");
    if (modoRegistro && password.length < 8)
      return avisar("La contraseña necesita al menos 8 caracteres");

    boton.disabled = true;
    boton.textContent = "Un momento…";
    try {
      if (modoRegistro) {
        await api.registro({ nombre: $("nombre").value.trim(), email, password });
        avisar("Cuenta creada, entrando…", "ok");
      }
      const { access_token, usuario } = await api.login(email, password);
      sesion.abrir(access_token, usuario);
      contenedor.style.padding = "";
      contenedor.style.maxWidth = "";
      ir(sesion.esPersonal ? "/ordenes" : "/menu");
    } catch (e) {
      avisar(e.message);
      boton.disabled = false;
      boton.textContent = modoRegistro ? "Crear cuenta" : "Entrar";
    }
  });
}
