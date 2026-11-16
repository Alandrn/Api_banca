"""Modelo con los datos personales, laborales y económicos del solicitante (1:1)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.solicitud import Solicitud

ESTADOS_CIVILES = ("soltero", "casado", "divorciado", "viudo", "union_libre")
TIPOS_EMPLEO = ("asalariado", "independiente")


class Solicitante(Base):
    """Expediente del solicitante de una solicitud de crédito."""

    __tablename__ = "solicitantes"

    id: Mapped[int] = mapped_column(primary_key=True)
    solicitud_id: Mapped[int] = mapped_column(ForeignKey("solicitudes.id"), unique=True)
    fecha_nacimiento: Mapped[date] = mapped_column(Date)
    curp_ficticia: Mapped[str] = mapped_column(String(18))
    estado_civil: Mapped[str] = mapped_column(String(15))
    dependientes: Mapped[int] = mapped_column(Integer, default=0)
    domicilio: Mapped[str] = mapped_column(String(200))
    ciudad: Mapped[str] = mapped_column(String(80))
    empresa: Mapped[str] = mapped_column(String(120))
    puesto: Mapped[str] = mapped_column(String(80))
    tipo_empleo: Mapped[str] = mapped_column(String(15))
    antiguedad_meses: Mapped[int] = mapped_column(Integer)
    ingreso_mensual: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    otros_ingresos: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    gastos_mensuales: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    deudas_mensuales: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    referencias: Mapped[list[dict[str, Any]]] = mapped_column(JSON)

    solicitud: Mapped["Solicitud"] = relationship(back_populates="solicitante")
