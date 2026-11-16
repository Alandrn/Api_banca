"""Esquemas de cuentas y movimientos (números siempre enmascarados)."""

from __future__ import annotations

from datetime import datetime

from app.schemas.common import DecimalSalida, SchemaBase


class CuentaOut(SchemaBase):
    """Cuenta demo con número enmascarado."""

    id: int
    numero_enmascarado: str
    tipo: str
    saldo: DecimalSalida
    moneda: str
    estado: str
    creada_en: datetime

    model_config = SchemaBase.model_config | {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1,
                    "numeroEnmascarado": "****7712",
                    "tipo": "debito",
                    "saldo": 15230.5,
                    "moneda": "MXN",
                    "estado": "activa",
                    "creadaEn": "2026-05-01T10:00:00",
                }
            ]
        }
    }


class MovimientoOut(SchemaBase):
    """Movimiento de cuenta (monto negativo para cargos)."""

    id: int
    tipo: str
    concepto: str
    monto: DecimalSalida
    saldo_resultante: DecimalSalida
    referencia: str
    fecha: datetime

    model_config = SchemaBase.model_config | {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 10,
                    "tipo": "compra",
                    "concepto": "Compra supermercado demo",
                    "monto": -850.0,
                    "saldoResultante": 14380.5,
                    "referencia": "MOV-DEMO-20261101-A1B2C3D4",
                    "fecha": "2026-11-01T18:22:00",
                }
            ]
        }
    }
