from fastapi import APIRouter, Query, status

from app.api.deps import DB, SoloAdmin, SoloPersonal, UsuarioActual
from app.models import EstadoOrden
from app.schemas.orden import (
    ComandaCocina, CuentaResumen, ItemAsignarCuenta, OrdenCambiarEstado, OrdenCrear,
    OrdenItemCrear, OrdenRespuesta, TandaCambiarEstado, TandaResumen,
)
from app.schemas.pago import Factura, PagoCrear
from app.services import OrdenService, PagoService

router = APIRouter(prefix="/ordenes", tags=["Órdenes"])


@router.get("", response_model=list[OrdenRespuesta])
def listar(
    db: DB,
    usuario: UsuarioActual,
    estado: EstadoOrden | None = None,
    mesa: int | None = None,
    pagada: bool | None = Query(default=None, description="true = saldadas, false = por cobrar"),
    cerrada: bool | None = Query(default=None, description="true = mesas ya terminadas"),
    skip: int = 0,
    limit: int = Query(default=50, le=200),
):
    """El personal ve todas las órdenes; un cliente solo ve las suyas.

    `pagada` y `cerrada` son independientes: una orden puede estar entregada y
    seguir sin cobrarse, y solo se cierra cuando ya no le falta nada.
    """
    return OrdenService(db).listar(
        usuario, estado=estado, mesa=mesa, pagada=pagada, cerrada=cerrada, skip=skip, limit=limit
    )


@router.get("/cocina", response_model=list[ComandaCocina], tags=["Cocina"])
def cocina(db: DB, usuario: SoloPersonal):
    """Tandas pendientes de sacar, más viejas primero.

    Una mesa que pidió postre más tarde aparece como comanda aparte aunque su
    primera tanda ya se haya entregado.
    """
    return OrdenService(db).cocina()


@router.get("/avisos", response_model=list[ComandaCocina], tags=["Cocina"])
def avisos(db: DB, usuario: SoloPersonal):
    """Tandas listas que siguen sin llevarse a la mesa.

    Es lo que alimenta las notificaciones del mesero: solo ve las de sus propias
    órdenes; un administrador las ve todas.
    """
    return OrdenService(db).listas_para_entregar(usuario)


@router.get("/{orden_id}", response_model=OrdenRespuesta)
def obtener(orden_id: int, db: DB, usuario: UsuarioActual):
    return OrdenService(db).obtener_para(orden_id, usuario)


@router.post("", response_model=OrdenRespuesta, status_code=status.HTTP_201_CREATED)
def crear(datos: OrdenCrear, db: DB, usuario: UsuarioActual):
    """Crea la comanda y calcula subtotal, IVA y total a partir del menú vigente."""
    return OrdenService(db).crear(datos, usuario)


@router.post("/{orden_id}/items", response_model=OrdenRespuesta)
def agregar_item(orden_id: int, linea: OrdenItemCrear, db: DB, usuario: UsuarioActual):
    """Agrega un platillo a una orden ya abierta.

    En consumo local se puede pedir más en cualquier momento: si la comanda ya
    salió a cocina, el platillo entra en una tanda nueva y todo se sigue cobrando
    junto en la misma mesa.
    """
    return OrdenService(db).agregar_item(orden_id, linea, usuario)


@router.delete("/{orden_id}/items/{item_id}", response_model=OrdenRespuesta)
def quitar_item(orden_id: int, item_id: int, db: DB, usuario: UsuarioActual):
    """Solo se puede quitar lo que todavía no entra a cocina."""
    return OrdenService(db).quitar_item(orden_id, item_id, usuario)


@router.patch("/{orden_id}/items/{item_id}/cuenta", response_model=OrdenRespuesta)
def asignar_cuenta(
    orden_id: int, item_id: int, datos: ItemAsignarCuenta, db: DB, usuario: SoloPersonal
):
    """Mueve un platillo a otra cuenta al dividir la mesa."""
    return OrdenService(db).asignar_cuenta(orden_id, item_id, datos.cuenta, usuario)


@router.get("/{orden_id}/cuentas", response_model=list[CuentaResumen])
def cuentas(orden_id: int, db: DB, usuario: UsuarioActual):
    """Cuánto debe y cuánto lleva pagado cada cuenta de la mesa."""
    servicio = OrdenService(db)
    return servicio.desglose(servicio.obtener_para(orden_id, usuario))


@router.get("/{orden_id}/tandas", response_model=list[TandaResumen])
def tandas(orden_id: int, db: DB, usuario: UsuarioActual):
    """Las rondas en que se pidió la orden, cada una con su propio avance."""
    servicio = OrdenService(db)
    return servicio.tandas(servicio.obtener_para(orden_id, usuario))


@router.patch("/{orden_id}/estado", response_model=OrdenRespuesta)
def cambiar_estado(orden_id: int, datos: OrdenCambiarEstado, db: DB, usuario: SoloPersonal):
    """Avanza la orden completa, arrastrando los platillos que van atrás."""
    return OrdenService(db).cambiar_estado(orden_id, datos.estado, usuario)


@router.patch("/{orden_id}/tandas/{tanda}/estado", response_model=OrdenRespuesta, tags=["Cocina"])
def cambiar_estado_tanda(
    orden_id: int, tanda: int, datos: TandaCambiarEstado, db: DB, usuario: SoloPersonal
):
    """Avanza una sola tanda. Es lo que usa el tablero de cocina."""
    return OrdenService(db).cambiar_estado_tanda(orden_id, tanda, datos.estado, usuario)


@router.post("/{orden_id}/cancelar", response_model=OrdenRespuesta)
def cancelar(orden_id: int, db: DB, usuario: UsuarioActual):
    return OrdenService(db).cancelar(orden_id, usuario)


@router.post("/{orden_id}/cerrar", response_model=OrdenRespuesta)
def cerrar(orden_id: int, db: DB, usuario: SoloPersonal):
    """Cierra la mesa. Exige que todo esté entregado y cobrado.

    A partir de aquí la orden no admite platillos, cobros ni cambios de estado.
    """
    return OrdenService(db).cerrar(orden_id, usuario)


@router.post("/{orden_id}/reabrir", response_model=OrdenRespuesta)
def reabrir(orden_id: int, db: DB, usuario: SoloAdmin):
    """Deshace un cierre hecho por error. Solo ADMIN."""
    return OrdenService(db).reabrir(orden_id, usuario)


@router.post("/{orden_id}/pagos", response_model=OrdenRespuesta, status_code=status.HTTP_201_CREATED)
def registrar_pago(orden_id: int, datos: PagoCrear, db: DB, usuario: SoloPersonal):
    """Registra un cobro contra una cuenta.

    Si se omite `monto` se cobra el saldo completo de esa cuenta. La propina se
    puede mandar como importe (`propina`) o como porcentaje (`propina_porcentaje`),
    que se calcula sobre lo que se está pagando.
    """
    return PagoService(db).registrar(orden_id, datos, usuario)


@router.get("/{orden_id}/factura", response_model=Factura)
def factura(
    orden_id: int,
    db: DB,
    usuario: UsuarioActual,
    cuenta: int | None = Query(default=None, description="Ticket de una sola cuenta"),
):
    """Ticket desglosado de toda la mesa, o de una cuenta si se indica cuál."""
    return PagoService(db).factura(orden_id, usuario, cuenta)
