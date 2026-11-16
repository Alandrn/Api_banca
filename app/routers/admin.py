"""Router de administración (solo admin)."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.responses import errores, ok, paginado
from app.dependencies.auth import Paginacion, paginacion, require_roles
from app.models.usuario import ROL_ADMIN, Usuario
from app.schemas.admin import EstadisticasOut
from app.schemas.common import Respuesta, RespuestaPaginada
from app.schemas.usuarios import AdminUsuarioIn, EstadoUsuarioIn, UsuarioOut
from app.services import admin as admin_service

router = APIRouter(prefix="/admin", tags=["Administración"])
solo_admin = require_roles(ROL_ADMIN)


@router.get(
    "/usuarios",
    response_model=RespuestaPaginada[UsuarioOut],
    summary="Listar usuarios",
    description="Lista paginada de usuarios con filtros por rol, activo y búsqueda (nombre, apellidos, email, código).",
    responses=errores(401, 403, 422),
)
def listar_usuarios(
    rol: Literal["cliente", "valuador", "analista", "admin"] | None = Query(None, description="Filtrar por rol"),
    activo: bool | None = Query(None, description="Filtrar por estado activo"),
    busqueda: str | None = Query(None, min_length=2, max_length=80, description="Texto a buscar"),
    pag: Paginacion = Depends(paginacion),
    _: Usuario = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    """Listado de usuarios."""
    usuarios, total = admin_service.listar_usuarios(
        db, rol=rol, activo=activo, busqueda=busqueda, offset=pag.offset, limit=pag.limit
    )
    return paginado([UsuarioOut.model_validate(u) for u in usuarios], pag.page, pag.limit, total, "Usuarios")


@router.get(
    "/usuarios/{usuario_id}",
    response_model=Respuesta[UsuarioOut],
    summary="Detalle de usuario",
    description="Datos de un usuario por id.",
    responses=errores(401, 403, 404),
)
def obtener_usuario(usuario_id: int, _: Usuario = Depends(solo_admin), db: Session = Depends(get_db)):
    """Detalle de un usuario."""
    return ok(UsuarioOut.model_validate(admin_service.obtener_usuario(db, usuario_id)), "Usuario")


@router.post(
    "/usuarios",
    status_code=201,
    response_model=Respuesta[UsuarioOut],
    summary="Crear personal interno",
    description="Crea un usuario con rol valuador, analista o admin.",
    responses=errores(401, 403, 409, 422),
)
def crear_usuario(datos: AdminUsuarioIn, _: Usuario = Depends(solo_admin), db: Session = Depends(get_db)):
    """Alta de personal interno."""
    usuario = admin_service.crear_personal(db, datos.model_dump())
    return ok(UsuarioOut.model_validate(usuario), "Usuario creado")


@router.patch(
    "/usuarios/{usuario_id}/estado",
    response_model=Respuesta[UsuarioOut],
    summary="Activar o desactivar usuario",
    description="Un usuario desactivado no puede iniciar sesión. El admin no puede desactivarse a sí mismo.",
    responses=errores(400, 401, 403, 404, 422),
)
def cambiar_estado(
    usuario_id: int, datos: EstadoUsuarioIn, admin: Usuario = Depends(solo_admin), db: Session = Depends(get_db)
):
    """Cambio de estado de un usuario."""
    usuario = admin_service.cambiar_estado_usuario(db, admin, usuario_id, datos.activo)
    return ok(UsuarioOut.model_validate(usuario), "Usuario activado" if usuario.activo else "Usuario desactivado")


@router.get(
    "/estadisticas",
    response_model=Respuesta[EstadisticasOut],
    summary="Estadísticas generales",
    description=(
        "Solicitudes por estado y tipo, monto total aprobado (aprobadas, condicionadas, aceptadas y "
        "formalizadas) y tasa de aprobación = favorables / resueltas × 100."
    ),
    responses=errores(401, 403),
)
def estadisticas(_: Usuario = Depends(solo_admin), db: Session = Depends(get_db)):
    """Indicadores del banco demo."""
    return ok(EstadisticasOut.model_validate(admin_service.estadisticas(db)), "Estadísticas")
