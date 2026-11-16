"""Servicio de administración: usuarios y estadísticas."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import ApiError
from app.models.cuenta import Cuenta
from app.models.solicitud import Solicitud
from app.models.usuario import ROLES, Usuario
from app.services.comun import obtener_o_404
from app.services.usuarios import crear_usuario
from app.utils.estados import (
    APROBADA,
    CONDICIONADA,
    ESTADOS,
    ESTADOS_FAVORABLES,
    FORMALIZADA,
    OFERTA_ACEPTADA,
    RECHAZADA,
)
from app.utils.finanzas import redondear


def listar_usuarios(
    db: Session, *, rol: str | None, activo: bool | None, busqueda: str | None, offset: int, limit: int
) -> tuple[list[Usuario], int]:
    """Lista paginada de usuarios con filtros."""
    consulta = select(Usuario)
    if rol:
        consulta = consulta.where(Usuario.rol == rol)
    if activo is not None:
        consulta = consulta.where(Usuario.activo == activo)
    if busqueda:
        patron = f"%{busqueda.lower()}%"
        consulta = consulta.where(
            or_(
                func.lower(Usuario.nombre).like(patron),
                func.lower(Usuario.apellidos).like(patron),
                func.lower(Usuario.email).like(patron),
                func.lower(Usuario.codigo).like(patron),
            )
        )
    total = db.scalar(select(func.count()).select_from(consulta.subquery())) or 0
    usuarios = list(db.scalars(consulta.order_by(Usuario.id).offset(offset).limit(limit)))
    return usuarios, total


def obtener_usuario(db: Session, usuario_id: int) -> Usuario:
    """Obtiene un usuario o 404 USUARIO_NO_ENCONTRADO."""
    return obtener_o_404(db, Usuario, usuario_id, "El usuario", "USUARIO_NO_ENCONTRADO")


def crear_personal(db: Session, datos: dict) -> Usuario:
    """Crea un usuario interno (valuador, analista o admin)."""
    usuario = crear_usuario(
        db,
        nombre=datos["nombre"],
        apellidos=datos["apellidos"],
        email=datos["email"],
        password=datos["password"],
        telefono=datos.get("telefono"),
        rol=datos["rol"],
    )
    db.commit()
    db.refresh(usuario)
    return usuario


def cambiar_estado_usuario(db: Session, admin: Usuario, usuario_id: int, activo: bool) -> Usuario:
    """Activa o desactiva un usuario. El admin no puede desactivarse a sí mismo."""
    usuario = obtener_usuario(db, usuario_id)
    if usuario.id == admin.id and not activo:
        raise ApiError(400, "OPERACION_NO_PERMITIDA", "No puede desactivar su propio usuario")
    usuario.activo = activo
    db.commit()
    db.refresh(usuario)
    return usuario


def estadisticas(db: Session) -> dict:
    """Indicadores: solicitudes por estado/tipo, monto aprobado y tasa de aprobación."""
    por_estado = {estado: 0 for estado in ESTADOS}
    for estado, cantidad in db.execute(select(Solicitud.estado, func.count()).group_by(Solicitud.estado)):
        por_estado[estado] = cantidad
    por_tipo = {"prestamo": 0, "hipoteca": 0}
    for tipo, cantidad in db.execute(select(Solicitud.tipo, func.count()).group_by(Solicitud.tipo)):
        por_tipo[tipo] = cantidad
    monto_aprobado = db.scalar(
        select(func.coalesce(func.sum(Solicitud.monto_aprobado), 0)).where(
            Solicitud.estado.in_([APROBADA, CONDICIONADA, OFERTA_ACEPTADA, FORMALIZADA])
        )
    )
    favorables = sum(por_estado[e] for e in ESTADOS_FAVORABLES)
    resueltas = favorables + por_estado[RECHAZADA]
    tasa = redondear(Decimal(favorables) / Decimal(resueltas) * 100) if resueltas else Decimal("0.00")
    por_rol = {rol: 0 for rol in ROLES}
    for rol, cantidad in db.execute(select(Usuario.rol, func.count()).group_by(Usuario.rol)):
        por_rol[rol] = cantidad
    return {
        "total_solicitudes": sum(por_estado.values()),
        "solicitudes_por_estado": por_estado,
        "solicitudes_por_tipo": por_tipo,
        "monto_total_aprobado": redondear(monto_aprobado or 0),
        "solicitudes_resueltas": resueltas,
        "solicitudes_favorables": favorables,
        "tasa_aprobacion_pct": tasa,
        "usuarios_por_rol": por_rol,
        "total_cuentas": db.scalar(select(func.count(Cuenta.id))) or 0,
    }
