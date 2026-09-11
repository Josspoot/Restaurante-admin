# Sabor · Restaurante

Aplicación completa para la operación de un restaurante: menú, órdenes, cocina, cobros
y facturación. Backend REST + frontend web, con persistencia en **SQLite**.

- **Backend**: FastAPI + SQLAlchemy, arquitectura por capas (MVC). El equivalente en
  Python a un proyecto de Spring Initializr con `spring-boot-starter-web` +
  `spring-data-jpa` + `spring-boot-starter-security`.
- **Frontend**: HTML + CSS + JavaScript modular, **sin build ni dependencias**. Lo sirve
  la misma aplicación, así que un solo comando levanta todo.

---

## Arranque rápido

> Si vienes de una versión anterior, borra `restaurante.db` y vuelve a correr `seed.py`:
> las órdenes ahora guardan tanda, estado y cuenta por platillo.

```bash
cd restaurante-api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env        # ajusta SECRET_KEY
python seed.py              # crea restaurante.db con menú y usuarios de prueba
uvicorn app.main:app --reload --no-server-header
```

| Dirección | Qué es |
|---|---|
| **http://127.0.0.1:8000/app/** | La aplicación web |
| http://127.0.0.1:8000/docs | Swagger UI: probar la API endpoint por endpoint |

En Swagger dale a **Authorize**, entra con `admin@restaurante.com` / `admin123` y el token
se aplica solo a las siguientes peticiones.

> Si el puerto 8000 está ocupado: `uvicorn app.main:app --reload --port 8010`.

### Cuentas de prueba (las crea `seed.py`)

| Rol | Correo | Contraseña |
|---|---|---|
| ADMIN | admin@restaurante.com | admin123 |
| MESERO | mesero@restaurante.com | mesero123 |
| CLIENTE | cliente@correo.com | cliente123 |

---

## Arquitectura

La petición baja por las capas y nunca las salta. Cada una tiene una única responsabilidad:

```
HTTP  ->  controllers/  ->  services/  ->  repositories/  ->  models/  ->  SQLite
              |               |                |                |
        traduce HTTP    reglas de negocio   consultas SQL    tablas
              |
          schemas/  (DTOs: validan la entrada y forman la respuesta JSON)
```

| Carpeta | Rol en MVC | Equivalente en Spring |
|---|---|---|
| `app/models/` | **Modelo** | `@Entity` (JPA/Hibernate) |
| `app/schemas/` | **Vista** (la vista de una API es su JSON) | DTOs + Bean Validation |
| `app/controllers/` | **Controlador** | `@RestController` |
| `app/services/` | Lógica de negocio | `@Service` |
| `app/repositories/` | Acceso a datos | `@Repository` / `JpaRepository` |
| `app/core/` | Configuración transversal | `application.properties`, `SecurityConfig` |
| `app/api/deps.py` | Inyección de dependencias y roles | DI + `@PreAuthorize` |

### Reglas que valen la pena conocer

- **Los controladores no deciden nada.** Reciben, delegan al servicio y devuelven. Toda regla
  de negocio vive en `services/`, así que se puede probar sin levantar el servidor.
- **Los servicios no saben qué es HTTP.** Lanzan excepciones de dominio
  (`RecursoNoEncontrado`, `ReglaDeNegocio`, `PermisoDenegado`) y `main.py` las traduce a
  404 / 409 / 403. Es el patrón `@ControllerAdvice`.
- **Dinero siempre en `Decimal`**, nunca `float`, redondeado con criterio comercial
  (`app/core/dinero.py`). En JSON viaja como *string* (`"417.60"`) para no perder precisión:
  en el front parséalo con `parseFloat()` o una librería de decimales.
- **Los precios se congelan al ordenar.** `OrdenItem` guarda una copia del precio del
  producto, así que subir el menú mañana no altera las facturas de hoy.
- **Los totales se recalculan en un solo lugar** (`OrdenService._recalcular`). No hay forma de
  que un total quede desincronizado de sus items.

---

## Modelo de datos

```
Categoria 1---N Producto
                   |
                   N
                   |
Usuario 1---N  Orden 1---N OrdenItem
 (cliente)       |
 (mesero)        1---N Pago
```

`Orden` guarda `subtotal`, `impuestos` y `total` ya calculados; `total_pagado`, `saldo`
y `pagada` se derivan de los pagos y no se almacenan.

Cada `OrdenItem` lleva además tres campos que sostienen el flujo de una mesa real:

| Campo | Para qué |
|---|---|
| `tanda` | Ronda en que se pidió. Todo lo que sale junto a la cocina comparte tanda |
| `estado` | Avance de ese platillo en concreto |
| `cuenta` | A qué cuenta se le carga al dividir la mesa |

### Ciclo de vida

```
PENDIENTE ──> EN_PREPARACION ──> LISTA ──> ENTREGADA
    │                │              │
    └────────────────┴──────────────┴──> CANCELADA
```

**El estado de la orden es el de su platillo menos avanzado.** No se guarda a mano: se
recalcula solo. De ahí sale el comportamiento de una mesa que sigue pidiendo.

- `ENTREGADA` y `CANCELADA` son terminales para la orden completa.
- No se cancela una orden que ya tiene pagos: primero hay que reembolsar.

### Pedir más en una mesa abierta

Comer en el local admite platillos **en cualquier momento**; para llevar y a domicilio se
congelan en cuanto la comanda entra a cocina (`Orden.ampliable` decide, y es una sola regla
para toda la aplicación).

Cuando se agrega algo a una orden que ya salió a cocina:

1. El platillo entra en una **tanda nueva**, en estado `PENDIENTE`.
2. La cocina la ve como **una comanda aparte** — con su hora y su propio botón — aunque la
   tanda anterior ya esté entregada.
3. La orden **retrocede** al estado del platillo más atrasado: una mesa `ENTREGADA` que pide
   postre vuelve a `PENDIENTE`, porque otra vez hay algo por preparar.
4. Todo sigue perteneciendo a la misma mesa y **se cobra junto** al final.

Cada tanda avanza sola con `PATCH /ordenes/{id}/tandas/{n}/estado`, paso a paso y sin
arrastrar a las demás. `PATCH /ordenes/{id}/estado` sigue existiendo para mover la orden
completa de un jalón.

Lo que ya está en cocina no se puede quitar: solo se borran los platillos en `PENDIENTE`.

### Cuentas divididas

Cada platillo se carga a una cuenta (`1` por defecto). Se mueve con
`PATCH /ordenes/{id}/items/{item_id}/cuenta` y `GET /ordenes/{id}/cuentas` devuelve cuánto
debe y cuánto lleva pagado cada una.

- Un pago siempre va **contra una cuenta**. Si la mesa está dividida hay que decir cuál;
  con una sola cuenta se resuelve sola.
- Una cuenta no puede pagar más de lo suyo, aunque la mesa deba más.
- **El IVA se redondea cuenta por cuenta**, así que lo que suman las cuentas cuadra al
  centavo con el total de la orden.
- No se mueve un platillo de una cuenta que ya recibió dinero: descuadraría lo cobrado
  contra lo consumido.
- `GET /ordenes/{id}/factura?cuenta=2` imprime el ticket de esa cuenta sola.

### Cerrar la mesa

Estar entregada y estar pagada son cosas distintas: la comida puede llevarse a la mesa y
la cuenta seguir abierta. Por eso el cierre es un tercer eje, con su propio campo
(`cerrada_en`) en vez de un estado más en la máquina de cocina.

`POST /ordenes/{id}/cerrar` exige que no falte nada. Qué falta lo define una sola propiedad,
`Orden.pendientes_para_cerrar`, que el servicio usa para rechazar y la interfaz para pintar
la lista de requisitos — la regla no está escrita dos veces.

Una vez cerrada, la orden no admite platillos, cobros ni cambios de estado.
`POST /ordenes/{id}/reabrir` la devuelve a la vida, solo para ADMIN.

En la lista de órdenes hay tres filtros independientes —**Estado**, **Cobro** y **Mesa**—
más un resumen con cuántas quedan por cobrar y cuánto dinero suman.

### Avisos al mesero

`GET /ordenes/avisos` devuelve las tandas que la cocina ya sacó y siguen sin llevarse a la
mesa. Un mesero solo ve las de sus propias órdenes; un administrador las ve todas.

El front lo consulta cada 20 s desde la campana de la cabecera: cuenta los pendientes, avisa
con un mensaje cuando aparece algo nuevo y deja marcar la entrega desde el propio panel. Va
por sondeo y no por WebSockets a propósito: es un aviso que tolera medio minuto de retraso y
no justifica mantener un canal abierto. Lo ya anunciado se recuerda en `localStorage`, así
que recargar la página no repite los avisos.

### Propinas

Se mandan de una de dos formas, nunca las dos a la vez (si llegan juntas es un `422`):

| Campo | Ejemplo | Resultado |
|---|---|---|
| `propina` | `"25.00"` | Importe tal cual |
| `propina_porcentaje` | `"15"` | 15 % **del monto de ese pago** |

Al dividir la mesa esto importa: un 15 % en la cuenta 1 se calcula sobre lo que paga esa
persona, no sobre el total. El porcentaje usado se guarda para poder explicarlo en el ticket.

---

## Endpoints

Todos cuelgan de `/api/v1`.

### Autenticación
| Método | Ruta | Acceso | Qué hace |
|---|---|---|---|
| POST | `/auth/registro` | público | Alta de cliente (siempre rol CLIENTE) |
| POST | `/auth/login` | público | Login OAuth2 form-data (el de Swagger) |
| POST | `/auth/login-json` | público | Login con JSON — **usa este desde el front** |
| GET | `/auth/yo` | autenticado | Perfil del dueño del token |
| POST | `/auth/usuarios` | ADMIN | Alta de meseros y administradores |

### Menú
| Método | Ruta | Acceso |
|---|---|---|
| GET | `/categorias` · `/categorias/{id}` | público |
| POST · PATCH · DELETE | `/categorias` | ADMIN |
| GET | `/productos?categoria_id=&disponible=&texto=&skip=&limit=` | público |
| GET | `/productos/{id}` | público |
| POST · PATCH · DELETE | `/productos` | ADMIN |

### Órdenes y cobros
| Método | Ruta | Acceso | Qué hace |
|---|---|---|---|
| GET | `/ordenes?estado=&mesa=&pagada=&cerrada=` | autenticado | El cliente solo ve las suyas |
| GET | `/ordenes/{id}` | autenticado | |
| POST | `/ordenes` | autenticado | Crea la comanda y calcula totales |
| POST | `/ordenes/{id}/items` | autenticado | Agrega platillo; abre tanda nueva si ya salió a cocina |
| DELETE | `/ordenes/{id}/items/{item_id}` | autenticado | Solo lo que sigue `PENDIENTE` |
| PATCH | `/ordenes/{id}/items/{item_id}/cuenta` | personal | Mueve un platillo de cuenta |
| GET | `/ordenes/{id}/cuentas` | autenticado | Total y saldo de cada cuenta |
| GET | `/ordenes/{id}/tandas` | autenticado | Las rondas y su avance |
| PATCH | `/ordenes/{id}/estado` | personal | Avanza la orden completa |
| PATCH | `/ordenes/{id}/tandas/{n}/estado` | personal | Avanza una sola tanda |
| GET | `/ordenes/cocina` | personal | Tandas pendientes de sacar |
| GET | `/ordenes/avisos` | personal | Tandas listas sin entregar (avisos del mesero) |
| POST | `/ordenes/{id}/cerrar` | personal | Da la mesa por terminada |
| POST | `/ordenes/{id}/reabrir` | ADMIN | Deshace un cierre |
| POST | `/ordenes/{id}/cancelar` | autenticado | |
| POST | `/ordenes/{id}/pagos` | personal | Cobro contra una cuenta, con propina |
| GET | `/ordenes/{id}/factura?cuenta=` | autenticado | Ticket de la mesa o de una cuenta |

### Códigos de error

| Código | Significado |
|---|---|
| 401 | Sin token, token inválido o expirado |
| 403 | Autenticado pero el rol no alcanza |
| 404 | El recurso no existe |
| 409 | La operación viola una regla de negocio |
| 422 | El JSON no cumple el esquema (lo valida Pydantic) |

Los errores de dominio responden con la misma forma:

```json
{ "error": "ReglaDeNegocio", "detalle": "No se puede pasar de PENDIENTE a ENTREGADA. Estados permitidos: EN_PREPARACION, CANCELADA" }
```

---

## Frontend

Vive en `frontend/` y lo sirve el propio FastAPI en `/app/`. Es JavaScript modular nativo:
**no hay `npm install`, ni bundler, ni paso de compilación** — editas un archivo, recargas
el navegador y ya está.

```
frontend/
├── index.html            cascarón: cabecera, contenedor de vista y avisos
├── css/estilos.css       todo el diseño, con la paleta en variables CSS
└── js/
    ├── app.js            arranque: define rutas y mantiene la cabecera al día
    ├── router.js         router por hash (#/ruta) con guardas por rol
    ├── api.js            único lugar que hace fetch; añade el token y traduce errores
    ├── sesion.js         token y usuario en localStorage
    ├── carrito.js        comanda en construcción, también persistida
    ├── ui.js             formato de dinero/fechas, avisos, modales
    └── vistas/           una vista por pantalla
```

### Pantallas

| Ruta | Quién entra | Qué hace |
|---|---|---|
| `#/login` | público | Entrar o registrarse. Trae botones de acceso rápido para las cuentas demo |
| `#/menu` | todos | Catálogo con búsqueda y filtros; arma la comanda y la envía a cocina |
| `#/ordenes` | todos | Lista filtrable por estado. El cliente solo ve las suyas |
| `#/ordenes/:id` | todos | Detalle por tandas: avanzar, dividir cuentas, cobrar, ticket |
| `#/menu?orden=N` | todos | El mismo menú, pero sumando platillos a una mesa abierta |
| `#/cocina` | personal | Tablero por tandas, refrescado cada 15 s |
| *(cabecera)* | personal | Campana de avisos: tandas listas para llevar a la mesa |
| `#/admin` | ADMIN | Alta y edición de platillos y categorías |

### El diseño

**Sin emojis.** Todos los símbolos son SVG de línea definidos en `js/iconos.js`: heredan el
color del texto, se alinean al píxel y se ven igual en cualquier sistema operativo, cosa que
un emoji no hace. Se usan con `icono("candado", { tam: 18 })`.

**Los controles responden al tacto.** Al pulsar, un botón se hunde un 4 % y suelta una onda
desde el punto exacto del clic. El efecto está delegado una sola vez en `app.js` en vez de
engancharse control por control, porque la interfaz se repinta constantemente. Se desactiva
solo si el sistema pide movimiento reducido.

Paleta de tres familias, definida como variables CSS al inicio de `estilos.css`:

| Rol | Color | Dónde se usa |
|---|---|---|
| Rojo `#d62828` | acción | Botones primarios, precios totales, estado activo |
| Amarillo `#ffb703` | acento | Categorías, insignias, resaltados, avatar |
| Blanco cálido `#fffbf6` | fondo | Lienzo; las tarjetas van en blanco puro encima |

Para cambiar toda la identidad visual basta editar el bloque `:root`. El resto del sistema
—bordes suaves, esquinas redondeadas, una sola sombra, tipografía del sistema— se apoya en
esas mismas variables.

### Detalles que vale la pena conocer

- **La interfaz nunca inventa reglas.** El grafo de estados de `orden_detalle.js` es una
  copia del que aplica el backend: la vista solo ofrece los botones que el servidor va a
  aceptar. Si cambias una regla, cámbiala en los dos lados.
- **El dinero se muestra con `Intl.NumberFormat`** y llega como string desde la API.
  El total de la comanda que ves antes de enviar es una estimación local; **el total real
  siempre lo calcula el backend** al crear la orden.
- **Todo lo que viene del servidor pasa por `esc()`** antes de entrar al HTML, para que el
  nombre de un platillo no pueda inyectar markup.
- **Si el token expira**, `api.js` cierra la sesión y te manda al login sin que cada vista
  tenga que ocuparse.

### Servirlo aparte del backend

Si prefieres el front en otro puerto (Live Server, `python -m http.server`, etc.), abre
`frontend/index.html` y apunta la API a mano:

```html
<script>window.API_BASE = "http://127.0.0.1:8000/api/v1";</script>
```

CORS ya viene abierto para desarrollo (`CORS_ORIGINS` en `.env`); ciérralo al dominio real
antes de publicar.

---

## Seguridad

El proyecto pasó una auditoría completa. Lo que hay que saber para no deshacerla:

### Antes de publicarlo

1. **Pon `ENTORNO="produccion"` en `.env`.** Con eso la aplicación se niega a arrancar sin
   una `SECRET_KEY` propia y cierra `/docs`, `/redoc` y `/openapi.json`.
2. **Genera tu llave** y ponla en `.env` (nunca en el código):
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```
3. **Ajusta `CORS_ORIGINS`** al dominio real. Nunca `"*"`: junto con credenciales, permite
   que cualquier web lea las respuestas de la API en nombre del usuario.
4. **Arranca uvicorn con `--no-server-header`** para no anunciar servidor y versión.
5. **Sirve por HTTPS.** El token viaja en la cabecera `Authorization`; sin TLS va en claro.

**Las cuentas de prueba solo existen en desarrollo.** El endpoint `/salud` devuelve
`demo: true|false` según `ENTORNO`, y la pantalla de entrada solo dibuja los accesos rápidos
si el servidor lo autoriza. Con `ENTORNO="produccion"` esos botones no llegan a existir, así
que un usuario administrador de ejemplo no queda a un clic en un servidor público.

### Lo que ya está puesto

| Defensa | Dónde |
|---|---|
| Llave de firma nunca por defecto | `core/config.py` |
| Freno de fuerza bruta (por IP y por cuenta) | `core/limitador.py` |
| Login de tiempo constante | `core/security.py` |
| JWT con algoritmo fijo y `exp`/`sub` obligatorios | `core/security.py` |
| Cabeceras de seguridad y CSP | `main.py` |
| CORS con lista blanca | `main.py` |
| Contraseñas con bcrypt, mínimo 8 caracteres | `core/security.py`, `schemas/usuario.py` |
| Escapado de todo lo que se pinta en el navegador | `js/ui.js` (`esc`) |

**El rol viene de la base de datos, no del token.** El token lleva un `rol` informativo,
pero `get_usuario_actual` relee al usuario en cada petición: un token manipulado que diga
`ADMIN` sigue teniendo los permisos del usuario real, y una cuenta desactivada deja de
entrar aunque su token siga vigente.

**La CSP prohíbe el código en línea.** Por eso no hay ningún `<script>` dentro del HTML ni
atributos `onclick`: la configuración del cliente vive en `js/config.js`. Si añades un
script en línea, el navegador lo bloqueará.

### Limitaciones conocidas

- **El limitador vive en memoria.** Con un solo proceso basta; con varios *workers* cada uno
  llevaría su propia cuenta. Ahí toca moverlo a Redis o al proxy de entrada.
- **El token no se puede revocar** antes de que expire (8 h). Cerrar sesión solo lo borra del
  navegador. Una lista de revocación o tokens de refresco lo resolverían.
- **El registro dice si un correo ya existe** (409). Es el precio de un mensaje útil; queda
  compensado con el límite de 5 registros por IP cada 10 minutos.
- **Dos cobros simultáneos** sobre la misma cuenta podrían pasar los dos la validación de
  saldo. Con SQLite y este volumen es teórico, pero existe.
- **El token se guarda en `localStorage`**, así que un XSS podría leerlo. Por eso la CSP y el
  escapado son la primera línea, no la última.

### Volver a auditar

```bash
pip install pip-audit
pip-audit                  # vulnerabilidades conocidas en las dependencias
pytest tests/test_seguridad.py -q
```

---

## Despliegue

### Por qué no funciona en Vercel

Vercel ejecuta funciones *serverless*: el disco es de solo lectura salvo `/tmp`, y cada
petición puede caer en una instancia distinta. Esta aplicación crea su base SQLite al
arrancar, así que la función revienta antes de atender nada
(`sqlite3.OperationalError: unable to open database file`). Y aunque se apuntara a `/tmp`,
los datos morirían entre peticiones.

**SQLite necesita un proceso con disco.** Para eso sirven Render, Railway o Fly.io. Si
quieres quedarte en Vercel, hay que cambiar a un PostgreSQL alojado: como todo pasa por
SQLAlchemy, sería cambiar `DATABASE_URL`, añadir `psycopg[binary]` y crear el punto de
entrada `api/index.py`.

### Render (plan gratuito)

El repositorio trae `render.yaml`. En Render: **New > Blueprint**, apunta a este
repositorio y listo. Levanta con:

```
uvicorn app.main:app --host 0.0.0.0 --port $PORT --no-server-header
```

### Variables de entorno

| Variable | Para qué | Valor sugerido |
|---|---|---|
| `SECRET_KEY` | Firma de los tokens. **Sin ella la app no arranca en producción** | generada por la plataforma |
| `ENTORNO` | `produccion` exige la llave y activa HSTS | `produccion` |
| `CONFIAR_PROXY` | Lee la IP real de `X-Forwarded-For` | `true` **solo si hay un proxy delante** |
| `SEMBRAR_INICIAL` | Carga el menú de ejemplo si la base está vacía | `true` la primera vez |
| `ADMIN_PASSWORD` | Contraseña del administrador al sembrar | la tuya |

| `DOCS_PUBLICAS` | Abre `/docs` aunque sea producción | `true` para una demo |
| `DEMO_ACTIVO` | Muestra los accesos rápidos del login | `true` para una demo |

Al definir `ADMIN_PASSWORD`, el acceso rápido de **Admin** desaparece del login: ese botón
manda la contraseña de ejemplo y ya no sería la correcta. El administrador entra escribiendo
su correo y la contraseña que hayas puesto. Los accesos de mesero y cliente siguen ahí.

`DOCS_PUBLICAS` y `DEMO_ACTIVO` son interruptores de tres estados: si no los defines,
siguen al entorno (abiertos en desarrollo, cerrados en producción). Definirlos manda sobre
eso, lo que permite desplegar con `ENTORNO="produccion"` —conservando la exigencia de llave
propia y las cabeceras de seguridad— y aun así dejar Swagger y las cuentas de prueba
visibles para una presentación.

### Lo que hay que saber del plan gratuito

- **El disco se borra en cada despliegue.** Con `SEMBRAR_INICIAL=true` la base se vuelve a
  llenar con el menú de ejemplo, pero las órdenes creadas se pierden. Para conservarlas hace
  falta un disco persistente (de pago) o mover la base a PostgreSQL.
- **El servicio se duerme tras un rato sin tráfico** y la primera petición tarda unos
  segundos en despertarlo.

---

## Cómo lo consume un front

```js
const API = "http://127.0.0.1:8000/api/v1";

// 1. Login
const { access_token } = await fetch(`${API}/auth/login-json`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ email: "mesero@restaurante.com", password: "mesero123" }),
}).then(r => r.json());

// 2. Menú (público, no necesita token)
const menu = await fetch(`${API}/productos?disponible=true`).then(r => r.json());

// 3. Crear una orden
const orden = await fetch(`${API}/ordenes`, {
  method: "POST",
  headers: { "Content-Type": "application/json", Authorization: `Bearer ${access_token}` },
  body: JSON.stringify({
    tipo: "LOCAL",
    mesa: 7,
    items: [{ producto_id: 4, cantidad: 2, notas: "sin cebolla" }],
  }),
}).then(r => r.json());

console.log(orden.numero, orden.total); // ORD-20260909-0001  417.60
```

También hay una demo en shell: `./scripts/demo.sh` (recorre el flujo completo con `curl`).

---

## Pruebas

```bash
pip install -r requirements-dev.txt
pytest -q
```

60 pruebas de extremo a extremo, cada una contra una base SQLite temporal:

- **Base**: totales con IVA, transiciones inválidas, permisos por rol, producto agotado,
  sobrepago rechazado y generación de la factura.
- **Tandas**: agregar con la cocina trabajando, que para llevar sí se cierre, que la cocina
  vea las tandas por separado, que una avance sin arrastrar a la otra y que no se pueda
  quitar lo que ya se está cocinando.
- **Cuentas**: dividir la mesa, mover platillos, cobrar una cuenta dejando la otra abierta,
  y el bloqueo de mover platillos de una cuenta ya pagada.
- **Propinas**: por porcentaje, por importe, las dos juntas rechazadas, y que el porcentaje
  se calcule sobre lo que paga cada quien al dividir.
- **Cierre**: que no se cierre sin entregar ni cobrar, el caso de entregada-pero-sin-pagar,
  que una mesa cerrada no acepte nada más, y que solo ADMIN pueda reabrirla.
- **Avisos**: que cada mesero vea solo los suyos, que desaparezcan al entregar y que se
  emitan por tanda.
- **Seguridad** (`test_seguridad.py`): bloqueo por fuerza bruta, tokens falsificados,
  `alg: none`, tokens caducados, escalada de rol, contraseñas cortas, fuga de correos y
  cabeceras de respuesta.

El frontend se verificó manejando un navegador Chromium por CDP, en tres recorridos
(29 + 24 + 30 comprobaciones): el flujo original, las tandas y cuentas, y el cierre con
avisos. Incluye una comprobación de que no queda ningún emoji en el DOM. Sin errores de
consola ni de red.

---

## Siguientes pasos sugeridos

- **Migraciones**: hoy las tablas se crean con `create_all` (bien para desarrollo). Para
  producción, agrega Alembic — el equivalente a Flyway/Liquibase.
- **Mesas y reservaciones**: entidad `Mesa` con estado, y `Reservacion` con fecha/hora.
- **Refresh tokens**: hoy el access token dura 8 horas y no hay renovación.
- **Reembolsos**: hoy no se puede anular un cobro, así que una orden con un pago mal
  registrado no se puede cancelar. Es el hueco más grande que queda.
- **Reportes**: ventas por día, productos más vendidos, propinas por mesero.
- **Tiempo real**: hoy la cocina consulta cada 15 s y los avisos cada 20 s; con WebSockets
  llegarían al instante y sin peticiones en vano.
- **Corte de caja**: agrupar las mesas cerradas por turno y cuadrar el efectivo.
- **Cambiar de motor**: como todo pasa por SQLAlchemy, migrar a PostgreSQL es solo cambiar
  `DATABASE_URL`.
