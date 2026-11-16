"""Router de sistema: estado de salud de la API."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.responses import ok
from app.schemas.common import Respuesta, SchemaBase
from app.utils.fechas import ahora

router = APIRouter(tags=["Sistema"])


class HealthOut(SchemaBase):
    """Estado del servicio."""

    estado: str
    servicio: str
    version: str
    base_datos: str
    fecha: str


@router.get(
    "/health",
    response_model=Respuesta[HealthOut],
    summary="Estado de la API",
    description="Verifica que la API esté en línea y que la base de datos responda. Público.",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "ok": True,
                        "message": "API en línea",
                        "data": {
                            "estado": "ok",
                            "servicio": "API Banco Demo",
                            "version": "1.0.0",
                            "baseDatos": "ok",
                            "fecha": "2026-11-15T12:00:00",
                        },
                        "demo": True,
                    }
                }
            }
        }
    },
)
def health(db: Session = Depends(get_db)):
    """Comprueba la conexión a la base de datos."""
    try:
        db.execute(text("SELECT 1"))
        estado_bd = "ok"
    except Exception:  # noqa: BLE001 - solo reporta el estado
        estado_bd = "error"
    datos = HealthOut(
        estado="ok" if estado_bd == "ok" else "degradado",
        servicio=settings.APP_NAME,
        version=settings.APP_VERSION,
        base_datos=estado_bd,
        fecha=ahora().isoformat(),
    )
    return ok(datos, "API en línea")
