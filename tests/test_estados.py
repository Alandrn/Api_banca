"""Pruebas de la máquina de estados."""

from __future__ import annotations

import pytest

from app.core.exceptions import ApiError
from app.utils import estados as E

VALIDAS = [
    (E.BORRADOR, E.DATOS_COMPLETOS, None),
    (E.BORRADOR, E.CANCELADA, None),
    (E.DATOS_COMPLETOS, E.EN_AVALUO, "hipoteca"),
    (E.DATOS_COMPLETOS, E.EN_ANALISIS, "prestamo"),
    (E.DATOS_COMPLETOS, E.CANCELADA, "prestamo"),
    (E.EN_AVALUO, E.AVALUO_COMPLETADO, "hipoteca"),
    (E.EN_AVALUO, E.CANCELADA, "hipoteca"),
    (E.AVALUO_COMPLETADO, E.EN_ANALISIS, "hipoteca"),
    (E.AVALUO_COMPLETADO, E.CANCELADA, "hipoteca"),
    (E.EN_ANALISIS, E.APROBADA, None),
    (E.EN_ANALISIS, E.CONDICIONADA, None),
    (E.EN_ANALISIS, E.RECHAZADA, None),
    (E.APROBADA, E.OFERTA_ACEPTADA, None),
    (E.APROBADA, E.OFERTA_RECHAZADA, None),
    (E.APROBADA, E.CANCELADA, None),
    (E.CONDICIONADA, E.OFERTA_ACEPTADA, None),
    (E.CONDICIONADA, E.OFERTA_RECHAZADA, None),
    (E.CONDICIONADA, E.CANCELADA, None),
    (E.OFERTA_ACEPTADA, E.FORMALIZADA, None),
]

INVALIDAS = [
    (E.BORRADOR, E.APROBADA, None),
    (E.BORRADOR, E.EN_ANALISIS, "prestamo"),
    (E.DATOS_COMPLETOS, E.EN_AVALUO, "prestamo"),
    (E.DATOS_COMPLETOS, E.EN_ANALISIS, "hipoteca"),
    (E.EN_AVALUO, E.EN_ANALISIS, "hipoteca"),
    (E.EN_ANALISIS, E.CANCELADA, None),
    (E.APROBADA, E.FORMALIZADA, None),
    (E.OFERTA_ACEPTADA, E.CANCELADA, None),
    (E.RECHAZADA, E.APROBADA, None),
    (E.FORMALIZADA, E.CANCELADA, None),
    (E.CANCELADA, E.BORRADOR, None),
    (E.OFERTA_RECHAZADA, E.OFERTA_ACEPTADA, None),
]


@pytest.mark.parametrize("actual,nuevo,tipo", VALIDAS)
def test_transiciones_validas(actual, nuevo, tipo):
    E.validar_transicion(actual, nuevo, tipo)
    assert E.puede_transitar(actual, nuevo, tipo)


@pytest.mark.parametrize("actual,nuevo,tipo", INVALIDAS)
def test_transiciones_invalidas(actual, nuevo, tipo):
    with pytest.raises(ApiError) as exc:
        E.validar_transicion(actual, nuevo, tipo)
    assert exc.value.status_code == 400 and exc.value.code == "TRANSICION_INVALIDA"
    assert exc.value.details[0]["estadoActual"] == actual


def test_mensaje_restriccion_por_tipo():
    with pytest.raises(ApiError) as exc:
        E.validar_transicion(E.DATOS_COMPLETOS, E.EN_AVALUO, "prestamo")
    assert "hipoteca" in exc.value.message
    assert exc.value.details[0]["permitidos"] == [E.CANCELADA, E.EN_ANALISIS]


def test_estado_desconocido():
    with pytest.raises(ApiError):
        E.validar_transicion("inventado", E.BORRADOR)


@pytest.mark.parametrize("estado", sorted(E.ESTADOS_FINALES))
def test_estados_finales_sin_salida(estado):
    assert E.es_final(estado) and E.TRANSICIONES[estado] == set()


def test_todos_los_estados_definidos():
    assert set(E.TRANSICIONES) == set(E.ESTADOS)
    destinos = set().union(*E.TRANSICIONES.values())
    assert destinos <= set(E.ESTADOS)
    assert E.ESTADOS_EDITABLES == {E.BORRADOR, E.DATOS_COMPLETOS}
