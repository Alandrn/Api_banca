"""Router de cuentas (solo consulta)."""

from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.responses import errores, ok, paginado
from app.dependencies.auth import Paginacion, paginacion, require_roles
from app.models.usuario import ROL_CLIENTE, Usuario
from app.schemas.common import Respuesta, RespuestaPaginada
from app.schemas.cuentas import CuentaOut, MovimientoOut
from app.services import cuentas as cuentas_service

router = APIRouter(prefix="/cuentas", tags=["Cuentas"])
solo_cliente = require_roles(ROL_CLIENTE)


@router.get(
    "",
    response_model=Respuesta[list[CuentaOut]],
    summary="Mis cuentas",
    description="Cuentas demo del cliente autenticado con número enmascarado.",
    responses=errores(401, 403),
)
def listar(usuario: Usuario = Depends(solo_cliente), db: Session = Depends(get_db)):
    """Cuentas del cliente."""
    return ok([CuentaOut.model_validate(c) for c in cuentas_service.listar(db, usuario)], "Cuentas")


@router.get(
    "/{cuenta_id}",
    response_model=Respuesta[CuentaOut],
    summary="Detalle de cuenta",
    description="Detalle de una cuenta propia (número enmascarado ****7712). 403 ACCESO_DENEGADO si es de otro cliente.",
    responses=errores(401, 403, 404),
)
def obtener(cuenta_id: int, usuario: Usuario = Depends(solo_cliente), db: Session = Depends(get_db)):
    """Detalle de cuenta."""
    return ok(CuentaOut.model_validate(cuentas_service.obtener(db, cuenta_id, usuario)), "Cuenta")


@router.get(
    "/{cuenta_id}/movimientos",
    response_model=RespuestaPaginada[MovimientoOut],
    summary="Movimientos de la cuenta",
    description="Paginado, del más reciente al más antiguo. Filtros `desde`, `hasta` (AAAA-MM-DD, desde ≤ hasta) y `tipo`.",
    responses=errores(400, 401, 403, 404, 422),
)
def movimientos(
    cuenta_id: int,
    desde: date | None = Query(None, description="Fecha inicial (AAAA-MM-DD)"),
    hasta: date | None = Query(None, description="Fecha final (AAAA-MM-DD)"),
    tipo: Literal["deposito", "retiro", "pago", "compra", "transferencia"] | None = Query(None),
    pag: Paginacion = Depends(paginacion),
    usuario: Usuario = Depends(solo_cliente),
    db: Session = Depends(get_db),
):
    """Movimientos de cuenta."""
    filas, total = cuentas_service.movimientos(
        db, cuenta_id, usuario, desde=desde, hasta=hasta, tipo=tipo, offset=pag.offset, limit=pag.limit
    )
    return paginado([MovimientoOut.model_validate(m) for m in filas], pag.page, pag.limit, total, "Movimientos")
