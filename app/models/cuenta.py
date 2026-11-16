"""Modelo de cuenta bancaria demo (solo consulta)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.utils.fechas import ahora
from app.utils.identificadores import enmascarar_cuenta

if TYPE_CHECKING:
    from app.models.movimiento import Movimiento
    from app.models.usuario import Usuario

TIPOS_CUENTA = ("debito", "ahorro")
ESTADOS_CUENTA = ("activa", "bloqueada")


class Cuenta(Base):
    """Cuenta de débito o ahorro de un cliente. Número con formato DEMO-XXXX-XXXX-XXXX."""

    __tablename__ = "cuentas"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    numero: Mapped[str] = mapped_column(String(24), unique=True)
    tipo: Mapped[str] = mapped_column(String(10), default="debito")
    saldo: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    moneda: Mapped[str] = mapped_column(String(3), default="MXN")
    estado: Mapped[str] = mapped_column(String(10), default="activa")
    creada_en: Mapped[datetime] = mapped_column(DateTime, default=ahora)

    usuario: Mapped["Usuario"] = relationship(back_populates="cuentas")
    movimientos: Mapped[list["Movimiento"]] = relationship(
        back_populates="cuenta", cascade="all, delete-orphan"
    )

    @property
    def numero_enmascarado(self) -> str:
        """Número de cuenta enmascarado (****7712)."""
        return enmascarar_cuenta(self.numero)
