"""Enumeraciones del dominio."""
from enum import Enum


class RolUsuario(str, Enum):
    ADMIN = "ADMIN"
    MESERO = "MESERO"
    CLIENTE = "CLIENTE"


class TipoOrden(str, Enum):
    LOCAL = "LOCAL"
    PARA_LLEVAR = "PARA_LLEVAR"
    DOMICILIO = "DOMICILIO"


class EstadoItem(str, Enum):
    """Avance de un platillo concreto dentro de la orden.

    Existe porque en una mesa se pide por tandas: la cocina puede tener la
    entrada ya servida y el postre todavia sin empezar, en la misma orden.
    """

    PENDIENTE = "PENDIENTE"
    EN_PREPARACION = "EN_PREPARACION"
    LISTA = "LISTA"
    ENTREGADA = "ENTREGADA"


# Cuanto ha avanzado cada estado. El estado de la orden es el minimo de sus items.
AVANCE: dict[str, int] = {
    EstadoItem.PENDIENTE: 0,
    EstadoItem.EN_PREPARACION: 1,
    EstadoItem.LISTA: 2,
    EstadoItem.ENTREGADA: 3,
}


class EstadoOrden(str, Enum):
    PENDIENTE = "PENDIENTE"
    EN_PREPARACION = "EN_PREPARACION"
    LISTA = "LISTA"
    ENTREGADA = "ENTREGADA"
    CANCELADA = "CANCELADA"


class MetodoPago(str, Enum):
    EFECTIVO = "EFECTIVO"
    TARJETA = "TARJETA"
    TRANSFERENCIA = "TRANSFERENCIA"
