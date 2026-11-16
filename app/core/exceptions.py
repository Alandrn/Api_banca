"""Excepción de negocio y manejadores centrales de errores.

Todos los errores de la API salen con el formato::

    { "ok": false, "error": { "code": "...", "message": "...", "details": [] }, "demo": true }
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("banco_demo")


class ApiError(Exception):
    """Error de negocio que los servicios lanzan sin conocer HTTP.

    Args:
        status_code: código HTTP sugerido (400, 401, 403, 404, 409...).
        code: código de error en MAYUSCULAS_CON_GUION_BAJO.
        message: mensaje legible en español.
        details: lista opcional con información adicional.
    """

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: list[Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or []


def respuesta_error(
    status_code: int, code: str, message: str, details: list[Any] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Construye una respuesta JSON de error con el formato estándar."""
    return JSONResponse(
        status_code=status_code,
        content={
            "ok": False,
            "error": {"code": code, "message": message, "details": details or []},
            "demo": True,
        },
        headers=headers,
    )


# ---------------------------------------------------------------------------
# Traducción de errores de validación de Pydantic al español
# ---------------------------------------------------------------------------

_MENSAJES_VALIDACION: dict[str, str] = {
    "missing": "Campo obligatorio",
    "string_too_short": "Debe tener al menos {min_length} caracteres",
    "string_too_long": "Debe tener como máximo {max_length} caracteres",
    "string_type": "Debe ser un texto",
    "string_pattern_mismatch": "El formato no es válido",
    "int_type": "Debe ser un número entero",
    "int_parsing": "Debe ser un número entero",
    "int_from_float": "Debe ser un número entero",
    "float_type": "Debe ser un número",
    "float_parsing": "Debe ser un número",
    "decimal_type": "Debe ser un número decimal",
    "decimal_parsing": "Debe ser un número decimal",
    "decimal_max_digits": "Debe tener como máximo {max_digits} dígitos",
    "decimal_max_places": "Debe tener como máximo {decimal_places} decimales",
    "decimal_whole_digits": "Tiene demasiados dígitos enteros",
    "bool_type": "Debe ser verdadero o falso",
    "bool_parsing": "Debe ser verdadero o falso",
    "greater_than": "Debe ser mayor que {gt}",
    "greater_than_equal": "Debe ser mayor o igual que {ge}",
    "less_than": "Debe ser menor que {lt}",
    "less_than_equal": "Debe ser menor o igual que {le}",
    "multiple_of": "Debe ser múltiplo de {multiple_of}",
    "literal_error": "Valor no permitido. Opciones: {expected}",
    "enum": "Valor no permitido. Opciones: {expected}",
    "date_type": "Debe ser una fecha (AAAA-MM-DD)",
    "date_parsing": "Debe ser una fecha válida (AAAA-MM-DD)",
    "date_from_datetime_parsing": "Debe ser una fecha válida (AAAA-MM-DD)",
    "datetime_type": "Debe ser una fecha y hora ISO 8601",
    "datetime_parsing": "Debe ser una fecha y hora ISO 8601",
    "datetime_from_date_parsing": "Debe ser una fecha y hora ISO 8601",
    "list_type": "Debe ser una lista",
    "too_short": "Debe contener al menos {min_length} elementos",
    "too_long": "Debe contener como máximo {max_length} elementos",
    "dict_type": "Debe ser un objeto",
    "model_type": "Debe ser un objeto",
    "model_attributes_type": "Debe ser un objeto",
    "json_invalid": "El cuerpo no es un JSON válido",
    "json_type": "El cuerpo debe ser JSON",
    "extra_forbidden": "Campo no permitido",
    "value_error": "{error}",
    "assertion_error": "{error}",
    "union_tag_invalid": "Valor no permitido",
    "missing_argument": "Campo obligatorio",
}

_UBICACIONES = {"body": "body", "query": "query", "path": "path", "header": "header", "cookie": "cookie"}


def traducir_errores_validacion(errores: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Convierte los errores de Pydantic en una lista ``{campo, mensaje}`` en español."""
    resultado: list[dict[str, str]] = []
    for err in errores:
        loc = list(err.get("loc", ()))
        if loc and loc[0] in _UBICACIONES:
            loc = loc[1:]
        campo = ".".join(str(p) for p in loc) or "body"
        tipo = err.get("type", "")
        ctx = dict(err.get("ctx") or {})
        plantilla = _MENSAJES_VALIDACION.get(tipo)
        if tipo in ("value_error", "assertion_error"):
            mensaje = str(ctx.get("error", err.get("msg", "Valor inválido")))
            mensaje = mensaje.removeprefix("Value error, ").removeprefix("Assertion failed, ")
        elif plantilla:
            try:
                mensaje = plantilla.format(**{k: str(v) for k, v in ctx.items()})
            except (KeyError, IndexError):
                mensaje = plantilla
        else:
            mensaje = f"Valor inválido ({err.get('msg', tipo)})"
        resultado.append({"campo": campo, "mensaje": mensaje})
    return resultado


# ---------------------------------------------------------------------------
# Manejadores
# ---------------------------------------------------------------------------

_CODIGOS_HTTP = {
    400: ("SOLICITUD_INCORRECTA", "La petición no es válida"),
    401: ("NO_AUTENTICADO", "Se requiere autenticación"),
    403: ("ACCESO_DENEGADO", "No tiene permiso para realizar esta acción"),
    404: ("RUTA_NO_ENCONTRADA", "La ruta solicitada no existe"),
    405: ("METODO_NO_PERMITIDO", "Método HTTP no permitido para esta ruta"),
    409: ("CONFLICTO", "Conflicto con el estado actual del recurso"),
    415: ("TIPO_CONTENIDO_NO_SOPORTADO", "Tipo de contenido no soportado"),
}


async def _manejar_api_error(_: Request, exc: ApiError) -> JSONResponse:
    return respuesta_error(exc.status_code, exc.code, exc.message, exc.details)


async def _manejar_validacion(_: Request, exc: RequestValidationError) -> JSONResponse:
    detalles = traducir_errores_validacion(list(exc.errors()))
    return respuesta_error(422, "ERROR_VALIDACION", "Los datos enviados no son válidos", detalles)


async def _manejar_http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    code, mensaje = _CODIGOS_HTTP.get(exc.status_code, ("ERROR_HTTP", "Error en la petición"))
    return respuesta_error(exc.status_code, code, mensaje, headers=getattr(exc, "headers", None))


def manejar_rate_limit(_: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Manejador síncrono (compatible con SlowAPIMiddleware) para el error 429."""
    return respuesta_error(
        429,
        "LIMITE_PETICIONES_EXCEDIDO",
        "Demasiadas peticiones. Intente de nuevo en un momento.",
        [{"limite": str(exc.detail)}],
        headers={"Retry-After": "60"},
    )


async def _manejar_error_interno(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Error no controlado: %s", exc)
    return respuesta_error(500, "ERROR_INTERNO", "Ocurrió un error interno en el servidor")


def registrar_manejadores(app: FastAPI) -> None:
    """Registra todos los manejadores de excepción en la aplicación."""
    app.add_exception_handler(ApiError, _manejar_api_error)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, _manejar_validacion)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, _manejar_http)  # type: ignore[arg-type]
    app.add_exception_handler(RateLimitExceeded, manejar_rate_limit)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _manejar_error_interno)
