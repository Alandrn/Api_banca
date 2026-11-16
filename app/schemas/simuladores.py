"""Esquemas de los simuladores públicos."""

from __future__ import annotations

from decimal import Decimal

from pydantic import Field, model_validator

from app.schemas.common import DecimalSalida, Dinero, Porcentaje, SchemaBase

LEYENDA_SIMULACION = "SIMULACIÓN DEMOSTRATIVA - NO ES UNA OFERTA REAL"


class _TasaOProducto(SchemaBase):
    """Base: la tasa se indica directamente o se toma del producto."""

    tasa_anual: Porcentaje | None = Field(default=None, ge=Decimal("0"), le=Decimal("100"))
    producto_id: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def _tasa_o_producto(self):
        if self.tasa_anual is None and self.producto_id is None:
            raise ValueError("Debe indicar tasaAnual o productoId")
        return self


class SimuladorPrestamoIn(_TasaOProducto):
    """Simulación de préstamo personal."""

    monto: Dinero = Field(gt=Decimal("0"))
    plazo_meses: int = Field(gt=0, le=480)

    model_config = SchemaBase.model_config | {
        "json_schema_extra": {
            "examples": [
                {"monto": 50000, "tasaAnual": 18.5, "plazoMeses": 24},
                {"monto": 80000, "productoId": 2, "plazoMeses": 36},
            ]
        }
    }


class SimuladorPrestamoOut(SchemaBase):
    """Resultado de simulación de préstamo."""

    monto: DecimalSalida
    tasa_anual: DecimalSalida
    plazo_meses: int
    mensualidad: DecimalSalida
    total_intereses: DecimalSalida
    total_pagar: DecimalSalida
    cat_demo: DecimalSalida
    producto_id: int | None = None
    producto_nombre: str | None = None
    leyenda: str = LEYENDA_SIMULACION


class SimuladorHipotecaIn(_TasaOProducto):
    """Simulación de hipoteca. El monto del crédito = valor del inmueble − enganche."""

    valor_inmueble: Dinero = Field(gt=Decimal("0"))
    enganche: Dinero = Field(ge=Decimal("0"))
    plazo_meses: int = Field(gt=0, le=480)
    enganche_min_pct: Porcentaje | None = Field(
        default=None, ge=Decimal("0"), le=Decimal("90"),
        description="Si no se indica, se toma del producto o 10% por defecto",
    )

    @model_validator(mode="after")
    def _enganche_menor(self):
        if self.enganche >= self.valor_inmueble:
            raise ValueError("El enganche debe ser menor que el valor del inmueble")
        return self

    model_config = SchemaBase.model_config | {
        "json_schema_extra": {
            "examples": [
                {"valorInmueble": 2500000, "enganche": 500000, "tasaAnual": 10.5, "plazoMeses": 240},
                {"valorInmueble": 2500000, "enganche": 500000, "productoId": 4, "plazoMeses": 240},
            ]
        }
    }


class SimuladorHipotecaOut(SimuladorPrestamoOut):
    """Resultado de simulación de hipoteca."""

    valor_inmueble: DecimalSalida
    enganche: DecimalSalida
    enganche_pct: DecimalSalida
    enganche_min_pct: DecimalSalida
    enganche_minimo: DecimalSalida
    cumple_enganche_minimo: bool
    mensaje_enganche: str


class AmortizacionIn(SchemaBase):
    """Parámetros de la tabla de amortización."""

    monto: Dinero = Field(gt=Decimal("0"))
    tasa_anual: Porcentaje = Field(ge=Decimal("0"), le=Decimal("100"))
    plazo_meses: int = Field(gt=0, le=480)

    model_config = SchemaBase.model_config | {
        "json_schema_extra": {"examples": [{"monto": 50000, "tasaAnual": 18.5, "plazoMeses": 12}]}
    }


class FilaAmortizacionOut(SchemaBase):
    """Fila de la tabla de amortización."""

    numero: int
    pago: DecimalSalida
    capital: DecimalSalida
    interes: DecimalSalida
    saldo: DecimalSalida
    fecha_pago: str | None = None


class AmortizacionOut(SchemaBase):
    """Tabla de amortización con su resumen."""

    monto: DecimalSalida
    tasa_anual: DecimalSalida
    plazo_meses: int
    mensualidad: DecimalSalida
    total_intereses: DecimalSalida
    total_pagar: DecimalSalida
    tabla: list[FilaAmortizacionOut]
    leyenda: str = LEYENDA_SIMULACION
