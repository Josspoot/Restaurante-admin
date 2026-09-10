"""Cobros por cuenta, propinas y generacion de la factura."""
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dinero import CERO, redondear
from app.core.exceptions import ReglaDeNegocio
from app.models import EstadoOrden, Orden, Pago, Usuario
from app.repositories import OrdenRepo
from app.schemas.pago import Factura, LineaFactura, PagoCrear
from app.services.orden_service import OrdenService


class PagoService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = OrdenRepo(db)
        self.ordenes = OrdenService(db)

    def registrar(self, orden_id: int, datos: PagoCrear, usuario: Usuario) -> Orden:
        orden = self.ordenes.obtener_para(orden_id, usuario)
        self.ordenes._exigir_abierta(orden)

        if orden.estado == EstadoOrden.CANCELADA:
            raise ReglaDeNegocio("No se puede cobrar una orden cancelada")
        if orden.total <= CERO:
            raise ReglaDeNegocio("La orden no tiene importe por cobrar")

        numero = self._resolver_cuenta(orden, datos.cuenta)
        cuenta = self.ordenes.cuenta(orden, numero)

        if cuenta.saldo <= CERO:
            raise ReglaDeNegocio(f"La cuenta {numero} ya está saldada")

        # Sin monto explicito se cobra el saldo completo de esa cuenta.
        monto = redondear(datos.monto) if datos.monto is not None else cuenta.saldo
        if monto > cuenta.saldo:
            raise ReglaDeNegocio(
                f"El monto ${monto} excede el saldo de la cuenta {numero}, que es ${cuenta.saldo}. "
                f"Si el cliente paga de más, registra la diferencia como propina."
            )

        propina, porcentaje = self._calcular_propina(datos, monto)

        orden.pagos.append(
            Pago(
                metodo=datos.metodo,
                monto=monto,
                propina=propina,
                propina_porcentaje=porcentaje,
                cuenta=numero,
                referencia=datos.referencia,
            )
        )
        return self.repo.guardar(orden)

    def factura(self, orden_id: int, usuario: Usuario, cuenta: int | None = None) -> Factura:
        """Ticket de toda la mesa, o de una sola cuenta si se indica cual."""
        orden = self.ordenes.obtener_para(orden_id, usuario)
        total_cuentas = len(orden.cuentas)

        if cuenta is None:
            items = list(orden.items)
            pagos = list(orden.pagos)
            subtotal, impuestos, total = orden.subtotal, orden.impuestos, orden.total
            pagado, propina, saldo = orden.total_pagado, orden.propina_total, orden.saldo
            pagada = orden.pagada
        else:
            resumen = self.ordenes.cuenta(orden, cuenta)
            items = [i for i in orden.items if i.cuenta == cuenta]
            pagos = [p for p in orden.pagos if p.cuenta == cuenta]
            subtotal, impuestos, total = resumen.subtotal, resumen.impuestos, resumen.total
            pagado, propina, saldo = resumen.pagado, resumen.propina, resumen.saldo
            pagada = resumen.pagada

        return Factura(
            orden_numero=orden.numero,
            fecha=orden.creado_en,
            mesa=orden.mesa,
            atendio=orden.mesero.nombre if orden.mesero else None,
            cliente=orden.cliente.nombre if orden.cliente else "Público general",
            cuenta=cuenta,
            total_cuentas=total_cuentas,
            lineas=[
                LineaFactura(
                    cantidad=i.cantidad,
                    descripcion=i.nombre_producto,
                    precio_unitario=i.precio_unitario,
                    importe=i.subtotal,
                )
                for i in items
            ],
            subtotal=subtotal,
            tasa_iva=Decimal(str(settings.IVA)),
            impuestos=impuestos,
            total=total,
            pagos=pagos,
            total_pagado=pagado,
            propina_total=propina,
            saldo=saldo,
            pagada=pagada,
        )

    # ------------------------------------------------------------------ internos

    @staticmethod
    def _resolver_cuenta(orden: Orden, pedida: int | None) -> int:
        cuentas = orden.cuentas
        if pedida is None:
            if len(cuentas) > 1:
                disponibles = ", ".join(str(c) for c in cuentas)
                raise ReglaDeNegocio(
                    f"La mesa está dividida en {len(cuentas)} cuentas ({disponibles}); "
                    f"indica cuál estás cobrando"
                )
            return cuentas[0] if cuentas else 1
        if pedida not in cuentas:
            disponibles = ", ".join(str(c) for c in cuentas)
            raise ReglaDeNegocio(f"La orden no tiene la cuenta {pedida}. Existen: {disponibles}")
        return pedida

    @staticmethod
    def _calcular_propina(datos: PagoCrear, monto: Decimal) -> tuple[Decimal, Decimal | None]:
        """La propina se pide como importe o como porcentaje sobre lo que se paga."""
        if datos.propina_porcentaje is not None:
            porcentaje = redondear(datos.propina_porcentaje)
            return redondear(monto * porcentaje / Decimal("100")), porcentaje
        return redondear(datos.propina or CERO), None
