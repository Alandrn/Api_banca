"""Router de solicitudes: alta, consulta, análisis, resolución, oferta y formalización."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.responses import errores, ok, paginado
from app.dependencies.auth import Paginacion, get_usuario_actual, paginacion, require_roles
from app.models.usuario import ROL_ANALISTA, ROL_CLIENTE, Usuario
from app.schemas.common import Respuesta, RespuestaPaginada
from app.schemas.evaluacion import ResolucionIn
from app.schemas.simuladores import AmortizacionOut
from app.schemas.solicitudes import (
    CancelarIn,
    HistorialOut,
    OfertaOut,
    SolicitudDetalleOut,
    SolicitudIn,
    SolicitudResumenOut,
)
from app.services import evaluacion as evaluacion_service
from app.services import solicitudes as solicitudes_service

router = APIRouter(prefix="/solicitudes", tags=["Solicitudes"])

solo_cliente = require_roles(ROL_CLIENTE)
cliente_o_analista = require_roles(ROL_CLIENTE, ROL_ANALISTA)
solo_analista = require_roles(ROL_ANALISTA)

EstadoFiltro = Literal[
    "borrador", "datos_completos", "en_avaluo", "avaluo_completado", "en_analisis", "aprobada",
    "condicionada", "rechazada", "oferta_aceptada", "oferta_rechazada", "formalizada", "cancelada",
]


def _detalle(solicitud) -> SolicitudDetalleOut:
    return SolicitudDetalleOut.model_validate(solicitudes_service.detalle(solicitud))


@router.post(
    "",
    status_code=201,
    response_model=Respuesta[SolicitudDetalleOut],
    summary="Crear solicitud",
    description=(
        "Crea una solicitud en estado `borrador`. Valida producto activo, monto y plazo del producto, "
        "máximo 3 solicitudes activas por cliente y, en hipotecas, `valorInmueble` obligatorio con "
        "enganche = valor − monto ≥ enganche mínimo del producto (400 ENGANCHE_INSUFICIENTE)."
    ),
    responses=errores(400, 401, 403, 404, 422),
)
def crear(datos: SolicitudIn, usuario: Usuario = Depends(solo_cliente), db: Session = Depends(get_db)):
    """Alta de solicitud."""
    solicitud = solicitudes_service.crear(db, usuario, datos.model_dump())
    return ok(_detalle(solicitud), f"Solicitud {solicitud.folio} creada")


@router.get(
    "",
    response_model=RespuestaPaginada[SolicitudResumenOut],
    summary="Listar solicitudes",
    description="Cliente: sus solicitudes. Analista/admin: todas. Filtros `estado` y `tipo`; paginado.",
    responses=errores(401, 403, 422),
)
def listar(
    estado: EstadoFiltro | None = Query(None, description="Filtrar por estado"),
    tipo: Literal["prestamo", "hipoteca"] | None = Query(None, description="Filtrar por tipo"),
    pag: Paginacion = Depends(paginacion),
    usuario: Usuario = Depends(cliente_o_analista),
    db: Session = Depends(get_db),
):
    """Listado de solicitudes."""
    filas, total = solicitudes_service.listar(
        db, usuario, estado=estado, tipo=tipo, offset=pag.offset, limit=pag.limit
    )
    return paginado([SolicitudResumenOut.model_validate(s) for s in filas], pag.page, pag.limit, total, "Solicitudes")


@router.get(
    "/{solicitud_id}",
    response_model=Respuesta[SolicitudDetalleOut],
    summary="Detalle de solicitud",
    description=(
        "Detalle completo con solicitante, inmueble, avalúo, documentos y `progreso` (qué falta para "
        "avanzar). Cliente: solo las suyas (403 ACCESO_DENEGADO). Valuador: solo con avalúo asignado."
    ),
    responses=errores(401, 403, 404),
)
def obtener(solicitud_id: int, usuario: Usuario = Depends(get_usuario_actual), db: Session = Depends(get_db)):
    """Detalle de solicitud."""
    return ok(SolicitudDetalleOut.model_validate(solicitudes_service.obtener_detalle(db, solicitud_id, usuario)),
              "Detalle de la solicitud")


@router.post(
    "/{solicitud_id}/cancelar",
    response_model=Respuesta[SolicitudDetalleOut],
    summary="Cancelar solicitud",
    description="Cancela una solicitud propia si su estado lo permite (no finales ni en análisis/oferta aceptada).",
    responses=errores(400, 401, 403, 404, 422),
)
def cancelar(
    solicitud_id: int,
    datos: CancelarIn | None = Body(default=None),
    usuario: Usuario = Depends(solo_cliente),
    db: Session = Depends(get_db),
):
    """Cancelación por el cliente."""
    solicitud = solicitudes_service.cancelar(db, solicitud_id, usuario, datos.motivo if datos else None)
    return ok(_detalle(solicitud), "Solicitud cancelada")


@router.get(
    "/{solicitud_id}/historial",
    response_model=Respuesta[list[HistorialOut]],
    summary="Historial de estados",
    description="Transiciones de estado con fecha, usuario y nota.",
    responses=errores(401, 403, 404),
)
def historial(solicitud_id: int, usuario: Usuario = Depends(get_usuario_actual), db: Session = Depends(get_db)):
    """Historial de la solicitud."""
    registros = solicitudes_service.historial(db, solicitud_id, usuario)
    return ok([HistorialOut.model_validate(r) for r in registros], "Historial de estados")


@router.post(
    "/{solicitud_id}/analisis",
    response_model=Respuesta[SolicitudDetalleOut],
    summary="Ejecutar análisis de crédito",
    description=(
        "Préstamo desde `datos_completos`; hipoteca desde `avaluo_completado`. Pasa a `en_analisis` y "
        "resuelve en la misma llamada (`aprobada`, `condicionada` o `rechazada`). El detalle de cada regla "
        "queda en `resultadoAnalisis`."
    ),
    responses=errores(400, 401, 403, 404),
)
def analisis(solicitud_id: int, usuario: Usuario = Depends(cliente_o_analista), db: Session = Depends(get_db)):
    """Análisis automático."""
    solicitud = evaluacion_service.ejecutar_analisis(db, solicitud_id, usuario)
    return ok(_detalle(solicitud), f"Análisis completado: solicitud {solicitud.estado}")


@router.patch(
    "/{solicitud_id}/resolucion",
    response_model=Respuesta[SolicitudDetalleOut],
    summary="Sobrescribir resolución",
    description=(
        "El analista reemplaza la resolución (estado, monto, tasa, plazo, motivo) mientras la solicitud esté "
        "en aprobada, condicionada o rechazada y antes de aceptar la oferta."
    ),
    responses=errores(400, 401, 403, 404, 422),
)
def resolucion(
    solicitud_id: int, datos: ResolucionIn, usuario: Usuario = Depends(solo_analista), db: Session = Depends(get_db)
):
    """Sobrescritura de la resolución."""
    solicitud = evaluacion_service.sobrescribir_resolucion(db, solicitud_id, usuario, datos.model_dump())
    return ok(_detalle(solicitud), "Resolución actualizada")


@router.get(
    "/{solicitud_id}/oferta",
    response_model=Respuesta[OfertaOut],
    summary="Consultar oferta",
    description=(
        "Monto, tasa, plazo, mensualidad, total a pagar, intereses, CAT demo y vigencia de 15 días. "
        "Leyenda: OFERTA DEMOSTRATIVA - NO ES UNA OFERTA REAL."
    ),
    responses=errores(400, 401, 403, 404),
)
def oferta(solicitud_id: int, usuario: Usuario = Depends(solo_cliente), db: Session = Depends(get_db)):
    """Oferta de la solicitud."""
    return ok(OfertaOut.model_validate(solicitudes_service.oferta(db, solicitud_id, usuario)), "Oferta demostrativa")


@router.post(
    "/{solicitud_id}/oferta/aceptar",
    response_model=Respuesta[SolicitudDetalleOut],
    summary="Aceptar oferta",
    description="Pasa a `oferta_aceptada` si la oferta está vigente (400 OFERTA_VENCIDA si no).",
    responses=errores(400, 401, 403, 404),
)
def aceptar(solicitud_id: int, usuario: Usuario = Depends(solo_cliente), db: Session = Depends(get_db)):
    """Aceptación de la oferta."""
    return ok(_detalle(solicitudes_service.aceptar_oferta(db, solicitud_id, usuario)), "Oferta aceptada")


@router.post(
    "/{solicitud_id}/oferta/rechazar",
    response_model=Respuesta[SolicitudDetalleOut],
    summary="Rechazar oferta",
    description="Pasa a `oferta_rechazada` (estado final). Motivo opcional.",
    responses=errores(400, 401, 403, 404, 422),
)
def rechazar(
    solicitud_id: int,
    datos: CancelarIn | None = Body(default=None),
    usuario: Usuario = Depends(solo_cliente),
    db: Session = Depends(get_db),
):
    """Rechazo de la oferta."""
    solicitud = solicitudes_service.rechazar_oferta(db, solicitud_id, usuario, datos.motivo if datos else None)
    return ok(_detalle(solicitud), "Oferta rechazada")


@router.post(
    "/{solicitud_id}/formalizar",
    response_model=Respuesta[SolicitudDetalleOut],
    summary="Formalizar crédito",
    description=(
        "Pasa de `oferta_aceptada` a `formalizada` y fija `formalizadaEn`. En préstamos se deposita el monto "
        "en la cuenta demo del cliente. Habilita la tabla de amortización."
    ),
    responses=errores(400, 401, 403, 404),
)
def formalizar(solicitud_id: int, usuario: Usuario = Depends(solo_cliente), db: Session = Depends(get_db)):
    """Formalización."""
    return ok(_detalle(solicitudes_service.formalizar(db, solicitud_id, usuario)), "Crédito formalizado")


@router.get(
    "/{solicitud_id}/amortizacion",
    response_model=Respuesta[AmortizacionOut],
    summary="Tabla de amortización del crédito",
    description="Solo para créditos formalizados (400 CREDITO_NO_FORMALIZADO). Incluye fecha de cada pago.",
    responses=errores(400, 401, 403, 404),
)
def amortizacion(solicitud_id: int, usuario: Usuario = Depends(solo_cliente), db: Session = Depends(get_db)):
    """Tabla de amortización."""
    return ok(AmortizacionOut.model_validate(solicitudes_service.amortizacion(db, solicitud_id, usuario)),
              "Tabla de amortización del crédito")
