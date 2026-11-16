"""Motor de análisis de crédito (lógica pura, sin base de datos ni HTTP).

Reglas (umbrales configurables en ``core/config.py``):

1. Capacidad de pago: mensualidad ≤ 35% de (ingreso + otros ingresos − deudas).
2. LTV (solo hipoteca): monto ≤ 90% del valor comercial del avalúo.
3. Puntaje de buró ficticio (400–850, reproducible a partir del folio) ≥ 600.
4. Antigüedad laboral ≥ 6 meses.
5. Edad al terminar el plazo ≤ 70 años.

Resolución:

- Cumple todas → ``aprobada``.
- Falla solo capacidad de pago y/o LTV → ``condicionada`` con el monto máximo que sí
  cumple (redondeado hacia abajo a centenas), salvo que sea menor al mínimo del
  producto → ``rechazada``.
- Falla buró, edad o antigüedad → ``rechazada`` (decisión de diseño: la antigüedad
  insuficiente se acepta al capturar datos pero el análisis la penaliza rechazando).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_DOWN, Decimal
from typing import Any

from app.core.config import settings
from app.utils.fechas import edad_en, sumar_meses
from app.utils.finanzas import a_decimal, calcular_mensualidad, monto_maximo_por_pago, redondear

BURO_MIN = 400
BURO_MAX = 850


def calcular_puntaje_buro(folio: str) -> int:
    """Puntaje de buró FICTICIO entre 400 y 850, reproducible a partir del folio."""
    digest = hashlib.sha256(folio.encode("utf-8")).hexdigest()
    return BURO_MIN + int(digest[:8], 16) % (BURO_MAX - BURO_MIN + 1)


@dataclass
class DatosAnalisis:
    """Entradas del análisis."""

    tipo: str
    monto: Decimal
    plazo_meses: int
    tasa_anual: Decimal
    monto_min_producto: Decimal
    ingreso_mensual: Decimal
    otros_ingresos: Decimal
    deudas_mensuales: Decimal
    antiguedad_meses: int
    fecha_nacimiento: date
    fecha_analisis: date
    puntaje_buro: int
    valor_inmueble: Decimal | None = None
    valor_comercial: Decimal | None = None


@dataclass
class ResultadoAnalisis:
    """Salida del análisis."""

    resolucion: str
    reglas: list[dict[str, Any]]
    tasa_aprobada: Decimal | None
    monto_aprobado: Decimal | None
    plazo_aprobado: int | None
    mensualidad_aprobada: Decimal | None
    enganche_requerido: Decimal | None
    motivo: str
    resumen: dict[str, Any] = field(default_factory=dict)

    def a_json(self) -> dict[str, Any]:
        """Representación JSON-serializable para guardar en ``resultado_analisis``."""
        return {"resolucion": self.resolucion, "reglas": self.reglas, **self.resumen}


def _f(valor: Decimal | None) -> float | None:
    return None if valor is None else float(valor)


def tasa_segun_buro(tasa_anual: Decimal, puntaje: int) -> Decimal:
    """Tasa aprobada: descuenta 1 punto porcentual si el buró es preferente (≥ 750)."""
    tasa = a_decimal(tasa_anual)
    if puntaje >= settings.ANALISIS_BURO_PREFERENTE:
        tasa = max(Decimal("0.00"), tasa - settings.ANALISIS_DESCUENTO_PREFERENTE)
    return redondear(tasa)


def evaluar(d: DatosAnalisis) -> ResultadoAnalisis:
    """Evalúa una solicitud y devuelve la resolución con el detalle de cada regla."""
    es_hipoteca = d.tipo == "hipoteca"
    tasa = tasa_segun_buro(d.tasa_anual, d.puntaje_buro)
    mensualidad = calcular_mensualidad(d.monto, tasa, d.plazo_meses)

    ingreso_neto = redondear(d.ingreso_mensual + d.otros_ingresos - d.deudas_mensuales)
    pago_maximo = redondear(max(Decimal("0"), ingreso_neto) * settings.ANALISIS_MAX_RELACION_PAGO)
    relacion = redondear(mensualidad / ingreso_neto * 100) if ingreso_neto > 0 else None
    cumple_capacidad = ingreso_neto > 0 and mensualidad <= pago_maximo

    reglas: list[dict[str, Any]] = [
        {
            "regla": "capacidad_pago",
            "descripcion": "Mensualidad ≤ 35% del ingreso neto (ingreso + otros − deudas)",
            "valor": _f(relacion),
            "limite": float(settings.ANALISIS_MAX_RELACION_PAGO * 100),
            "cumple": cumple_capacidad,
        }
    ]

    cumple_ltv = True
    ltv_max_monto: Decimal | None = None
    if es_hipoteca:
        valor_comercial = d.valor_comercial or Decimal("0")
        ltv = redondear(d.monto / valor_comercial * 100) if valor_comercial > 0 else None
        ltv_max_monto = redondear(valor_comercial * settings.ANALISIS_MAX_LTV)
        cumple_ltv = valor_comercial > 0 and d.monto <= ltv_max_monto
        reglas.append(
            {
                "regla": "ltv",
                "descripcion": "Monto ≤ 90% del valor comercial del avalúo",
                "valor": _f(ltv),
                "limite": float(settings.ANALISIS_MAX_LTV * 100),
                "cumple": cumple_ltv,
            }
        )

    cumple_buro = d.puntaje_buro >= settings.ANALISIS_BURO_MINIMO
    reglas.append(
        {
            "regla": "buro",
            "descripcion": "Puntaje de buró ficticio mínimo",
            "valor": d.puntaje_buro,
            "limite": settings.ANALISIS_BURO_MINIMO,
            "cumple": cumple_buro,
        }
    )

    cumple_antiguedad = d.antiguedad_meses >= settings.ANALISIS_ANTIGUEDAD_MIN_MESES
    reglas.append(
        {
            "regla": "antiguedad_laboral",
            "descripcion": "Antigüedad laboral mínima en meses",
            "valor": d.antiguedad_meses,
            "limite": settings.ANALISIS_ANTIGUEDAD_MIN_MESES,
            "cumple": cumple_antiguedad,
        }
    )

    fecha_fin = sumar_meses(d.fecha_analisis, d.plazo_meses)
    edad_fin = edad_en(d.fecha_nacimiento, fecha_fin)
    cumple_edad = edad_fin <= settings.EDAD_MAXIMA_FIN_PLAZO
    reglas.append(
        {
            "regla": "edad_fin_plazo",
            "descripcion": "Edad al terminar el plazo del crédito",
            "valor": edad_fin,
            "limite": settings.EDAD_MAXIMA_FIN_PLAZO,
            "cumple": cumple_edad,
        }
    )

    resumen: dict[str, Any] = {
        "puntajeBuro": d.puntaje_buro,
        "ingresoNeto": float(ingreso_neto),
        "pagoMaximo": float(pago_maximo),
        "mensualidadSolicitada": float(mensualidad),
        "tasaAplicada": float(tasa),
        "fechaAnalisis": d.fecha_analisis.isoformat(),
    }

    def rechazo(motivo: str) -> ResultadoAnalisis:
        return ResultadoAnalisis("rechazada", reglas, None, None, None, None, None, motivo, resumen)

    # Reglas no corregibles → rechazo
    motivos: list[str] = []
    if not cumple_buro:
        motivos.append(f"puntaje de buró {d.puntaje_buro} menor al mínimo {settings.ANALISIS_BURO_MINIMO}")
    if not cumple_edad:
        motivos.append(f"la edad al terminar el plazo ({edad_fin}) excede {settings.EDAD_MAXIMA_FIN_PLAZO} años")
    if not cumple_antiguedad:
        motivos.append(
            f"antigüedad laboral de {d.antiguedad_meses} meses, menor a {settings.ANALISIS_ANTIGUEDAD_MIN_MESES}"
        )
    if motivos:
        return rechazo("Solicitud rechazada: " + "; ".join(motivos) + ".")

    if cumple_capacidad and cumple_ltv:
        return ResultadoAnalisis(
            "aprobada",
            reglas,
            tasa,
            redondear(d.monto),
            d.plazo_meses,
            mensualidad,
            redondear(d.valor_inmueble - d.monto) if es_hipoteca and d.valor_inmueble else None,
            "Solicitud aprobada: cumple todas las reglas del análisis.",
            resumen,
        )

    # Falla capacidad y/o LTV → calcular monto máximo que sí cumple
    limites = [d.monto]
    if not cumple_capacidad:
        limites.append(monto_maximo_por_pago(pago_maximo, tasa, d.plazo_meses))
    if not cumple_ltv and ltv_max_monto is not None:
        limites.append(ltv_max_monto)
    paso = settings.ANALISIS_REDONDEO_MONTO_CONDICIONADO
    monto_max = (min(limites) / paso).to_integral_value(rounding=ROUND_DOWN) * paso
    monto_max = redondear(monto_max)
    resumen["montoMaximo"] = float(monto_max)

    if monto_max < d.monto_min_producto:
        return rechazo(
            f"Solicitud rechazada: el monto máximo que cumple las reglas ({monto_max}) es menor al "
            f"mínimo del producto ({redondear(d.monto_min_producto)})."
        )

    mensualidad_max = calcular_mensualidad(monto_max, tasa, d.plazo_meses)
    fallas = []
    if not cumple_capacidad:
        fallas.append("capacidad de pago")
    if not cumple_ltv:
        fallas.append("LTV")
    enganche_req = None
    motivo = f"Solicitud condicionada por {' y '.join(fallas)}: el monto máximo autorizado es {monto_max}"
    if es_hipoteca and d.valor_inmueble:
        enganche_req = redondear(d.valor_inmueble - monto_max)
        motivo += f"; se requiere un enganche de {enganche_req}"
    motivo += "."
    return ResultadoAnalisis(
        "condicionada", reglas, tasa, monto_max, d.plazo_meses, mensualidad_max, enganche_req, motivo, resumen
    )
