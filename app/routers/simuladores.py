"""Router de simuladores públicos."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.responses import errores, ok
from app.schemas.common import Respuesta
from app.schemas.simuladores import (
    AmortizacionIn,
    AmortizacionOut,
    SimuladorHipotecaIn,
    SimuladorHipotecaOut,
    SimuladorPrestamoIn,
    SimuladorPrestamoOut,
)
from app.services import simuladores as simuladores_service

router = APIRouter(prefix="/simuladores", tags=["Simuladores"])


@router.post(
    "/prestamo",
    response_model=Respuesta[SimuladorPrestamoOut],
    summary="Simular préstamo",
    description=(
        "Calcula mensualidad (método francés), total de intereses, total a pagar y CAT demostrativo. "
        "Indique `tasaAnual` o `productoId` (en ese caso se valida monto y plazo del producto). Público."
    ),
    responses=errores(400, 404, 422),
)
def prestamo(datos: SimuladorPrestamoIn, db: Session = Depends(get_db)):
    """Simulador de préstamo."""
    resultado = simuladores_service.simular_prestamo(db, datos.model_dump())
    return ok(SimuladorPrestamoOut.model_validate(resultado), "Simulación de préstamo")


@router.post(
    "/hipoteca",
    response_model=Respuesta[SimuladorHipotecaOut],
    summary="Simular hipoteca",
    description=(
        "Igual que el préstamo más valor del inmueble, enganche, % de enganche y validación del enganche "
        "mínimo (del producto o 10% por defecto). Monto del crédito = valor − enganche. Público."
    ),
    responses=errores(400, 404, 422),
)
def hipoteca(datos: SimuladorHipotecaIn, db: Session = Depends(get_db)):
    """Simulador de hipoteca."""
    resultado = simuladores_service.simular_hipoteca(db, datos.model_dump())
    return ok(SimuladorHipotecaOut.model_validate(resultado), "Simulación de hipoteca")


@router.post(
    "/amortizacion",
    response_model=Respuesta[AmortizacionOut],
    summary="Tabla de amortización",
    description="Tabla mes a mes (número, pago, capital, interés, saldo). El último pago deja el saldo en 0.00. Público.",
    responses=errores(422),
)
def amortizacion(datos: AmortizacionIn):
    """Tabla de amortización."""
    resultado = simuladores_service.simular_amortizacion(datos.model_dump())
    return ok(AmortizacionOut.model_validate(resultado), "Tabla de amortización")
