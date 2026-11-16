"""Router del expediente: datos del solicitante y documentos simulados."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.responses import errores, ok
from app.dependencies.auth import get_usuario_actual, require_roles
from app.models.usuario import ROL_ANALISTA, ROL_CLIENTE, Usuario
from app.schemas.common import Respuesta
from app.schemas.expediente import (
    DocumentoEstadoOut,
    DocumentoIn,
    DocumentoOut,
    DocumentoRevisionIn,
    SolicitanteIn,
    SolicitanteOut,
)
from app.services import expediente as expediente_service

router = APIRouter(prefix="/solicitudes", tags=["Expediente"])
solo_cliente = require_roles(ROL_CLIENTE)
solo_analista = require_roles(ROL_ANALISTA)


def _mensaje(base: str, avanzo: bool) -> str:
    return base + (". La solicitud avanzó a datos_completos" if avanzo else "")


@router.put(
    "/{solicitud_id}/solicitante",
    response_model=Respuesta[SolicitanteOut],
    summary="Guardar datos del solicitante",
    description=(
        "Crea o reemplaza los datos personales, laborales y económicos. Reglas: mayor de 18 años, menor de "
        "70 al terminar el plazo, ingreso > 0 y mínimo 2 referencias. Solo en borrador o datos_completos."
    ),
    responses=errores(400, 401, 403, 404, 422),
)
def guardar_solicitante(
    solicitud_id: int, datos: SolicitanteIn, usuario: Usuario = Depends(solo_cliente), db: Session = Depends(get_db)
):
    """Captura del solicitante."""
    solicitante, _, avanzo = expediente_service.guardar_solicitante(db, solicitud_id, usuario, datos.model_dump())
    return ok(SolicitanteOut.model_validate(solicitante), _mensaje("Datos del solicitante guardados", avanzo))


@router.get(
    "/{solicitud_id}/solicitante",
    response_model=Respuesta[SolicitanteOut],
    summary="Consultar datos del solicitante",
    description="404 SOLICITANTE_NO_REGISTRADO si aún no se capturan.",
    responses=errores(401, 403, 404),
)
def obtener_solicitante(
    solicitud_id: int, usuario: Usuario = Depends(get_usuario_actual), db: Session = Depends(get_db)
):
    """Consulta del solicitante."""
    solicitante = expediente_service.obtener_solicitante(db, solicitud_id, usuario)
    return ok(SolicitanteOut.model_validate(solicitante), "Datos del solicitante")


@router.get(
    "/{solicitud_id}/documentos",
    response_model=Respuesta[list[DocumentoEstadoOut]],
    summary="Documentos requeridos y su estado",
    description="Lista todos los documentos requeridos con estado pendiente, entregado, validado o rechazado.",
    responses=errores(401, 403, 404),
)
def listar_documentos(
    solicitud_id: int, usuario: Usuario = Depends(get_usuario_actual), db: Session = Depends(get_db)
):
    """Estado de documentos."""
    docs = expediente_service.listar_documentos(db, solicitud_id, usuario)
    return ok([DocumentoEstadoOut.model_validate(d) for d in docs], "Documentos de la solicitud")


@router.post(
    "/{solicitud_id}/documentos",
    status_code=201,
    response_model=Respuesta[DocumentoOut],
    summary="Entregar documento simulado",
    description=(
        "Registra un documento SIMULADO (solo nombre de archivo, no se sube nada). 400 DOCUMENTO_NO_REQUERIDO "
        "si el tipo no aplica al producto; 409 DOCUMENTO_YA_ENTREGADO si ya existe y no está rechazado; si "
        "estaba rechazado se reemplaza."
    ),
    responses=errores(400, 401, 403, 404, 409, 422),
)
def entregar_documento(
    solicitud_id: int, datos: DocumentoIn, usuario: Usuario = Depends(solo_cliente), db: Session = Depends(get_db)
):
    """Entrega de documento."""
    documento, _, avanzo = expediente_service.entregar_documento(
        db, solicitud_id, usuario, datos.tipo, datos.nombre_archivo_simulado
    )
    return ok(DocumentoOut.model_validate(documento), _mensaje("Documento entregado", avanzo))


@router.patch(
    "/{solicitud_id}/documentos/{documento_id}",
    response_model=Respuesta[DocumentoOut],
    summary="Validar o rechazar documento",
    description="El analista marca el documento como validado o rechazado (observaciones obligatorias al rechazar).",
    responses=errores(400, 401, 403, 404, 422),
)
def revisar_documento(
    solicitud_id: int,
    documento_id: int,
    datos: DocumentoRevisionIn,
    _: Usuario = Depends(solo_analista),
    db: Session = Depends(get_db),
):
    """Revisión de documento."""
    documento = expediente_service.revisar_documento(db, solicitud_id, documento_id, datos.estado, datos.observaciones)
    return ok(DocumentoOut.model_validate(documento), f"Documento {documento.estado}")
