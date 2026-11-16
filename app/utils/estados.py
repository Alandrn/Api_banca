"""Máquina de estados de las solicitudes de crédito."""

from __future__ import annotations

from app.core.exceptions import ApiError

BORRADOR = "borrador"
DATOS_COMPLETOS = "datos_completos"
EN_AVALUO = "en_avaluo"
AVALUO_COMPLETADO = "avaluo_completado"
EN_ANALISIS = "en_analisis"
APROBADA = "aprobada"
CONDICIONADA = "condicionada"
RECHAZADA = "rechazada"
OFERTA_ACEPTADA = "oferta_aceptada"
OFERTA_RECHAZADA = "oferta_rechazada"
FORMALIZADA = "formalizada"
CANCELADA = "cancelada"

ESTADOS = (
    BORRADOR,
    DATOS_COMPLETOS,
    EN_AVALUO,
    AVALUO_COMPLETADO,
    EN_ANALISIS,
    APROBADA,
    CONDICIONADA,
    RECHAZADA,
    OFERTA_ACEPTADA,
    OFERTA_RECHAZADA,
    FORMALIZADA,
    CANCELADA,
)

TRANSICIONES: dict[str, set[str]] = {
    BORRADOR: {DATOS_COMPLETOS, CANCELADA},
    DATOS_COMPLETOS: {EN_AVALUO, EN_ANALISIS, CANCELADA},
    EN_AVALUO: {AVALUO_COMPLETADO, CANCELADA},
    AVALUO_COMPLETADO: {EN_ANALISIS, CANCELADA},
    EN_ANALISIS: {APROBADA, CONDICIONADA, RECHAZADA},
    APROBADA: {OFERTA_ACEPTADA, OFERTA_RECHAZADA, CANCELADA},
    CONDICIONADA: {OFERTA_ACEPTADA, OFERTA_RECHAZADA, CANCELADA},
    OFERTA_ACEPTADA: {FORMALIZADA},
    RECHAZADA: set(),
    OFERTA_RECHAZADA: set(),
    FORMALIZADA: set(),
    CANCELADA: set(),
}

# Transiciones que solo aplican a un tipo de crédito.
RESTRICCIONES_TIPO: dict[tuple[str, str], str] = {
    (DATOS_COMPLETOS, EN_AVALUO): "hipoteca",
    (DATOS_COMPLETOS, EN_ANALISIS): "prestamo",
}

ESTADOS_FINALES = frozenset({RECHAZADA, OFERTA_RECHAZADA, FORMALIZADA, CANCELADA})
ESTADOS_EDITABLES = frozenset({BORRADOR, DATOS_COMPLETOS})
ESTADOS_RESUELTOS = frozenset({APROBADA, CONDICIONADA, RECHAZADA})
ESTADOS_CON_OFERTA = frozenset({APROBADA, CONDICIONADA})
ESTADOS_FAVORABLES = frozenset({APROBADA, CONDICIONADA, OFERTA_ACEPTADA, OFERTA_RECHAZADA, FORMALIZADA})


def es_final(estado: str) -> bool:
    """Indica si el estado es final (no admite más transiciones)."""
    return estado in ESTADOS_FINALES


def puede_transitar(actual: str, nuevo: str, tipo: str | None = None) -> bool:
    """Indica si la transición es válida (considerando el tipo de crédito si se indica)."""
    if nuevo not in TRANSICIONES.get(actual, set()):
        return False
    requerido = RESTRICCIONES_TIPO.get((actual, nuevo))
    return not (requerido and tipo and tipo != requerido)


def validar_transicion(actual: str, nuevo: str, tipo: str | None = None) -> None:
    """Valida una transición; lanza ApiError 400 TRANSICION_INVALIDA si no está permitida."""
    if actual not in TRANSICIONES:
        raise ApiError(400, "TRANSICION_INVALIDA", f"Estado actual desconocido: '{actual}'")
    if not puede_transitar(actual, nuevo, tipo):
        requerido = RESTRICCIONES_TIPO.get((actual, nuevo))
        if requerido and tipo and tipo != requerido and nuevo in TRANSICIONES[actual]:
            mensaje = f"La transición de '{actual}' a '{nuevo}' solo aplica a solicitudes de tipo {requerido}"
        else:
            mensaje = f"No se puede pasar de '{actual}' a '{nuevo}'"
        permitidos = sorted(
            e for e in TRANSICIONES[actual] if puede_transitar(actual, e, tipo)
        )
        raise ApiError(
            400,
            "TRANSICION_INVALIDA",
            mensaje,
            [{"estadoActual": actual, "estadoSolicitado": nuevo, "permitidos": permitidos}],
        )
