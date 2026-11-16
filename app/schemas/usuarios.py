"""Esquemas de usuarios, perfil y administración de usuarios."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator

from app.schemas.common import Correo, SchemaBase
from app.schemas.cuentas import CuentaOut

PATRON_TELEFONO = r"^\+?[0-9]{10,15}$"
PATRON_NOMBRE = r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ' .-]+$"


def validar_password_segura(valor: str) -> str:
    """Mínimo 8 caracteres, al menos una mayúscula y un número."""
    if len(valor) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres")
    if not re.search(r"[A-Z]", valor):
        raise ValueError("La contraseña debe contener al menos una letra mayúscula")
    if not re.search(r"[0-9]", valor):
        raise ValueError("La contraseña debe contener al menos un número")
    return valor


class UsuarioOut(SchemaBase):
    """Datos públicos de un usuario (nunca incluye password_hash)."""

    id: int
    codigo: str | None
    nombre: str
    apellidos: str
    email: str
    telefono: str | None
    rol: str
    activo: bool
    creado_en: datetime

    model_config = SchemaBase.model_config | {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 6,
                    "codigo": "USR-DEMO-000006",
                    "nombre": "Ana",
                    "apellidos": "López Pérez",
                    "email": "cliente1@demo-banco.test",
                    "telefono": "5512345678",
                    "rol": "cliente",
                    "activo": True,
                    "creadoEn": "2026-01-10T12:00:00",
                }
            ]
        }
    }


class RegistroIn(SchemaBase):
    """Alta pública de un cliente."""

    nombre: str = Field(min_length=2, max_length=80, pattern=PATRON_NOMBRE)
    apellidos: str = Field(min_length=2, max_length=120, pattern=PATRON_NOMBRE)
    email: Correo
    password: str = Field(max_length=72)
    telefono: str | None = Field(default=None, pattern=PATRON_TELEFONO)

    _valida_password = field_validator("password")(validar_password_segura)

    model_config = SchemaBase.model_config | {
        "json_schema_extra": {
            "examples": [
                {
                    "nombre": "Laura",
                    "apellidos": "Martínez Ruiz",
                    "email": "laura.martinez@demo-banco.test",
                    "password": "Segura2026",
                    "telefono": "5511223344",
                }
            ]
        }
    }


class RegistroOut(SchemaBase):
    """Resultado del registro: usuario y cuenta demo creada."""

    usuario: UsuarioOut
    cuenta: CuentaOut


class PerfilUpdateIn(SchemaBase):
    """Campos editables del perfil."""

    nombre: str | None = Field(default=None, min_length=2, max_length=80, pattern=PATRON_NOMBRE)
    apellidos: str | None = Field(default=None, min_length=2, max_length=120, pattern=PATRON_NOMBRE)
    telefono: str | None = Field(default=None, pattern=PATRON_TELEFONO)

    model_config = SchemaBase.model_config | {
        "json_schema_extra": {"examples": [{"telefono": "5599887766", "nombre": "Ana María"}]}
    }


class PasswordUpdateIn(SchemaBase):
    """Cambio de contraseña."""

    password_actual: str = Field(min_length=1, max_length=72)
    password_nueva: str = Field(max_length=72)

    _valida_password = field_validator("password_nueva")(validar_password_segura)

    model_config = SchemaBase.model_config | {
        "json_schema_extra": {"examples": [{"passwordActual": "Demo1234!", "passwordNueva": "NuevaClave2026"}]}
    }


class AdminUsuarioIn(SchemaBase):
    """Alta de personal interno por el admin."""

    nombre: str = Field(min_length=2, max_length=80, pattern=PATRON_NOMBRE)
    apellidos: str = Field(min_length=2, max_length=120, pattern=PATRON_NOMBRE)
    email: Correo
    password: str = Field(max_length=72)
    telefono: str | None = Field(default=None, pattern=PATRON_TELEFONO)
    rol: Literal["valuador", "analista", "admin"]

    _valida_password = field_validator("password")(validar_password_segura)

    model_config = SchemaBase.model_config | {
        "json_schema_extra": {
            "examples": [
                {
                    "nombre": "Jorge",
                    "apellidos": "Valdez Soto",
                    "email": "valuador3@demo-banco.test",
                    "password": "Valuador2026",
                    "telefono": "5544332211",
                    "rol": "valuador",
                }
            ]
        }
    }


class EstadoUsuarioIn(SchemaBase):
    """Activar o desactivar un usuario."""

    activo: bool

    model_config = SchemaBase.model_config | {"json_schema_extra": {"examples": [{"activo": False}]}}

