"""Modelo del avalúo del inmueble (1:1 con inmueble)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.utils.fechas import ahora

if TYPE_CHECKING:
    from app.models.inmueble import Inmueble
    from app.models.usuario import Usuario

ESTADOS_AVALUO = ("solicitado", "completado")
ESTADOS_CONSERVACION = ("excelente", "bueno", "regular", "malo")


class Avaluo(Base):
    """Avalúo comercial del inmueble realizado por un valuador (simulado)."""

    __tablename__ = "avaluos"

    id: Mapped[int] = mapped_column(primary_key=True)
    folio: Mapped[str | None] = mapped_column(String(30), unique=True, index=True)
    inmueble_id: Mapped[int] = mapped_column(ForeignKey("inmuebles.id"), unique=True)
    valuador_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    estado: Mapped[str] = mapped_column(String(12), default="solicitado")
    fecha_solicitud: Mapped[datetime] = mapped_column(DateTime, default=ahora)
    fecha_visita: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    valor_comercial: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    estado_conservacion: Mapped[str | None] = mapped_column(String(12), nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    generado_automaticamente: Mapped[bool] = mapped_column(Boolean, default=True)

    inmueble: Mapped["Inmueble"] = relationship(back_populates="avaluo")
    valuador: Mapped["Usuario"] = relationship()

    @property
    def solicitud_id(self) -> int | None:
        """Id de la solicitud a la que pertenece el inmueble avaluado."""
        return self.inmueble.solicitud_id if self.inmueble else None

    @property
    def valuador_nombre(self) -> str | None:
        """Nombre completo del valuador asignado."""
        return self.valuador.nombre_completo if self.valuador else None
