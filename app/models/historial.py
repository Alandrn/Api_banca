"""Modelo del historial de cambios de estado de una solicitud."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.utils.fechas import ahora

if TYPE_CHECKING:
    from app.models.solicitud import Solicitud
    from app.models.usuario import Usuario


class HistorialEstado(Base):
    """Registro de una transición de estado (quién, cuándo y por qué)."""

    __tablename__ = "historial_estados"

    id: Mapped[int] = mapped_column(primary_key=True)
    solicitud_id: Mapped[int] = mapped_column(ForeignKey("solicitudes.id"), index=True)
    estado_anterior: Mapped[str | None] = mapped_column(String(20), nullable=True)
    estado_nuevo: Mapped[str] = mapped_column(String(20))
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    nota: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha: Mapped[datetime] = mapped_column(DateTime, default=ahora)

    solicitud: Mapped["Solicitud"] = relationship(back_populates="historial")
    usuario: Mapped["Usuario | None"] = relationship()
