"""Servicio de autenticación."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ApiError
from app.core.security import crear_token, verificar_password
from app.models.usuario import Usuario


def login(db: Session, email: str, password: str) -> tuple[str, int, Usuario]:
    """Valida credenciales y devuelve (token, expira_en_segundos, usuario)."""
    usuario = db.scalar(select(Usuario).where(Usuario.email == email.lower()))
    if usuario is None or not verificar_password(password, usuario.password_hash):
        raise ApiError(401, "CREDENCIALES_INVALIDAS", "Correo o contraseña incorrectos")
    if not usuario.activo:
        raise ApiError(403, "USUARIO_INACTIVO", "El usuario está desactivado; contacte al administrador")
    token, expira = crear_token(usuario.id, usuario.rol)
    return token, expira, usuario
