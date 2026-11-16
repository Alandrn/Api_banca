"""Dependencias de autenticación y autorización por rol."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import ApiError
from app.core.security import decodificar_token
from app.models.usuario import ROL_ADMIN, Usuario

_bearer = HTTPBearer(auto_error=False, description="Token JWT obtenido en /auth/login")


def get_usuario_actual(
    credenciales: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Usuario:
    """Obtiene el usuario autenticado a partir del header ``Authorization: Bearer``."""
    if credenciales is None or not credenciales.credentials:
        raise ApiError(401, "NO_AUTENTICADO", "Se requiere autenticación (Authorization: Bearer <token>)")
    payload = decodificar_token(credenciales.credentials)
    try:
        usuario_id = int(payload["sub"])
    except (TypeError, ValueError) as exc:
        raise ApiError(401, "TOKEN_INVALIDO", "El token no es válido") from exc
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise ApiError(401, "TOKEN_INVALIDO", "El usuario del token no existe")
    if not usuario.activo:
        raise ApiError(403, "USUARIO_INACTIVO", "El usuario está desactivado")
    return usuario


def require_roles(*roles: str) -> Callable[..., Usuario]:
    """Crea una dependencia que exige alguno de los roles indicados (admin siempre pasa)."""

    def _dependencia(usuario: Usuario = Depends(get_usuario_actual)) -> Usuario:
        if usuario.rol == ROL_ADMIN or usuario.rol in roles:
            return usuario
        raise ApiError(
            403,
            "PERMISO_INSUFICIENTE",
            "Su rol no tiene permiso para esta operación",
            [{"rolActual": usuario.rol, "rolesPermitidos": sorted(set(roles) | {ROL_ADMIN})}],
        )

    return _dependencia


@dataclass
class Paginacion:
    """Parámetros de paginación ya validados."""

    page: int
    limit: int

    @property
    def offset(self) -> int:
        """Desplazamiento para la consulta."""
        return (self.page - 1) * self.limit


def paginacion(
    page: int = Query(1, ge=1, description="Número de página (desde 1)"),
    limit: int = Query(10, ge=1, le=100, description="Elementos por página (máximo 100)"),
) -> Paginacion:
    """Dependencia de paginación ``?page=1&limit=10``."""
    return Paginacion(page=page, limit=limit)
