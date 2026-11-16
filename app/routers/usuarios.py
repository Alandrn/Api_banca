"""Router de usuarios: registro y perfil."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.responses import errores, ok
from app.dependencies.auth import get_usuario_actual
from app.models.usuario import Usuario
from app.schemas.common import MensajeSimple, Respuesta
from app.schemas.cuentas import CuentaOut
from app.schemas.usuarios import PasswordUpdateIn, PerfilUpdateIn, RegistroIn, RegistroOut, UsuarioOut
from app.services import usuarios as usuarios_service

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


@router.post(
    "/registro",
    status_code=201,
    response_model=Respuesta[RegistroOut],
    summary="Registro de cliente",
    description=(
        "Crea un usuario con rol cliente y le abre una cuenta de débito DEMO con saldo inicial aleatorio. "
        "La contraseña requiere mínimo 8 caracteres, una mayúscula y un número. 409 EMAIL_REGISTRADO si el "
        "correo ya existe."
    ),
    responses=errores(409, 422),
)
def registro(datos: RegistroIn, db: Session = Depends(get_db)):
    """Registro público de clientes."""
    usuario, cuenta = usuarios_service.registrar_cliente(db, **datos.model_dump())
    return ok(
        RegistroOut(usuario=UsuarioOut.model_validate(usuario), cuenta=CuentaOut.model_validate(cuenta)),
        "Registro exitoso. Se creó una cuenta de débito demo.",
    )


@router.get(
    "/perfil",
    response_model=Respuesta[UsuarioOut],
    summary="Consultar perfil",
    description="Datos del perfil del usuario autenticado.",
    responses=errores(401),
)
def perfil(usuario: Usuario = Depends(get_usuario_actual)):
    """Perfil propio."""
    return ok(UsuarioOut.model_validate(usuario), "Perfil del usuario")


@router.patch(
    "/perfil",
    response_model=Respuesta[UsuarioOut],
    summary="Actualizar perfil",
    description="Actualiza nombre, apellidos y/o teléfono. Solo se modifican los campos enviados.",
    responses=errores(400, 401, 422),
)
def actualizar_perfil(
    datos: PerfilUpdateIn, usuario: Usuario = Depends(get_usuario_actual), db: Session = Depends(get_db)
):
    """Actualización parcial del perfil."""
    actualizado = usuarios_service.actualizar_perfil(db, usuario, datos.model_dump(exclude_unset=True))
    return ok(UsuarioOut.model_validate(actualizado), "Perfil actualizado")


@router.patch(
    "/perfil/password",
    response_model=Respuesta[MensajeSimple],
    summary="Cambiar contraseña",
    description="Requiere la contraseña actual. La nueva debe tener mínimo 8 caracteres, una mayúscula y un número.",
    responses=errores(400, 401, 422),
)
def cambiar_password(
    datos: PasswordUpdateIn, usuario: Usuario = Depends(get_usuario_actual), db: Session = Depends(get_db)
):
    """Cambio de contraseña."""
    usuarios_service.cambiar_password(db, usuario, datos.password_actual, datos.password_nueva)
    return ok(MensajeSimple(id=usuario.id), "Contraseña actualizada correctamente")
