"""Funciones compartidas por los servicios: búsqueda, acceso y transiciones."""

from __future__ import annotations

from typing import TypeVar

from sqlalchemy.orm import Session

from app.core.exceptions import ApiError
from app.models.avaluo import Avaluo
from app.models.historial import HistorialEstado
from app.models.inmueble import Inmueble
from app.models.solicitud import Solicitud
from app.models.usuario import ROL_ADMIN, ROL_ANALISTA, ROL_CLIENTE, ROL_VALUADOR, Usuario
from app.utils.estados import ESTADOS_EDITABLES, validar_transicion
from app.utils.fechas import ahora

M = TypeVar("M")


def obtener_o_404(db: Session, modelo: type[M], id_: int, nombre: str, code: str) -> M:
    """Obtiene un registro por id o lanza 404 con el código indicado."""
    objeto = db.get(modelo, id_)
    if objeto is None:
        raise ApiError(404, code, f"{nombre} con id {id_} no existe")
    return objeto


def es_personal(usuario: Usuario) -> bool:
    """Analista o admin: pueden ver todas las solicitudes."""
    return usuario.rol in (ROL_ANALISTA, ROL_ADMIN)


def obtener_solicitud(db: Session, solicitud_id: int) -> Solicitud:
    """Obtiene una solicitud o lanza 404 SOLICITUD_NO_ENCONTRADA."""
    return obtener_o_404(db, Solicitud, solicitud_id, "La solicitud", "SOLICITUD_NO_ENCONTRADA")


def _valuador_asignado(solicitud: Solicitud, usuario: Usuario) -> bool:
    inmueble: Inmueble | None = solicitud.inmueble
    avaluo: Avaluo | None = inmueble.avaluo if inmueble else None
    return avaluo is not None and avaluo.valuador_id == usuario.id


def solicitud_con_acceso(db: Session, solicitud_id: int, usuario: Usuario) -> Solicitud:
    """Solicitud visible para el usuario.

    - analista/admin: cualquiera.
    - cliente: solo las propias.
    - valuador: solo si tiene asignado el avalúo de la solicitud.
    """
    solicitud = obtener_solicitud(db, solicitud_id)
    if es_personal(usuario):
        return solicitud
    if usuario.rol == ROL_CLIENTE and solicitud.usuario_id == usuario.id:
        return solicitud
    if usuario.rol == ROL_VALUADOR and _valuador_asignado(solicitud, usuario):
        return solicitud
    raise ApiError(403, "ACCESO_DENEGADO", "No tiene permiso para acceder a esta solicitud")


def solicitud_propia(db: Session, solicitud_id: int, usuario: Usuario) -> Solicitud:
    """Solicitud que pertenece al usuario (admin puede operar cualquiera)."""
    solicitud = obtener_solicitud(db, solicitud_id)
    if usuario.rol == ROL_ADMIN or solicitud.usuario_id == usuario.id:
        return solicitud
    raise ApiError(403, "ACCESO_DENEGADO", "La solicitud no le pertenece")


def solicitud_propia_o_personal(db: Session, solicitud_id: int, usuario: Usuario) -> Solicitud:
    """Solicitud propia (cliente) o cualquiera si es analista/admin."""
    solicitud = obtener_solicitud(db, solicitud_id)
    if es_personal(usuario) or solicitud.usuario_id == usuario.id:
        return solicitud
    raise ApiError(403, "ACCESO_DENEGADO", "La solicitud no le pertenece")


def validar_editable(solicitud: Solicitud) -> None:
    """Solo se editan datos/documentos/inmueble en borrador o datos_completos."""
    if solicitud.estado not in ESTADOS_EDITABLES:
        raise ApiError(
            400,
            "SOLICITUD_NO_EDITABLE",
            f"La solicitud está en estado '{solicitud.estado}' y ya no puede modificarse",
        )


def cambiar_estado(
    db: Session, solicitud: Solicitud, nuevo: str, usuario_id: int | None, nota: str | None = None,
    validar: bool = True,
) -> HistorialEstado:
    """Valida la transición, cambia el estado y registra el historial (sin commit)."""
    if validar:
        validar_transicion(solicitud.estado, nuevo, solicitud.tipo)
    registro = HistorialEstado(
        solicitud_id=solicitud.id,
        estado_anterior=solicitud.estado,
        estado_nuevo=nuevo,
        usuario_id=usuario_id,
        nota=nota,
        fecha=ahora(),
    )
    solicitud.estado = nuevo
    solicitud.actualizada_en = ahora()
    db.add(registro)
    solicitud.historial.append(registro)
    return registro
