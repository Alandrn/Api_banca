"""Esquemas de autenticación."""

from __future__ import annotations

from pydantic import Field

from app.schemas.common import Correo, SchemaBase
from app.schemas.usuarios import UsuarioOut


class LoginIn(SchemaBase):
    """Credenciales de acceso."""

    email: Correo
    password: str = Field(min_length=1, max_length=72)

    model_config = SchemaBase.model_config | {
        "json_schema_extra": {"examples": [{"email": "cliente1@demo-banco.test", "password": "Demo1234!"}]}
    }


class TokenOut(SchemaBase):
    """Token JWT y datos del usuario autenticado."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    usuario: UsuarioOut
