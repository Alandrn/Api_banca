"""Utilidades de seguridad: hash de contraseñas y tokens JWT."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.exceptions import ApiError

_pwd_context = CryptContext(
    schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=settings.BCRYPT_ROUNDS
)


def hash_password(password: str) -> str:
    """Genera el hash bcrypt de una contraseña."""
    return _pwd_context.hash(password)


def verificar_password(password: str, password_hash: str) -> bool:
    """Compara una contraseña en claro contra su hash."""
    try:
        return _pwd_context.verify(password, password_hash)
    except (ValueError, TypeError):
        return False


def crear_token(usuario_id: int, rol: str) -> tuple[str, int]:
    """Crea un JWT con ``sub`` (id) y ``rol``. Devuelve (token, segundos de vigencia)."""
    ahora = datetime.now(timezone.utc)
    expira = ahora + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload: dict[str, Any] = {
        "sub": str(usuario_id),
        "rol": rol,
        "iat": int(ahora.timestamp()),
        "exp": int(expira.timestamp()),
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return token, settings.JWT_EXPIRE_MINUTES * 60


def decodificar_token(token: str) -> dict[str, Any]:
    """Valida y decodifica un JWT. Lanza ApiError 401 si es inválido o expiró."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except ExpiredSignatureError as exc:
        raise ApiError(401, "TOKEN_EXPIRADO", "El token ha expirado, inicie sesión de nuevo") from exc
    except JWTError as exc:
        raise ApiError(401, "TOKEN_INVALIDO", "El token no es válido") from exc
    if "sub" not in payload or "rol" not in payload:
        raise ApiError(401, "TOKEN_INVALIDO", "El token no contiene la información requerida")
    return payload
