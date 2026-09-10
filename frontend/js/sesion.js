/**
 * Estado de la sesion: token JWT y usuario, persistidos en localStorage
 * para que un F5 no te saque de la aplicacion.
 */
const CLAVE_TOKEN = "sabor.token";
const CLAVE_USUARIO = "sabor.usuario";

function leer(clave) {
  try {
    const crudo = localStorage.getItem(clave);
    return crudo ? JSON.parse(crudo) : null;
  } catch {
    return null;
  }
}

export const sesion = {
  token: leer(CLAVE_TOKEN),
  usuario: leer(CLAVE_USUARIO),

  abrir(token, usuario) {
    this.token = token;
    this.usuario = usuario;
    try {
      localStorage.setItem(CLAVE_TOKEN, JSON.stringify(token));
      localStorage.setItem(CLAVE_USUARIO, JSON.stringify(usuario));
    } catch {
      /* modo privado: la sesion vive solo en memoria */
    }
  },

  cerrar() {
    this.token = null;
    this.usuario = null;
    try {
      localStorage.removeItem(CLAVE_TOKEN);
      localStorage.removeItem(CLAVE_USUARIO);
      localStorage.removeItem("sabor.carrito");
    } catch {
      /* ignorar */
    }
  },

  get activa() {
    return Boolean(this.token && this.usuario);
  },
  get rol() {
    return this.usuario?.rol ?? null;
  },
  get esAdmin() {
    return this.rol === "ADMIN";
  },
  get esPersonal() {
    return this.rol === "ADMIN" || this.rol === "MESERO";
  },
};
