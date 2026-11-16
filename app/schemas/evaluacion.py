"""Esquemas de inmueble, avalúo y resolución del análisis."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field, model_validator

from app.schemas.common import Dinero, Porcentaje, SchemaBase


class InmuebleIn(SchemaBase):
    """Datos del inmueble a hipotecar."""

    tipo: Literal["casa", "departamento", "terreno"]
    direccion: str = Field(min_length=5, max_length=200)
    colonia: str = Field(min_length=2, max_length=100)
    ciudad: str = Field(min_length=2, max_length=80)
    estado: str = Field(min_length=2, max_length=60)
    cp: str = Field(pattern=r"^[0-9]{5}$")
    m2_terreno: Decimal = Field(gt=Decimal("0"), max_digits=10, decimal_places=2)
    m2_construccion: Decimal = Field(ge=Decimal("0"), max_digits=10, decimal_places=2)
    antiguedad_anios: int = Field(ge=0, le=200)
    recamaras: int = Field(default=0, ge=0, le=30)
    banos: int = Field(default=0, ge=0, le=30)
    valor_estimado_cliente: Dinero = Field(gt=Decimal("0"))

    @model_validator(mode="after")
    def _coherencia(self) -> "InmuebleIn":
        if self.tipo != "terreno" and self.m2_construccion <= 0:
            raise ValueError("m2Construccion debe ser mayor que 0 para casas y departamentos")
        return self

    model_config = SchemaBase.model_config | {
        "json_schema_extra": {
            "examples": [
                {
                    "tipo": "casa",
                    "direccion": "Calle Demo 45",
                    "colonia": "Del Valle",
                    "ciudad": "Ciudad de México",
                    "estado": "Ciudad de México",
                    "cp": "03100",
                    "m2Terreno": 160,
                    "m2Construccion": 140,
                    "antiguedadAnios": 8,
                    "recamaras": 3,
                    "banos": 2,
                    "valorEstimadoCliente": 2500000,
                }
            ]
        }
    }


class AvaluoOut(SchemaBase):
    """Avalúo del inmueble."""

    id: int
    folio: str | None
    inmueble_id: int
    solicitud_id: int | None = None
    valuador_id: int
    valuador_nombre: str | None = None
    estado: str
    fecha_solicitud: datetime
    fecha_visita: datetime | None
    valor_comercial: Dinero | None
    estado_conservacion: str | None
    observaciones: str | None
    generado_automaticamente: bool


class InmuebleOut(SchemaBase):
    """Inmueble registrado con su avalúo (si existe)."""

    id: int
    solicitud_id: int
    tipo: str
    direccion: str
    colonia: str
    ciudad: str
    estado: str
    cp: str
    m2_terreno: Dinero
    m2_construccion: Dinero
    antiguedad_anios: int
    recamaras: int
    banos: int
    valor_estimado_cliente: Dinero
    avaluo: AvaluoOut | None = None


class AvaluoResultadoIn(SchemaBase):
    """Ajuste manual del resultado del avalúo por el valuador."""

    valor_comercial: Dinero = Field(gt=Decimal("0"))
    estado_conservacion: Literal["excelente", "bueno", "regular", "malo"]
    observaciones: str = Field(min_length=5, max_length=1000)

    model_config = SchemaBase.model_config | {
        "json_schema_extra": {
            "examples": [
                {
                    "valorComercial": 2380000,
                    "estadoConservacion": "bueno",
                    "observaciones": "Visita realizada; acabados en buen estado, requiere impermeabilización.",
                }
            ]
        }
    }


class ResolucionIn(SchemaBase):
    """Sobrescritura de la resolución por el analista."""

    estado: Literal["aprobada", "condicionada", "rechazada"]
    monto: Dinero | None = Field(default=None, gt=Decimal("0"))
    tasa: Porcentaje | None = Field(default=None, ge=Decimal("0"), le=Decimal("100"))
    plazo: int | None = Field(default=None, gt=0, le=480)
    motivo: str = Field(min_length=5, max_length=1000)

    model_config = SchemaBase.model_config | {
        "json_schema_extra": {
            "examples": [
                {
                    "estado": "aprobada",
                    "monto": 1800000,
                    "tasa": 10.0,
                    "plazo": 240,
                    "motivo": "Revisión manual: ingresos adicionales comprobados.",
                },
                {"estado": "rechazada", "motivo": "Inconsistencias en la documentación."},
            ]
        }
    }
