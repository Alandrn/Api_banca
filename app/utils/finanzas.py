"""Cálculos financieros con Decimal (método francés de cuota fija).

Todos los importes se redondean a 2 decimales con ROUND_HALF_UP, salvo
``monto_maximo_por_pago`` que trunca (ROUND_DOWN) para no exceder el pago máximo.
"""

from __future__ import annotations

from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal, getcontext
from typing import Any

getcontext().prec = 34

CENTAVO = Decimal("0.01")
CIEN = Decimal("100")
DOCE = Decimal("12")


def a_decimal(valor: Any) -> Decimal:
    """Convierte cualquier número a Decimal (vía str para evitar errores de float)."""
    if isinstance(valor, Decimal):
        return valor
    return Decimal(str(valor))


def redondear(valor: Any) -> Decimal:
    """Redondea a 2 decimales con ROUND_HALF_UP."""
    return a_decimal(valor).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def tasa_mensual(tasa_anual: Any) -> Decimal:
    """Convierte una tasa anual en porcentaje (ej. 18.5) a tasa mensual decimal."""
    return a_decimal(tasa_anual) / CIEN / DOCE


def _validar(monto: Any, plazo_meses: int) -> None:
    if plazo_meses <= 0:
        raise ValueError("El plazo debe ser mayor que cero")
    if a_decimal(monto) < 0:
        raise ValueError("El monto no puede ser negativo")


def calcular_mensualidad(monto: Any, tasa_anual: Any, plazo_meses: int) -> Decimal:
    """Cuota fija mensual (método francés). Si la tasa es 0 devuelve monto/plazo.

    Fórmula: ``P = M * i * (1+i)^n / ((1+i)^n - 1)``.
    """
    _validar(monto, plazo_meses)
    m = a_decimal(monto)
    i = tasa_mensual(tasa_anual)
    if i == 0:
        return redondear(m / plazo_meses)
    factor = (1 + i) ** plazo_meses
    return redondear(m * i * factor / (factor - 1))


def tabla_amortizacion(monto: Any, tasa_anual: Any, plazo_meses: int) -> list[dict[str, Any]]:
    """Tabla mes a mes ``{numero, pago, capital, interes, saldo}``.

    El último pago ajusta el redondeo para que el saldo final sea exactamente 0.00.
    """
    _validar(monto, plazo_meses)
    saldo = redondear(monto)
    i = tasa_mensual(tasa_anual)
    cuota = calcular_mensualidad(monto, tasa_anual, plazo_meses)
    filas: list[dict[str, Any]] = []
    for numero in range(1, plazo_meses + 1):
        interes = redondear(saldo * i)
        if numero == plazo_meses:
            capital = saldo
        else:
            capital = min(cuota - interes, saldo)
        pago = capital + interes
        saldo = saldo - capital
        filas.append(
            {
                "numero": numero,
                "pago": redondear(pago),
                "capital": redondear(capital),
                "interes": interes,
                "saldo": redondear(saldo),
            }
        )
    return filas


def resumen_credito(monto: Any, tasa_anual: Any, plazo_meses: int) -> dict[str, Decimal]:
    """Mensualidad, total a pagar y total de intereses (sumando la tabla real)."""
    tabla = tabla_amortizacion(monto, tasa_anual, plazo_meses)
    total = sum((f["pago"] for f in tabla), Decimal("0"))
    return {
        "mensualidad": calcular_mensualidad(monto, tasa_anual, plazo_meses),
        "total_pagar": redondear(total),
        "total_intereses": redondear(total - redondear(monto)),
    }


def monto_maximo_por_pago(pago_maximo: Any, tasa_anual: Any, plazo_meses: int) -> Decimal:
    """Inversa de la mensualidad: el monto máximo cuya cuota no excede ``pago_maximo``.

    Fórmula: ``M = P * (1 - (1+i)^-n) / i``. Trunca a centavos (ROUND_DOWN).
    """
    if plazo_meses <= 0:
        raise ValueError("El plazo debe ser mayor que cero")
    p = a_decimal(pago_maximo)
    if p <= 0:
        return Decimal("0.00")
    i = tasa_mensual(tasa_anual)
    if i == 0:
        monto = p * plazo_meses
    else:
        monto = p * (1 - (1 + i) ** (-plazo_meses)) / i
    return monto.quantize(CENTAVO, rounding=ROUND_DOWN)


def cat_demo(tasa_anual: Any, plazo_meses: int, comision_apertura_pct: Any = Decimal("1.00")) -> Decimal:
    """CAT DEMOSTRATIVO (aproximación simple, NO es el cálculo oficial de Banxico).

    ``CAT ≈ ((1 + tasa_mensual)^12 - 1) * 100 + comision_apertura_pct * 12 / plazo``

    Es decir, la tasa efectiva anual más la comisión de apertura prorrateada por año
    del plazo. Resultado en porcentaje con 2 decimales.
    """
    if plazo_meses <= 0:
        raise ValueError("El plazo debe ser mayor que cero")
    i = tasa_mensual(tasa_anual)
    efectiva = ((1 + i) ** 12 - 1) * CIEN
    comision = a_decimal(comision_apertura_pct) * DOCE / plazo_meses
    return redondear(efectiva + comision)
