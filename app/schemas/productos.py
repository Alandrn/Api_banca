"""Esquemas de productos de crédito."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import Field, model_validator

from app.models.producto import DOCUMENTOS_SOLO_HIPOTECA, TIPOS_DOCUMENTO
from app.schemas.common import Dinero, Porcentaje, SchemaBase

TipoDocumento = Literal[
    "identificacion", "comprobante_domicilio", "comprobante_ingresos", "estados_cuenta", "escrituras", "predial"
]


class ProductoOut(SchemaBase):
    """Producto de crédito."""

    id: int
    nombre: str
    tipo: str
    descripcion: str
    tasa_anual: Porcentaje
    monto_min: Dinero
    monto_max: Dinero
    plazos_meses: list[int]
    enganche_min_pct: Porcentaje | None
    documentos_requeridos: list[str]
    requisitos: list[str]
    condiciones: str
    activo: bool

    model_config = SchemaBase.model_config | {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 4,
                    "nombre": "Hipoteca Fija Demo",
                    "tipo": "hipoteca",
                    "descripcion": "Crédito hipotecario demostrativo a tasa fija.",
                    "tasaAnual": 10.5,
                    "montoMin": 500000.0,
                    "montoMax": 5000000.0,
                    "plazosMeses": [120, 180, 240],
                    "engancheMinPct": 10.0,
                    "documentosRequeridos": ["identificacion", "comprobante_domicilio", "comprobante_ingresos",
                                             "estados_cuenta", "escrituras", "predial"],
                    "requisitos": ["Ser mayor de edad", "Enganche mínimo del 10%"],
                    "condiciones": "Tasa fija durante todo el plazo. Producto demostrativo.",
                    "activo": True,
                }
            ]
        }
    }


class ProductoIn(SchemaBase):
    """Alta o reemplazo completo de un producto (admin)."""

    nombre: str = Field(min_length=3, max_length=120)
    tipo: Literal["prestamo", "hipoteca"]
    descripcion: str = Field(min_length=5, max_length=2000)
    tasa_anual: Porcentaje = Field(ge=Decimal("0"), le=Decimal("100"))
    monto_min: Dinero = Field(gt=Decimal("0"))
    monto_max: Dinero = Field(gt=Decimal("0"))
    plazos_meses: list[int] = Field(min_length=1, max_length=20)
    enganche_min_pct: Porcentaje | None = Field(default=None, ge=Decimal("0"), le=Decimal("90"))
    documentos_requeridos: list[TipoDocumento] = Field(min_length=1)
    requisitos: list[str] = Field(default_factory=list, max_length=30)
    condiciones: str = Field(min_length=5, max_length=4000)
    activo: bool = True

    @model_validator(mode="after")
    def _validar_coherencia(self) -> "ProductoIn":
        if self.monto_min >= self.monto_max:
            raise ValueError("montoMin debe ser menor que montoMax")
        if any(p <= 0 or p > 480 for p in self.plazos_meses):
            raise ValueError("Cada plazo debe estar entre 1 y 480 meses")
        if len(set(self.plazos_meses)) != len(self.plazos_meses):
            raise ValueError("plazosMeses no debe tener valores repetidos")
        if len(set(self.documentos_requeridos)) != len(self.documentos_requeridos):
            raise ValueError("documentosRequeridos no debe tener valores repetidos")
        if self.tipo == "hipoteca":
            if self.enganche_min_pct is None:
                raise ValueError("engancheMinPct es obligatorio para productos de hipoteca")
        else:
            if self.enganche_min_pct is not None:
                raise ValueError("engancheMinPct solo aplica a productos de hipoteca")
            invalidos = [d for d in self.documentos_requeridos if d in DOCUMENTOS_SOLO_HIPOTECA]
            if invalidos:
                raise ValueError(f"Los documentos {invalidos} solo aplican a hipotecas")
        self.plazos_meses = sorted(self.plazos_meses)
        return self

    model_config = SchemaBase.model_config | {
        "json_schema_extra": {
            "examples": [
                {
                    "nombre": "Préstamo Auto Demo",
                    "tipo": "prestamo",
                    "descripcion": "Préstamo demostrativo para compra de auto.",
                    "tasaAnual": 16.9,
                    "montoMin": 30000,
                    "montoMax": 400000,
                    "plazosMeses": [12, 24, 36, 48],
                    "engancheMinPct": None,
                    "documentosRequeridos": ["identificacion", "comprobante_domicilio", "comprobante_ingresos"],
                    "requisitos": ["Ser mayor de edad", "Ingreso mínimo demostrable"],
                    "condiciones": "Tasa fija. Producto demostrativo sin validez comercial.",
                    "activo": True,
                }
            ]
        }
    }


class DocumentoRequisitoOut(SchemaBase):
    """Documento requerido por un producto."""

    tipo: str
    descripcion: str


class RequisitosOut(SchemaBase):
    """Requisitos legibles y documentos de un producto."""

    producto_id: int
    nombre: str
    tipo: str
    requisitos: list[str]
    documentos_requeridos: list[DocumentoRequisitoOut]
    enganche_min_pct: Porcentaje | None
    monto_min: Dinero
    monto_max: Dinero
    plazos_meses: list[int]
    condiciones: str


__all__ = ["ProductoIn", "ProductoOut", "RequisitosOut", "DocumentoRequisitoOut", "TIPOS_DOCUMENTO"]
