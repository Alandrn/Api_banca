"""Constructores del sobre de respuesta estándar y documentación de errores.

Éxito::

    { "ok": true, "message": "...", "data": {...}, "meta": {...}, "demo": true }

``meta`` solo aparece en listas paginadas.
"""

from __future__ import annotations

from typing import Any

MENSAJE_OK = "Operación realizada correctamente"


def ok(data: Any = None, message: str = MENSAJE_OK) -> dict[str, Any]:
    """Respuesta de éxito sin paginación."""
    return {"ok": True, "message": message, "data": data, "demo": True}


def paginado(data: list[Any], page: int, limit: int, total: int, message: str = MENSAJE_OK) -> dict[str, Any]:
    """Respuesta de éxito para listas paginadas."""
    return {
        "ok": True,
        "message": message,
        "data": data,
        "meta": {"page": page, "limit": limit, "total": total},
        "demo": True,
    }


# ---------------------------------------------------------------------------
# Documentación OpenAPI de errores
# ---------------------------------------------------------------------------

_EJEMPLOS_ERROR: dict[int, tuple[str, str, str]] = {
    400: ("Regla de negocio incumplida", "TRANSICION_INVALIDA", "No se puede pasar de 'borrador' a 'aprobada'"),
    401: ("No autenticado", "NO_AUTENTICADO", "Se requiere autenticación"),
    403: ("Sin permiso", "ACCESO_DENEGADO", "No tiene permiso para acceder a este recurso"),
    404: ("Recurso inexistente", "RECURSO_NO_ENCONTRADO", "El recurso solicitado no existe"),
    409: ("Conflicto", "CONFLICTO", "El recurso ya existe"),
    422: ("Error de validación", "ERROR_VALIDACION", "Los datos enviados no son válidos"),
    429: ("Límite de peticiones", "LIMITE_PETICIONES_EXCEDIDO", "Demasiadas peticiones. Intente de nuevo en un momento."),
}


def errores(*codigos: int) -> dict[int | str, dict[str, Any]]:
    """Genera el bloque ``responses`` de OpenAPI para los códigos de error indicados."""
    respuestas: dict[int | str, dict[str, Any]] = {}
    for codigo in codigos:
        descripcion, code, mensaje = _EJEMPLOS_ERROR[codigo]
        detalles: list[Any] = []
        if codigo == 422:
            detalles = [{"campo": "montoSolicitado", "mensaje": "Debe ser mayor que 0"}]
        respuestas[codigo] = {
            "description": descripcion,
            "content": {
                "application/json": {
                    "example": {
                        "ok": False,
                        "error": {"code": code, "message": mensaje, "details": detalles},
                        "demo": True,
                    }
                }
            },
        }
    return respuestas
