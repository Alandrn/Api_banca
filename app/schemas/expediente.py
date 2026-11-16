"""Esquemas del expediente: datos del solicitante y documentos simulados."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field, model_validator

from app.schemas.common import Dinero, SchemaBase
from app.schemas.productos import TipoDocumento
from app.schemas.usuarios import PATRON_NOMBRE, PATRON_TELEFONO


class Referencia(SchemaBase):
    """Referencia personal del solicitante."""

    nombre: str = Field(min_length=3, max_length=120, pattern=PATRON_NOMBRE)
    telefono: str = Field(pattern=PATRON_TELEFONO)
    relacion: str = Field(min_length=3, max_length=40)


class SolicitanteIn(SchemaBase):
    """Datos personales, laborales y económicos (reemplazo completo)."""

    fecha_nacimiento: date
    curp_ficticia: str = Field(
        pattern=r"^[A-Z0-9]{18}$", description="CURP FICTICIA de 18 caracteres alfanuméricos en mayúsculas"
    )
    estado_civil: Literal["soltero", "casado", "divorciado", "viudo", "union_libre"]
    dependientes: int = Field(default=0, ge=0, le=20)
    domicilio: str = Field(min_length=5, max_length=200)
    ciudad: str = Field(min_length=2, max_length=80)
    empresa: str = Field(min_length=2, max_length=120)
    puesto: str = Field(min_length=2, max_length=80)
    tipo_empleo: Literal["asalariado", "independiente"]
    antiguedad_meses: int = Field(ge=0, le=720)
    ingreso_mensual: Dinero = Field(gt=Decimal("0"))
    otros_ingresos: Dinero = Field(default=Decimal("0"), ge=Decimal("0"))
    gastos_mensuales: Dinero = Field(default=Decimal("0"), ge=Decimal("0"))
    deudas_mensuales: Dinero = Field(default=Decimal("0"), ge=Decimal("0"))
    referencias: list[Referencia] = Field(min_length=2, max_length=5)

    @model_validator(mode="after")
    def _telefonos_distintos(self) -> "SolicitanteIn":
        telefonos = [r.telefono for r in self.referencias]
        if len(set(telefonos)) != len(telefonos):
            raise ValueError("Las referencias deben tener teléfonos distintos")
        return self

    model_config = SchemaBase.model_config | {
        "json_schema_extra": {
            "examples": [
                {
                    "fechaNacimiento": "1990-04-15",
                    "curpFicticia": "DEMO900415HDFXXX01",
                    "estadoCivil": "casado",
                    "dependientes": 2,
                    "domicilio": "Av. Demo 123, Col. Centro",
                    "ciudad": "Ciudad de México",
                    "empresa": "Empresa Demo SA de CV",
                    "puesto": "Ingeniero de software",
                    "tipoEmpleo": "asalariado",
                    "antiguedadMeses": 48,
                    "ingresoMensual": 65000,
                    "otrosIngresos": 5000,
                    "gastosMensuales": 20000,
                    "deudasMensuales": 3000,
                    "referencias": [
                        {"nombre": "María Gómez", "telefono": "5511112222", "relacion": "hermana"},
                        {"nombre": "Pedro Ruiz", "telefono": "5533334444", "relacion": "amigo"},
                    ],
                }
            ]
        }
    }


class SolicitanteOut(SchemaBase):
    """Datos del solicitante guardados."""

    id: int
    solicitud_id: int
    fecha_nacimiento: date
    curp_ficticia: str
    estado_civil: str
    dependientes: int
    domicilio: str
    ciudad: str
    empresa: str
    puesto: str
    tipo_empleo: str
    antiguedad_meses: int
    ingreso_mensual: Dinero
    otros_ingresos: Dinero
    gastos_mensuales: Dinero
    deudas_mensuales: Dinero
    referencias: list[Referencia]


class DocumentoIn(SchemaBase):
    """Entrega de un documento simulado (no se sube ningún archivo real)."""

    tipo: TipoDocumento
    nombre_archivo_simulado: str = Field(
        min_length=5, max_length=150, pattern=r"^[\w\-. ]+\.(pdf|jpg|jpeg|png)$",
        description="Nombre de archivo simulado con extensión .pdf, .jpg, .jpeg o .png",
    )

    model_config = SchemaBase.model_config | {
        "json_schema_extra": {"examples": [{"tipo": "identificacion", "nombreArchivoSimulado": "ine_demo.pdf"}]}
    }


class DocumentoOut(SchemaBase):
    """Documento entregado."""

    id: int
    solicitud_id: int
    tipo: str
    nombre_archivo_simulado: str
    estado: str
    observaciones: str | None
    fecha: datetime


class DocumentoEstadoOut(SchemaBase):
    """Estado de un documento requerido (incluye los pendientes)."""

    tipo: str
    descripcion: str
    estado: str = Field(description="pendiente | entregado | validado | rechazado")
    documento_id: int | None = None
    nombre_archivo_simulado: str | None = None
    observaciones: str | None = None
    fecha: datetime | None = None


class DocumentoRevisionIn(SchemaBase):
    """Revisión de un documento por el analista."""

    estado: Literal["validado", "rechazado"]
    observaciones: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _observaciones_si_rechazo(self) -> "DocumentoRevisionIn":
        if self.estado == "rechazado" and not self.observaciones:
            raise ValueError("Las observaciones son obligatorias al rechazar un documento")
        return self

    model_config = SchemaBase.model_config | {
        "json_schema_extra": {
            "examples": [
                {"estado": "validado"},
                {"estado": "rechazado", "observaciones": "Documento ilegible, favor de entregarlo de nuevo"},
            ]
        }
    }
