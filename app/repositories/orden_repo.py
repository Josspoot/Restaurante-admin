from datetime import datetime, timezone

from sqlalchemy import func, select

from app.models import EstadoOrden, Orden, Pago
from app.repositories.base import RepositorioBase


class OrdenRepo(RepositorioBase[Orden]):
    modelo = Orden

    def buscar(
        self,
        estado: EstadoOrden | None = None,
        cliente_id: int | None = None,
        mesa: int | None = None,
        pagada: bool | None = None,
        cerrada: bool | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Orden]:
        stmt = select(Orden)
        if estado is not None:
            stmt = stmt.where(Orden.estado == estado)
        if cliente_id is not None:
            stmt = stmt.where(Orden.cliente_id == cliente_id)
        if mesa is not None:
            stmt = stmt.where(Orden.mesa == mesa)
        if cerrada is not None:
            stmt = stmt.where(Orden.cerrada_en.is_not(None) if cerrada else Orden.cerrada_en.is_(None))
        if pagada is not None:
            # "Pagada" no es una columna: se compara el total contra lo cobrado.
            # Va en SQL y no en Python para que la paginacion siga siendo correcta.
            cobrado = (
                select(func.coalesce(func.sum(Pago.monto), 0))
                .where(Pago.orden_id == Orden.id)
                .scalar_subquery()
            )
            stmt = stmt.where(cobrado >= Orden.total if pagada else cobrado < Orden.total)
        stmt = stmt.order_by(Orden.creado_en.desc()).offset(skip).limit(limit)
        return list(self.db.scalars(stmt).unique())

    def activas(self) -> list[Orden]:
        """Ordenes con algo por preparar o entregar (lo que le importa a la cocina)."""
        stmt = (
            select(Orden)
            .where(
                Orden.estado.in_(
                    [EstadoOrden.PENDIENTE, EstadoOrden.EN_PREPARACION, EstadoOrden.LISTA]
                )
            )
            .order_by(Orden.creado_en)
        )
        return list(self.db.scalars(stmt).unique())

    def siguiente_numero(self) -> str:
        """Folio legible del dia: ORD-20260909-0007."""
        hoy = datetime.now(timezone.utc)
        prefijo = f"ORD-{hoy:%Y%m%d}"
        consecutivo = self.db.scalar(
            select(func.count(Orden.id)).where(Orden.numero.like(f"{prefijo}%"))
        )
        return f"{prefijo}-{(consecutivo or 0) + 1:04d}"
