"""Esquemas de estadísticas de administración."""

from __future__ import annotations

from app.schemas.common import DecimalSalida, SchemaBase


class EstadisticasOut(SchemaBase):
    """Indicadores generales del banco demo."""

    total_solicitudes: int
    solicitudes_por_estado: dict[str, int]
    solicitudes_por_tipo: dict[str, int]
    monto_total_aprobado: DecimalSalida
    solicitudes_resueltas: int
    solicitudes_favorables: int
    tasa_aprobacion_pct: DecimalSalida
    usuarios_por_rol: dict[str, int]
    total_cuentas: int
