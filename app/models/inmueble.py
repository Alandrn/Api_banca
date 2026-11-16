"""Modelo del inmueble a hipotecar (1:1 con solicitud de hipoteca)."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.avaluo import Avaluo
    from app.models.solicitud import Solicitud

TIPOS_INMUEBLE = ("casa", "departamento", "terreno")


class Inmueble(Base):
    """Inmueble en garantía de una hipoteca."""

    __tablename__ = "inmuebles"

    id: Mapped[int] = mapped_column(primary_key=True)
    solicitud_id: Mapped[int] = mapped_column(ForeignKey("solicitudes.id"), unique=True)
    tipo: Mapped[str] = mapped_column(String(15))
    direccion: Mapped[str] = mapped_column(String(200))
    colonia: Mapped[str] = mapped_column(String(100))
    ciudad: Mapped[str] = mapped_column(String(80))
    estado: Mapped[str] = mapped_column(String(60))
    cp: Mapped[str] = mapped_column(String(5))
    m2_terreno: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    m2_construccion: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    antiguedad_anios: Mapped[int] = mapped_column(Integer)
    recamaras: Mapped[int] = mapped_column(Integer, default=0)
    banos: Mapped[int] = mapped_column(Integer, default=0)
    valor_estimado_cliente: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    solicitud: Mapped["Solicitud"] = relationship(back_populates="inmueble")
    avaluo: Mapped["Avaluo | None"] = relationship(
        back_populates="inmueble", uselist=False, cascade="all, delete-orphan"
    )
