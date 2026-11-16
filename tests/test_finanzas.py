"""Pruebas de las utilidades financieras y del motor de análisis."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.utils.analisis import DatosAnalisis, evaluar, tasa_segun_buro
from app.utils.finanzas import (
    calcular_mensualidad,
    cat_demo,
    monto_maximo_por_pago,
    redondear,
    resumen_credito,
    tabla_amortizacion,
)


def _referencia_float(monto: float, tasa: float, n: int) -> float:
    """Cálculo independiente con float para contrastar."""
    i = tasa / 100 / 12
    return round(monto * i * (1 + i) ** n / ((1 + i) ** n - 1), 2)


def test_mensualidad_valor_conocido():
    # Nota: el enunciado menciona ≈ 2,520.37; el método francés exacto da 2,508.30
    assert calcular_mensualidad(50000, Decimal("18.5"), 24) == Decimal("2508.30")


@pytest.mark.parametrize(
    "monto,tasa,plazo,esperado",
    [
        (100000, 12, 12, Decimal("8884.88")),  # valor de libro de texto
        (1000000, 10.5, 240, None),
        (250000, 24, 36, None),
        (2000000, 9.8, 180, None),
    ],
)
def test_mensualidad_contra_referencia(monto, tasa, plazo, esperado):
    resultado = calcular_mensualidad(monto, Decimal(str(tasa)), plazo)
    assert float(resultado) == pytest.approx(_referencia_float(monto, tasa, plazo), abs=0.01)
    if esperado is not None:
        assert resultado == esperado


def test_mensualidad_tasa_cero():
    assert calcular_mensualidad(1200, 0, 12) == Decimal("100.00")
    assert calcular_mensualidad(1000, 0, 3) == Decimal("333.33")


def test_mensualidad_plazo_invalido():
    with pytest.raises(ValueError):
        calcular_mensualidad(1000, 10, 0)


@pytest.mark.parametrize("monto,tasa,plazo", [(50000, 18.5, 24), (1000, 0, 3), (1800000, 10.5, 240),
                                              (12345.67, 15, 60), (10000, 24, 12)])
def test_amortizacion_saldo_final_cero(monto, tasa, plazo):
    tabla = tabla_amortizacion(monto, Decimal(str(tasa)), plazo)
    assert len(tabla) == plazo
    assert tabla[-1]["saldo"] == Decimal("0.00")
    assert sum(f["capital"] for f in tabla) == redondear(monto)
    for fila in tabla:
        assert fila["pago"] == fila["capital"] + fila["interes"]
        assert fila["saldo"] >= 0


def test_amortizacion_tasa_cero_ajusta_ultimo_pago():
    tabla = tabla_amortizacion(1000, 0, 3)
    assert [f["pago"] for f in tabla] == [Decimal("333.33"), Decimal("333.33"), Decimal("333.34")]


def test_resumen_credito():
    r = resumen_credito(50000, Decimal("18.5"), 24)
    assert r["total_pagar"] == r["total_intereses"] + Decimal("50000.00")
    assert r["total_intereses"] > 0


def test_monto_maximo_es_inversa():
    for tasa, plazo in ((Decimal("18.5"), 24), (Decimal("10.5"), 240), (Decimal("0"), 12)):
        pago = calcular_mensualidad(80000, tasa, plazo)
        maximo = monto_maximo_por_pago(pago, tasa, plazo)
        assert abs(maximo - Decimal("80000")) < Decimal("1.00")
        assert calcular_mensualidad(maximo, tasa, plazo) <= pago
    assert monto_maximo_por_pago(0, 10, 12) == Decimal("0.00")


def test_redondeo_half_up():
    assert redondear(Decimal("2.345")) == Decimal("2.35")
    assert redondear(Decimal("2.344")) == Decimal("2.34")
    assert redondear("0.005") == Decimal("0.01")


def test_cat_demo():
    cat = cat_demo(Decimal("18.5"), 24, Decimal("1"))
    assert cat > Decimal("18.5")
    assert cat_demo(0, 12, 0) == Decimal("0.00")
    with pytest.raises(ValueError):
        cat_demo(10, 0)


def test_tasa_segun_buro():
    assert tasa_segun_buro(Decimal("18.5"), 749) == Decimal("18.50")
    assert tasa_segun_buro(Decimal("18.5"), 750) == Decimal("17.50")


def _datos(**cambios) -> DatosAnalisis:
    base = dict(
        tipo="prestamo", monto=Decimal("80000"), plazo_meses=24, tasa_anual=Decimal("18.5"),
        monto_min_producto=Decimal("50000"), ingreso_mensual=Decimal("40000"), otros_ingresos=Decimal("0"),
        deudas_mensuales=Decimal("0"), antiguedad_meses=24, fecha_nacimiento=date(1990, 1, 1),
        fecha_analisis=date(2026, 1, 1), puntaje_buro=700,
    )
    base.update(cambios)
    return DatosAnalisis(**base)


def test_evaluar_aprobada():
    r = evaluar(_datos())
    assert r.resolucion == "aprobada" and r.monto_aprobado == Decimal("80000.00")


def test_evaluar_edad_rechaza():
    r = evaluar(_datos(fecha_nacimiento=date(1950, 1, 1)))
    assert r.resolucion == "rechazada" and "edad" in r.motivo


def test_evaluar_deudas_reducen_capacidad():
    r = evaluar(_datos(ingreso_mensual=Decimal("15000"), deudas_mensuales=Decimal("5000")))
    assert r.resolucion == "condicionada"
    assert r.mensualidad_aprobada <= Decimal("10000") * Decimal("0.35")


def test_evaluar_ingreso_neto_negativo_rechaza():
    r = evaluar(_datos(ingreso_mensual=Decimal("1000"), deudas_mensuales=Decimal("5000")))
    assert r.resolucion == "rechazada"


def test_evaluar_hipoteca_ltv():
    r = evaluar(_datos(tipo="hipoteca", monto=Decimal("1800000"), plazo_meses=240, tasa_anual=Decimal("10.5"),
                       monto_min_producto=Decimal("500000"), ingreso_mensual=Decimal("90000"),
                       valor_inmueble=Decimal("2500000"), valor_comercial=Decimal("1900000")))
    assert r.resolucion == "condicionada" and r.monto_aprobado == Decimal("1710000.00")
    assert r.enganche_requerido == Decimal("790000.00")
    json = r.a_json()
    assert json["resolucion"] == "condicionada" and json["montoMaximo"] == 1710000.0
