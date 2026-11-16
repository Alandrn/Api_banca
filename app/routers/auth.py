"""Router de autenticación."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.middlewares import limiter
from app.core.responses import errores, ok
from app.dependencies.auth import get_usuario_actual
from app.models.usuario import Usuario
from app.schemas.auth import LoginIn, TokenOut
from app.schemas.common import Respuesta
from app.schemas.usuarios import UsuarioOut
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post(
    "/login",
    response_model=Respuesta[TokenOut],
    summary="Iniciar sesión",
    description=(
        "Valida correo y contraseña y devuelve un token JWT (vigencia 60 min) junto con los datos del "
        "usuario. Limitado a 5 intentos por minuto por IP. Usuarios inactivos reciben 403 USUARIO_INACTIVO."
    ),
    responses=errores(401, 403, 422, 429),
)
@limiter.limit(settings.RATE_LIMIT_LOGIN)
def login(request: Request, datos: LoginIn, db: Session = Depends(get_db)):
    """Inicio de sesión con correo y contraseña."""
    token, expira, usuario = auth_service.login(db, datos.email, datos.password)
    return ok(
        TokenOut(access_token=token, expires_in=expira, usuario=UsuarioOut.model_validate(usuario)),
        "Inicio de sesión exitoso",
    )


@router.get(
    "/me",
    response_model=Respuesta[UsuarioOut],
    summary="Usuario autenticado",
    description="Devuelve los datos del usuario dueño del token.",
    responses=errores(401, 403),
)
def me(usuario: Usuario = Depends(get_usuario_actual)):
    """Datos del usuario autenticado."""
    return ok(UsuarioOut.model_validate(usuario), "Usuario autenticado")
