"""Modelo de movimiento de una cuenta demo."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.utils.fechas import ahora

if TYPE_CHECKING:
    from app.models.cuenta import Cuenta

TIPOS_MOVIMIENTO = ("deposito", "retiro", "pago", "compra", "transferencia")


class Movimiento(Base):
    """Movimiento de cuenta. ``monto`` es negativo para cargos."""

    __tablename__ = "movimientos"

    id: Mapped[int] = mapped_column(primary_key=True)
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("cuentas.id"), index=True)
    tipo: Mapped[str] = mapped_column(String(15), index=True)
    concepto: Mapped[str] = mapped_column(String(160))
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    saldo_resultante: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    referencia: Mapped[str] = mapped_column(String(40), unique=True)
    fecha: Mapped[datetime] = mapped_column(DateTime, default=ahora, index=True)

    cuenta: Mapped["Cuenta"] = relationship(back_populates="movimientos")
