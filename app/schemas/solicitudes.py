"""Esquemas de solicitudes de crédito, historial y oferta."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import Field

from app.schemas.common import DecimalSalida, Dinero, Porcentaje, SchemaBase
from app.schemas.evaluacion import InmuebleOut
from app.schemas.expediente import DocumentoEstadoOut, SolicitanteOut


class SolicitudIn(SchemaBase):
    """Creación de una solicitud. ``valorInmueble`` es obligatorio para hipoteca."""

    producto_id: int = Field(gt=0)
    monto_solicitado: Dinero = Field(gt=Decimal("0"))
    plazo_meses: int = Field(gt=0, le=480)
    valor_inmueble: Dinero | None = Field(default=None, gt=Decimal("0"))

    model_config = SchemaBase.model_config | {
        "json_schema_extra": {
            "examples": [
                {"productoId": 4, "montoSolicitado": 2000000, "plazoMeses": 240, "valorInmueble": 2500000},
                {"productoId": 2, "montoSolicitado": 80000, "plazoMeses": 24},
            ]
        }
    }


class ProductoResumenOut(SchemaBase):
    """Resumen del producto dentro de una solicitud."""

    id: int
    nombre: str
    tipo: str
    tasa_anual: Porcentaje


class SolicitudResumenOut(SchemaBase):
    """Solicitud en listados."""

    id: int
    folio: str | None
    usuario_id: int
    producto: ProductoResumenOut
    tipo: str
    monto_solicitado: Dinero
    plazo_meses: int
    valor_inmueble: Dinero | None
    enganche: Dinero | None
    estado: str
    monto_aprobado: Dinero | None
    tasa_aprobada: Porcentaje | None
    plazo_aprobado: int | None
    mensualidad_aprobada: Dinero | None
    creada_en: datetime
    actualizada_en: datetime


class ProgresoOut(SchemaBase):
    """Qué le falta a la solicitud para avanzar."""

    porcentaje: int
    solicitante_completo: bool
    documentos_requeridos: list[str]
    documentos_entregados: list[str]
    documentos_pendientes: list[str]
    documentos_rechazados: list[str]
    inmueble_requerido: bool
    inmueble_registrado: bool
    avaluo_requerido: bool
    avaluo_estado: str | None
    editable: bool
    siguiente_paso: str


class SolicitudDetalleOut(SolicitudResumenOut):
    """Detalle completo de una solicitud."""

    puntaje_buro: int | None
    resultado_analisis: dict[str, Any] | None
    enganche_requerido: Dinero | None
    motivo_resolucion: str | None
    resuelta_en: datetime | None
    formalizada_en: datetime | None
    solicitante: SolicitanteOut | None
    inmueble: InmuebleOut | None
    documentos: list[DocumentoEstadoOut]
    progreso: ProgresoOut


class CancelarIn(SchemaBase):
    """Motivo opcional de cancelación."""

    motivo: str | None = Field(default=None, max_length=500)

    model_config = SchemaBase.model_config | {
        "json_schema_extra": {"examples": [{"motivo": "Ya no necesito el crédito"}]}
    }


class HistorialOut(SchemaBase):
    """Registro del historial de estados."""

    id: int
    estado_anterior: str | None
    estado_nuevo: str
    usuario_id: int | None
    nota: str | None
    fecha: datetime


class OfertaOut(SchemaBase):
    """Oferta demostrativa derivada de la resolución."""

    solicitud_id: int
    folio: str | None
    estado: str
    producto: str
    monto: DecimalSalida
    tasa_anual: DecimalSalida
    plazo_meses: int
    mensualidad: DecimalSalida
    total_pagar: DecimalSalida
    total_intereses: DecimalSalida
    cat_demo: DecimalSalida
    enganche_requerido: DecimalSalida | None
    condicionada: bool
    condiciones: str | None
    fecha_emision: datetime
    vigente_hasta: datetime
    vigente: bool
    leyenda: str = "OFERTA DEMOSTRATIVA - NO ES UNA OFERTA REAL"
