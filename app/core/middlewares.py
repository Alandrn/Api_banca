"""Middlewares propios: red permitida y cabeceras de seguridad/demostración."""

from __future__ import annotations

import ipaddress

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings
from app.core.exceptions import respuesta_error

# Limitador global: RATE_LIMIT_DEFAULT para todas las rutas, límites específicos por decorador.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.RATE_LIMIT_DEFAULT],
    enabled=settings.RATE_LIMIT_ENABLED,
    headers_enabled=False,
)


def ip_permitida(ip: str | None) -> bool:
    """Indica si una IP pertenece a alguna red de ALLOWED_NETWORKS (vacío = todas)."""
    redes = settings.redes_permitidas
    if not redes:
        return True
    if not ip:
        return False
    try:
        direccion = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(direccion in red for red in redes)


class RedPermitidaMiddleware(BaseHTTPMiddleware):
    """Rechaza con 403 RED_NO_PERMITIDA las peticiones fuera de las redes configuradas."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        ip = request.client.host if request.client else None
        if not ip_permitida(ip):
            return respuesta_error(
                403, "RED_NO_PERMITIDA", "La petición proviene de una red no autorizada"
            )
        return await call_next(request)


class CabecerasSeguridadMiddleware(BaseHTTPMiddleware):
    """Agrega cabeceras de seguridad básicas y la marca de entorno demostrativo."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        respuesta = await call_next(request)
        respuesta.headers.setdefault("X-Content-Type-Options", "nosniff")
        respuesta.headers.setdefault("X-Frame-Options", "DENY")
        respuesta.headers.setdefault("Referrer-Policy", "no-referrer")
        respuesta.headers["X-Demo"] = "true"
        return respuesta
