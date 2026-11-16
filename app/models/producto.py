"""Modelo de producto de crédito (préstamo personal o hipoteca)."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import JSON, Boolean, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

TIPO_PRESTAMO = "prestamo"
TIPO_HIPOTECA = "hipoteca"
TIPOS_PRODUCTO = (TIPO_PRESTAMO, TIPO_HIPOTECA)

TIPOS_DOCUMENTO = (
    "identificacion",
    "comprobante_domicilio",
    "comprobante_ingresos",
    "estados_cuenta",
    "escrituras",
    "predial",
)
DOCUMENTOS_SOLO_HIPOTECA = ("escrituras", "predial")

DESCRIPCION_DOCUMENTOS = {
    "identificacion": "Identificación oficial vigente (simulada)",
    "comprobante_domicilio": "Comprobante de domicilio no mayor a 3 meses (simulado)",
    "comprobante_ingresos": "Comprobante de ingresos de los últimos 3 meses (simulado)",
    "estados_cuenta": "Estados de cuenta bancarios de los últimos 3 meses (simulados)",
    "escrituras": "Escrituras o contrato de compraventa del inmueble (simulado)",
    "predial": "Boleta predial al corriente del inmueble (simulada)",
}


class ProductoCredito(Base):
    """Producto de crédito ofrecido por el banco demo."""

    __tablename__ = "productos_credito"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), unique=True)
    tipo: Mapped[str] = mapped_column(String(10), index=True)
    descripcion: Mapped[str] = mapped_column(Text)
    tasa_anual: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    monto_min: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    monto_max: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    plazos_meses: Mapped[list[int]] = mapped_column(JSON)
    enganche_min_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    documentos_requeridos: Mapped[list[str]] = mapped_column(JSON)
    requisitos: Mapped[list[str]] = mapped_column(JSON)
    condiciones: Mapped[str] = mapped_column(Text)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
