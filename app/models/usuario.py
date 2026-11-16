"""Modelo de usuario del banco demo."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.utils.fechas import ahora

if TYPE_CHECKING:
    from app.models.cuenta import Cuenta
    from app.models.solicitud import Solicitud

ROL_CLIENTE = "cliente"
ROL_VALUADOR = "valuador"
ROL_ANALISTA = "analista"
ROL_ADMIN = "admin"
ROLES = (ROL_CLIENTE, ROL_VALUADOR, ROL_ANALISTA, ROL_ADMIN)


class Usuario(Base):
    """Usuario del sistema (cliente, valuador, analista o admin)."""

    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str | None] = mapped_column(String(20), unique=True, index=True)
    nombre: Mapped[str] = mapped_column(String(80))
    apellidos: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    telefono: Mapped[str | None] = mapped_column(String(20))
    rol: Mapped[str] = mapped_column(String(20), index=True, default=ROL_CLIENTE)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=ahora)

    cuentas: Mapped[list["Cuenta"]] = relationship(back_populates="usuario", cascade="all, delete-orphan")
    solicitudes: Mapped[list["Solicitud"]] = relationship(
        back_populates="usuario", cascade="all, delete-orphan", foreign_keys="Solicitud.usuario_id"
    )

    @property
    def nombre_completo(self) -> str:
        """Nombre y apellidos."""
        return f"{self.nombre} {self.apellidos}"
