"""Servicio de consulta de cuentas y movimientos."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ApiError
from app.models.cuenta import Cuenta
from app.models.movimiento import Movimiento
from app.models.usuario import ROL_ADMIN, Usuario
from app.services.comun import obtener_o_404


def listar(db: Session, usuario: Usuario) -> list[Cuenta]:
    """Cuentas del usuario (admin ve todas)."""
    consulta = select(Cuenta).order_by(Cuenta.id)
    if usuario.rol != ROL_ADMIN:
        consulta = consulta.where(Cuenta.usuario_id == usuario.id)
    return list(db.scalars(consulta))


def obtener(db: Session, cuenta_id: int, usuario: Usuario) -> Cuenta:
    """Cuenta propia (403 ACCESO_DENEGADO si es de otro cliente)."""
    cuenta = obtener_o_404(db, Cuenta, cuenta_id, "La cuenta", "CUENTA_NO_ENCONTRADA")
    if usuario.rol != ROL_ADMIN and cuenta.usuario_id != usuario.id:
        raise ApiError(403, "ACCESO_DENEGADO", "La cuenta no le pertenece")
    return cuenta


def movimientos(
    db: Session, cuenta_id: int, usuario: Usuario, *, desde: date | None, hasta: date | None,
    tipo: str | None, offset: int, limit: int,
) -> tuple[list[Movimiento], int]:
    """Movimientos paginados de una cuenta propia, del más reciente al más antiguo."""
    cuenta = obtener(db, cuenta_id, usuario)
    if desde and hasta and desde > hasta:
        raise ApiError(400, "RANGO_FECHAS_INVALIDO", "La fecha 'desde' debe ser menor o igual a 'hasta'")
    consulta = select(Movimiento).where(Movimiento.cuenta_id == cuenta.id)
    if desde:
        consulta = consulta.where(Movimiento.fecha >= datetime.combine(desde, time.min))
    if hasta:
        consulta = consulta.where(Movimiento.fecha < datetime.combine(hasta + timedelta(days=1), time.min))
    if tipo:
        consulta = consulta.where(Movimiento.tipo == tipo)
    total = db.scalar(select(func.count()).select_from(consulta.subquery())) or 0
    filas = list(
        db.scalars(consulta.order_by(Movimiento.fecha.desc(), Movimiento.id.desc()).offset(offset).limit(limit))
    )
    return filas, total
