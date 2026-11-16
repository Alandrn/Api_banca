"""Utilidades de fechas. Todas las fechas se manejan en UTC (sin zona en BD)."""

from __future__ import annotations

import calendar
from datetime import date, datetime, timezone


def ahora() -> datetime:
    """Fecha y hora actual en UTC sin información de zona (formato de almacenamiento)."""
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


def hoy() -> date:
    """Fecha actual en UTC."""
    return ahora().date()


def sumar_meses(fecha: date, meses: int) -> date:
    """Suma meses a una fecha ajustando el día al último del mes si es necesario."""
    mes_total = fecha.month - 1 + meses
    anio = fecha.year + mes_total // 12
    mes = mes_total % 12 + 1
    dia = min(fecha.day, calendar.monthrange(anio, mes)[1])
    return date(anio, mes, dia)


def edad_en(fecha_nacimiento: date, fecha: date) -> int:
    """Edad cumplida (años completos) en una fecha dada."""
    anios = fecha.year - fecha_nacimiento.year
    if (fecha.month, fecha.day) < (fecha_nacimiento.month, fecha_nacimiento.day):
        anios -= 1
    return anios
