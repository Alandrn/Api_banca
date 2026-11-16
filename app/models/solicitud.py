"""Modelo de solicitud de crédito (préstamo o hipoteca)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.utils.fechas import ahora

if TYPE_CHECKING:
    from app.models.documento import DocumentoSolicitud
    from app.models.historial import HistorialEstado
    from app.models.inmueble import Inmueble
    from app.models.producto import ProductoCredito
    from app.models.solicitante import Solicitante
    from app.models.usuario import Usuario


class Solicitud(Base):
    """Solicitud de crédito con su estado dentro de la máquina de estados."""

    __tablename__ = "solicitudes"

    id: Mapped[int] = mapped_column(primary_key=True)
    folio: Mapped[str | None] = mapped_column(String(30), unique=True, index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos_credito.id"), index=True)
    tipo: Mapped[str] = mapped_column(String(10), index=True)
    monto_solicitado: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    plazo_meses: Mapped[int] = mapped_column(Integer)
    valor_inmueble: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    enganche: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    estado: Mapped[str] = mapped_column(String(20), index=True, default="borrador")
    puntaje_buro: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resultado_analisis: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    monto_aprobado: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    tasa_aprobada: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    plazo_aprobado: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mensualidad_aprobada: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    enganche_requerido: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    motivo_resolucion: Mapped[str | None] = mapped_column(Text, nullable=True)
    creada_en: Mapped[datetime] = mapped_column(DateTime, default=ahora)
    actualizada_en: Mapped[datetime] = mapped_column(DateTime, default=ahora, onupdate=ahora)
    resuelta_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    formalizada_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    usuario: Mapped["Usuario"] = relationship(back_populates="solicitudes", foreign_keys=[usuario_id])
    producto: Mapped["ProductoCredito"] = relationship()
    solicitante: Mapped["Solicitante | None"] = relationship(
        back_populates="solicitud", uselist=False, cascade="all, delete-orphan"
    )
    inmueble: Mapped["Inmueble | None"] = relationship(
        back_populates="solicitud", uselist=False, cascade="all, delete-orphan"
    )
    documentos: Mapped[list["DocumentoSolicitud"]] = relationship(
        back_populates="solicitud", cascade="all, delete-orphan", order_by="DocumentoSolicitud.id"
    )
    historial: Mapped[list["HistorialEstado"]] = relationship(
        back_populates="solicitud", cascade="all, delete-orphan", order_by="HistorialEstado.id"
    )
