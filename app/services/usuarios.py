"""Servicio de usuarios: registro, perfil y contraseña."""

from __future__ import annotations

import random
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ApiError
from app.core.security import hash_password, verificar_password
from app.models.cuenta import Cuenta
from app.models.movimiento import Movimiento
from app.models.usuario import ROL_CLIENTE, Usuario
from app.utils.fechas import ahora
from app.utils.finanzas import redondear
from app.utils.identificadores import codigo_usuario, numero_cuenta, referencia_movimiento

SALDO_INICIAL_MIN = 1000
SALDO_INICIAL_MAX = 50000


def email_existe(db: Session, email: str) -> bool:
    """Indica si ya hay un usuario con ese correo."""
    return db.scalar(select(Usuario.id).where(Usuario.email == email.lower())) is not None


def crear_usuario(
    db: Session, *, nombre: str, apellidos: str, email: str, password: str | None = None,
    telefono: str | None, rol: str, password_hash: str | None = None,
) -> Usuario:
    """Crea un usuario con su código USR-DEMO (sin commit). Lanza 409 si el correo existe."""
    if email_existe(db, email):
        raise ApiError(409, "EMAIL_REGISTRADO", "El correo electrónico ya está registrado")
    usuario = Usuario(
        nombre=nombre,
        apellidos=apellidos,
        email=email.lower(),
        password_hash=password_hash or hash_password(password or ""),
        telefono=telefono,
        rol=rol,
        activo=True,
        creado_en=ahora(),
    )
    db.add(usuario)
    db.flush()
    usuario.codigo = codigo_usuario(usuario.id)
    return usuario


def numero_cuenta_unico(db: Session, rng: random.Random | None = None) -> str:
    """Genera un número de cuenta DEMO que no exista en la BD."""
    while True:
        numero = numero_cuenta(rng)
        if db.scalar(select(Cuenta.id).where(Cuenta.numero == numero)) is None:
            return numero


def registrar_cliente(
    db: Session, *, nombre: str, apellidos: str, email: str, password: str, telefono: str | None
) -> tuple[Usuario, Cuenta]:
    """Registra un cliente y le abre una cuenta de débito demo con saldo inicial aleatorio."""
    usuario = crear_usuario(
        db, nombre=nombre, apellidos=apellidos, email=email, password=password, telefono=telefono,
        rol=ROL_CLIENTE,
    )
    saldo = redondear(Decimal(random.randint(SALDO_INICIAL_MIN * 100, SALDO_INICIAL_MAX * 100)) / 100)
    fecha = ahora()
    cuenta = Cuenta(
        usuario_id=usuario.id,
        numero=numero_cuenta_unico(db),
        tipo="debito",
        saldo=saldo,
        moneda="MXN",
        estado="activa",
        creada_en=fecha,
    )
    db.add(cuenta)
    db.flush()
    db.add(
        Movimiento(
            cuenta_id=cuenta.id,
            tipo="deposito",
            concepto="Depósito inicial de apertura (demo)",
            monto=saldo,
            saldo_resultante=saldo,
            referencia=referencia_movimiento(fecha),
            fecha=fecha,
        )
    )
    db.commit()
    db.refresh(usuario)
    return usuario, cuenta


def actualizar_perfil(db: Session, usuario: Usuario, cambios: dict) -> Usuario:
    """Actualiza nombre, apellidos y/o teléfono."""
    permitidos = {"nombre", "apellidos", "telefono"}
    datos = {k: v for k, v in cambios.items() if k in permitidos}
    if not datos:
        raise ApiError(400, "SIN_CAMBIOS", "No se indicó ningún campo para actualizar")
    for campo, valor in datos.items():
        if campo in ("nombre", "apellidos") and valor is None:
            raise ApiError(400, "CAMPO_OBLIGATORIO", f"El campo '{campo}' no puede quedar vacío")
        setattr(usuario, campo, valor)
    db.commit()
    db.refresh(usuario)
    return usuario


def cambiar_password(db: Session, usuario: Usuario, actual: str, nueva: str) -> None:
    """Cambia la contraseña validando la actual."""
    if not verificar_password(actual, usuario.password_hash):
        raise ApiError(400, "PASSWORD_INCORRECTA", "La contraseña actual no es correcta")
    if actual == nueva:
        raise ApiError(400, "PASSWORD_REPETIDA", "La nueva contraseña debe ser distinta de la actual")
    usuario.password_hash = hash_password(nueva)
    db.commit()
