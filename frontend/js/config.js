/**
 * Configuración del cliente.
 *
 * Vive en un archivo propio y no en un <script> dentro del HTML porque la
 * Content-Security-Policy de la aplicación prohíbe el código en línea: es
 * justo lo que impide que un XSS inyecte y ejecute un script.
 *
 * Déjalo en null si el front lo sirve el propio FastAPI (se detecta el origen).
 * Ponle la URL completa si lo sirves aparte, por ejemplo:
 *   window.API_BASE = "http://127.0.0.1:8010/api/v1";
 */
window.API_BASE = null;
