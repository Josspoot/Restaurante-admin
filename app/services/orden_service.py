"""Reglas de negocio de las ordenes: armado, tandas, cuentas y ciclo de vida."""
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dinero import CERO, redondear
from app.core.exceptions import PermisoDenegado, RecursoNoEncontrado, ReglaDeNegocio
from app.models import (
    AVANCE, EstadoItem, EstadoOrden, Orden, OrdenItem, RolUsuario, Usuario,
)
from app.repositories import OrdenRepo, ProductoRepo, UsuarioRepo
from app.schemas.orden import (
    ComandaCocina, CuentaResumen, OrdenCrear, OrdenItemCrear, OrdenItemRespuesta, TandaResumen,
)

# Maquina de estados de la orden: de que estado se puede pasar a cuales.
TRANSICIONES: dict[EstadoOrden, set[EstadoOrden]] = {
    EstadoOrden.PENDIENTE: {EstadoOrden.EN_PREPARACION, EstadoOrden.CANCELADA},
    EstadoOrden.EN_PREPARACION: {EstadoOrden.LISTA, EstadoOrden.CANCELADA},
    EstadoOrden.LISTA: {EstadoOrden.ENTREGADA, EstadoOrden.CANCELADA},
    EstadoOrden.ENTREGADA: set(),
    EstadoOrden.CANCELADA: set(),
}

# El estado de la orden es el del platillo menos avanzado, asi que ambos
# enums se corresponden uno a uno.
ITEM_A_ORDEN: dict[EstadoItem, EstadoOrden] = {
    EstadoItem.PENDIENTE: EstadoOrden.PENDIENTE,
    EstadoItem.EN_PREPARACION: EstadoOrden.EN_PREPARACION,
    EstadoItem.LISTA: EstadoOrden.LISTA,
    EstadoItem.ENTREGADA: EstadoOrden.ENTREGADA,
}

class OrdenService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = OrdenRepo(db)
        self.productos = ProductoRepo(db)
        self.usuarios = UsuarioRepo(db)

    # ------------------------------------------------------------------ lectura

    def obtener(self, id_: int) -> Orden:
        orden = self.repo.obtener(id_)
        if not orden:
            raise RecursoNoEncontrado(f"No existe la orden {id_}")
        return orden

    def obtener_para(self, id_: int, usuario: Usuario) -> Orden:
        """Un cliente solo puede ver sus propias ordenes; el personal ve todas."""
        orden = self.obtener(id_)
        if usuario.rol == RolUsuario.CLIENTE and orden.cliente_id != usuario.id:
            raise PermisoDenegado("Esta orden no te pertenece")
        return orden

    def listar(self, usuario: Usuario, **filtros) -> list[Orden]:
        if usuario.rol == RolUsuario.CLIENTE:
            filtros["cliente_id"] = usuario.id
        return self.repo.buscar(**filtros)

    # ------------------------------------------------------------------ escritura

    def crear(self, datos: OrdenCrear, usuario: Usuario) -> Orden:
        es_personal = usuario.rol in (RolUsuario.ADMIN, RolUsuario.MESERO)

        if es_personal:
            cliente_id = datos.cliente_id
            if cliente_id is not None and not self.usuarios.obtener(cliente_id):
                raise RecursoNoEncontrado(f"No existe el usuario {cliente_id}")
            mesero_id = usuario.id
        else:
            # Un cliente siempre crea la orden a su propio nombre.
            cliente_id = usuario.id
            mesero_id = None

        orden = Orden(
            numero=self.repo.siguiente_numero(),
            tipo=datos.tipo,
            mesa=datos.mesa,
            notas=datos.notas,
            cliente_id=cliente_id,
            mesero_id=mesero_id,
            estado=EstadoOrden.PENDIENTE,
        )
        for linea in datos.items:
            orden.items.append(self._construir_item(linea, tanda=1))

        self._recalcular(orden)
        return self.repo.guardar(orden)

    def agregar_item(self, id_: int, linea: OrdenItemCrear, usuario: Usuario) -> Orden:
        """Agrega un platillo. Si la comanda ya salio a cocina, abre una tanda nueva."""
        orden = self.obtener_para(id_, usuario)
        self._exigir_ampliable(orden)

        tanda = self._tanda_destino(orden)
        existente = next(
            (
                i
                for i in orden.items
                if i.producto_id == linea.producto_id
                and i.notas == linea.notas
                and i.cuenta == linea.cuenta
                and i.tanda == tanda
                and i.estado == EstadoItem.PENDIENTE
            ),
            None,
        )
        if existente:
            # Mismo platillo, misma nota, misma cuenta y aun sin cocinar: se acumula.
            existente.cantidad += linea.cantidad
            existente.subtotal = redondear(existente.precio_unitario * existente.cantidad)
        else:
            orden.items.append(self._construir_item(linea, tanda=tanda))

        self._recalcular(orden)
        self._sincronizar_estado(orden)
        return self.repo.guardar(orden)

    def quitar_item(self, id_: int, item_id: int, usuario: Usuario) -> Orden:
        orden = self.obtener_para(id_, usuario)
        self._exigir_abierta(orden)
        if orden.estado == EstadoOrden.CANCELADA:
            raise ReglaDeNegocio("La orden esta cancelada")

        item = next((i for i in orden.items if i.id == item_id), None)
        if not item:
            raise RecursoNoEncontrado(f"La orden {orden.numero} no tiene el item {item_id}")
        if item.estado != EstadoItem.PENDIENTE:
            raise ReglaDeNegocio(
                f"'{item.nombre_producto}' ya esta en cocina y no se puede quitar"
            )
        if len(orden.items) == 1:
            raise ReglaDeNegocio("Una orden no puede quedarse sin platillos; cancélala en su lugar")
        if self._cuenta_con_pagos(orden, item.cuenta):
            raise ReglaDeNegocio(
                f"La cuenta {item.cuenta} ya tiene pagos; no se puede cambiar lo que incluye"
            )

        orden.items.remove(item)
        self._recalcular(orden)
        self._sincronizar_estado(orden)
        return self.repo.guardar(orden)

    def cambiar_estado(self, id_: int, nuevo: EstadoOrden, usuario: Usuario) -> Orden:
        """Avanza la orden completa: arrastra todos los platillos que van atras."""
        orden = self.obtener_para(id_, usuario)
        self._exigir_abierta(orden)
        if nuevo == orden.estado:
            return orden
        if nuevo not in TRANSICIONES[orden.estado]:
            permitidos = ", ".join(e.value for e in TRANSICIONES[orden.estado]) or "ninguno"
            raise ReglaDeNegocio(
                f"No se puede pasar de {orden.estado.value} a {nuevo.value}. "
                f"Estados permitidos: {permitidos}"
            )

        if nuevo == EstadoOrden.CANCELADA:
            if orden.pagos:
                raise ReglaDeNegocio(
                    "La orden ya tiene pagos registrados; hay que reembolsarlos antes de cancelar"
                )
            orden.estado = EstadoOrden.CANCELADA
            return self.repo.guardar(orden)

        destino = EstadoItem(nuevo.value)
        for item in orden.items:
            if AVANCE[item.estado] < AVANCE[destino]:
                item.estado = destino

        self._sincronizar_estado(orden)
        return self.repo.guardar(orden)

    def cambiar_estado_tanda(
        self, id_: int, tanda: int, nuevo: EstadoItem, usuario: Usuario
    ) -> Orden:
        """Avanza una sola tanda. Es lo que usa la pantalla de cocina."""
        orden = self.obtener_para(id_, usuario)
        self._exigir_abierta(orden)
        if orden.estado == EstadoOrden.CANCELADA:
            raise ReglaDeNegocio("La orden esta cancelada")

        items = [i for i in orden.items if i.tanda == tanda]
        if not items:
            raise RecursoNoEncontrado(f"La orden {orden.numero} no tiene la tanda {tanda}")

        actual = self._estado_de(items)
        if AVANCE[nuevo] != AVANCE[actual] + 1:
            raise ReglaDeNegocio(
                f"La tanda {tanda} va en {actual.value} y debe avanzar paso a paso"
            )

        for item in items:
            if AVANCE[item.estado] < AVANCE[nuevo]:
                item.estado = nuevo

        self._sincronizar_estado(orden)
        return self.repo.guardar(orden)

    def asignar_cuenta(self, id_: int, item_id: int, cuenta: int, usuario: Usuario) -> Orden:
        """Mueve un platillo de cuenta al dividir la mesa."""
        orden = self.obtener_para(id_, usuario)
        self._exigir_abierta(orden)
        if orden.estado == EstadoOrden.CANCELADA:
            raise ReglaDeNegocio("La orden esta cancelada")

        item = next((i for i in orden.items if i.id == item_id), None)
        if not item:
            raise RecursoNoEncontrado(f"La orden {orden.numero} no tiene el item {item_id}")
        if item.cuenta == cuenta:
            return orden

        # Si cualquiera de las dos cuentas ya recibio dinero, moverlo descuadraria
        # lo cobrado contra lo consumido.
        for numero in (item.cuenta, cuenta):
            if self._cuenta_con_pagos(orden, numero):
                raise ReglaDeNegocio(
                    f"La cuenta {numero} ya tiene pagos; reembolsalos antes de mover platillos"
                )

        item.cuenta = cuenta
        self._compactar_cuentas(orden)
        self._recalcular(orden)
        return self.repo.guardar(orden)

    def cancelar(self, id_: int, usuario: Usuario) -> Orden:
        return self.cambiar_estado(id_, EstadoOrden.CANCELADA, usuario)

    # --------------------------------------------------------------- cierre

    def cerrar(self, id_: int, usuario: Usuario) -> Orden:
        """Da la mesa por terminada: todo entregado y todo cobrado."""
        orden = self.obtener_para(id_, usuario)
        if orden.cerrada:
            raise ReglaDeNegocio(f"La orden {orden.numero} ya estaba cerrada")

        faltas = orden.pendientes_para_cerrar
        if faltas:
            raise ReglaDeNegocio(f"Todavía no se puede cerrar la mesa: {'; '.join(faltas).lower()}")

        orden.cerrada_en = datetime.now(timezone.utc)
        orden.cerrada_por_id = usuario.id
        return self.repo.guardar(orden)

    def reabrir(self, id_: int, usuario: Usuario) -> Orden:
        """Deshace un cierre. Solo ADMIN, para corregir un error."""
        orden = self.obtener_para(id_, usuario)
        if not orden.cerrada:
            raise ReglaDeNegocio(f"La orden {orden.numero} no está cerrada")
        orden.cerrada_en = None
        orden.cerrada_por_id = None
        return self.repo.guardar(orden)

    # -------------------------------------------------------------- avisos

    def listas_para_entregar(self, usuario: Usuario) -> list[ComandaCocina]:
        """Tandas que la cocina ya sacó y siguen sin llevarse a la mesa.

        Un mesero solo ve las de sus propias ordenes; un admin las ve todas.
        """
        mias = usuario.rol == RolUsuario.MESERO
        return [
            comanda
            for comanda in self.cocina()
            if comanda.estado == EstadoItem.LISTA
            and (not mias or comanda.mesero_id == usuario.id)
        ]

    # -------------------------------------------------------------------- cuentas

    def desglose(self, orden: Orden) -> list[CuentaResumen]:
        """Cuanto debe cada cuenta y cuanto lleva pagado."""
        resumenes: list[CuentaResumen] = []
        for numero in sorted({i.cuenta for i in orden.items}):
            items = [i for i in orden.items if i.cuenta == numero]
            subtotal = redondear(sum((i.subtotal for i in items), CERO))
            impuestos = redondear(subtotal * Decimal(str(settings.IVA)))
            total = redondear(subtotal + impuestos)
            pagos = [p for p in orden.pagos if p.cuenta == numero]
            pagado = redondear(sum((p.monto for p in pagos), CERO))
            propina = redondear(sum((p.propina for p in pagos), CERO))
            resumenes.append(
                CuentaResumen(
                    numero=numero,
                    items=[OrdenItemRespuesta.model_validate(i) for i in items],
                    subtotal=subtotal,
                    impuestos=impuestos,
                    total=total,
                    pagado=pagado,
                    propina=propina,
                    saldo=redondear(total - pagado),
                    pagada=pagado >= total,
                )
            )
        return resumenes

    def cuenta(self, orden: Orden, numero: int) -> CuentaResumen:
        for resumen in self.desglose(orden):
            if resumen.numero == numero:
                return resumen
        raise RecursoNoEncontrado(f"La orden {orden.numero} no tiene la cuenta {numero}")

    # -------------------------------------------------------------------- tandas

    def tandas(self, orden: Orden) -> list[TandaResumen]:
        """Las rondas de la orden, cada una con su propio avance."""
        return [
            TandaResumen(
                numero=numero,
                estado=self._estado_de(items := [i for i in orden.items if i.tanda == numero]),
                items=[OrdenItemRespuesta.model_validate(i) for i in items],
            )
            for numero in orden.tandas
        ]

    def cocina(self) -> list[ComandaCocina]:
        """Todas las tandas que la cocina todavia tiene que sacar, mas viejas primero.

        Una mesa que pidio postre despues aparece como una comanda aparte, aunque
        su primera tanda ya se haya entregado.
        """
        comandas: list[ComandaCocina] = []
        for orden in self.repo.activas():
            for numero in orden.tandas:
                items = [i for i in orden.items if i.tanda == numero]
                estado = self._estado_de(items)
                if estado == EstadoItem.ENTREGADA:
                    continue
                comandas.append(
                    ComandaCocina(
                        orden_id=orden.id,
                        numero=orden.numero,
                        tipo=orden.tipo,
                        mesa=orden.mesa,
                        tanda=numero,
                        estado=estado,
                        notas=orden.notas,
                        mesero_id=orden.mesero_id,
                        mesero=orden.mesero.nombre if orden.mesero else None,
                        creado_en=min(i.creado_en for i in items),
                        items=[OrdenItemRespuesta.model_validate(i) for i in items],
                    )
                )
        return sorted(comandas, key=lambda c: c.creado_en)

    # ------------------------------------------------------------------ internos

    @staticmethod
    def _estado_de(items: list[OrdenItem]) -> EstadoItem:
        """El avance de un grupo de platillos es el del menos avanzado."""
        return EstadoItem(_estado_por_avance(min(AVANCE[i.estado] for i in items)))

    def _construir_item(self, linea: OrdenItemCrear, tanda: int) -> OrdenItem:
        producto = self.productos.obtener(linea.producto_id)
        if not producto:
            raise RecursoNoEncontrado(f"No existe el producto {linea.producto_id}")
        if not producto.disponible:
            raise ReglaDeNegocio(f"'{producto.nombre}' no está disponible en este momento")

        precio = redondear(producto.precio)
        return OrdenItem(
            producto_id=producto.id,
            cantidad=linea.cantidad,
            precio_unitario=precio,
            subtotal=redondear(precio * linea.cantidad),
            notas=linea.notas,
            cuenta=linea.cuenta,
            tanda=tanda,
            estado=EstadoItem.PENDIENTE,
        )

    @staticmethod
    def _exigir_abierta(orden: Orden) -> None:
        """Una mesa cerrada es historia: no se toca nada de ella."""
        if orden.cerrada:
            raise ReglaDeNegocio(
                f"La orden {orden.numero} está cerrada. Un administrador puede reabrirla."
            )

    @staticmethod
    def _exigir_ampliable(orden: Orden) -> None:
        """La regla vive en Orden.ampliable; aqui solo se traduce a un mensaje."""
        OrdenService._exigir_abierta(orden)
        if orden.ampliable:
            return
        if orden.estado == EstadoOrden.CANCELADA:
            raise ReglaDeNegocio("No se le pueden agregar platillos a una orden cancelada")
        raise ReglaDeNegocio(
            f"Una orden {orden.tipo.value} solo admite cambios mientras está pendiente; "
            f"esta va en {orden.estado.value}. En el local sí se puede pedir más en cualquier momento."
        )

    @staticmethod
    def _tanda_destino(orden: Orden) -> int:
        """La tanda abierta si nada de ella salio a cocina; si no, la siguiente."""
        if not orden.items:
            return 1
        ultima = max(i.tanda for i in orden.items)
        sin_cocinar = all(
            i.estado == EstadoItem.PENDIENTE for i in orden.items if i.tanda == ultima
        )
        return ultima if sin_cocinar else ultima + 1

    @staticmethod
    def _cuenta_con_pagos(orden: Orden, numero: int) -> bool:
        return any(p.cuenta == numero for p in orden.pagos)

    @staticmethod
    def _compactar_cuentas(orden: Orden) -> None:
        """Evita huecos: si la cuenta 2 se queda vacia, la 3 pasa a ser la 2."""
        usadas = sorted({i.cuenta for i in orden.items})
        renumerar = {vieja: nueva for nueva, vieja in enumerate(usadas, start=1)}
        if all(v == k for k, v in renumerar.items()):
            return
        for item in orden.items:
            item.cuenta = renumerar[item.cuenta]
        for pago in orden.pagos:
            if pago.cuenta in renumerar:
                pago.cuenta = renumerar[pago.cuenta]

    def _recalcular(self, orden: Orden) -> None:
        """Unica fuente de verdad de los totales.

        El IVA se redondea cuenta por cuenta para que la suma de las cuentas
        cuadre al centavo con el total de la orden.
        """
        tasa = Decimal(str(settings.IVA))
        subtotal = CERO
        impuestos = CERO
        for numero in sorted({i.cuenta for i in orden.items}):
            sub_cuenta = sum((i.subtotal for i in orden.items if i.cuenta == numero), CERO)
            subtotal += sub_cuenta
            impuestos += redondear(sub_cuenta * tasa)
        orden.subtotal = redondear(subtotal)
        orden.impuestos = redondear(impuestos)
        orden.total = redondear(orden.subtotal + orden.impuestos)

    @staticmethod
    def _sincronizar_estado(orden: Orden) -> None:
        """La orden va tan atrasada como su platillo menos avanzado."""
        if orden.estado == EstadoOrden.CANCELADA or not orden.items:
            return
        orden.estado = ITEM_A_ORDEN[OrdenService._estado_de(orden.items)]


def _estado_por_avance(valor: int) -> str:
    for estado, avance in AVANCE.items():
        if avance == valor:
            return estado.value
    raise ValueError(f"Avance desconocido: {valor}")
