"""Modelo de documento simulado del expediente (no se suben archivos reales)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.utils.fechas import ahora

if TYPE_CHECKING:
    from app.models.solicitud import Solicitud

ESTADOS_DOCUMENTO = ("entregado", "validado", "rechazado")


class DocumentoSolicitud(Base):
    """Documento entregado para una solicitud. Solo se guarda el nombre simulado."""

    __tablename__ = "documentos_solicitud"
    __table_args__ = (UniqueConstraint("solicitud_id", "tipo", name="uq_documento_solicitud_tipo"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    solicitud_id: Mapped[int] = mapped_column(ForeignKey("solicitudes.id"), index=True)
    tipo: Mapped[str] = mapped_column(String(30))
    nombre_archivo_simulado: Mapped[str] = mapped_column(String(150))
    estado: Mapped[str] = mapped_column(String(12), default="entregado")
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha: Mapped[datetime] = mapped_column(DateTime, default=ahora)

    solicitud: Mapped["Solicitud"] = relationship(back_populates="documentos")
