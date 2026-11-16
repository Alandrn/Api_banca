"""Router de evaluación del inmueble: inmueble y avalúos."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.responses import errores, ok, paginado
from app.dependencies.auth import Paginacion, get_usuario_actual, paginacion, require_roles
from app.models.usuario import ROL_ANALISTA, ROL_CLIENTE, ROL_VALUADOR, Usuario
from app.schemas.common import Respuesta, RespuestaPaginada
from app.schemas.evaluacion import AvaluoOut, AvaluoResultadoIn, InmuebleIn, InmuebleOut
from app.services import evaluacion as evaluacion_service

router = APIRouter(tags=["Evaluación del inmueble"])
solo_cliente = require_roles(ROL_CLIENTE)
cliente_o_analista = require_roles(ROL_CLIENTE, ROL_ANALISTA)
valuador_o_analista = require_roles(ROL_VALUADOR, ROL_ANALISTA)
solo_valuador = require_roles(ROL_VALUADOR)


@router.put(
    "/solicitudes/{solicitud_id}/inmueble",
    response_model=Respuesta[InmuebleOut],
    summary="Registrar inmueble",
    description="Crea o reemplaza el inmueble de una hipoteca (400 SOLO_HIPOTECA en préstamos). Solo en borrador o datos_completos.",
    responses=errores(400, 401, 403, 404, 422),
)
def guardar_inmueble(
    solicitud_id: int, datos: InmuebleIn, usuario: Usuario = Depends(solo_cliente), db: Session = Depends(get_db)
):
    """Registro del inmueble."""
    inmueble, _, avanzo = evaluacion_service.guardar_inmueble(db, solicitud_id, usuario, datos.model_dump())
    mensaje = "Inmueble registrado" + (". La solicitud avanzó a datos_completos" if avanzo else "")
    return ok(InmuebleOut.model_validate(inmueble), mensaje)


@router.get(
    "/solicitudes/{solicitud_id}/inmueble",
    response_model=Respuesta[InmuebleOut],
    summary="Consultar inmueble",
    description="Inmueble con su avalúo (si existe). 404 INMUEBLE_NO_REGISTRADO si aún no se registra.",
    responses=errores(400, 401, 403, 404),
)
def obtener_inmueble(solicitud_id: int, usuario: Usuario = Depends(get_usuario_actual), db: Session = Depends(get_db)):
    """Consulta del inmueble."""
    return ok(InmuebleOut.model_validate(evaluacion_service.obtener_inmueble(db, solicitud_id, usuario)), "Inmueble")


@router.post(
    "/solicitudes/{solicitud_id}/avaluo",
    status_code=201,
    response_model=Respuesta[AvaluoOut],
    summary="Solicitar avalúo",
    description=(
        "Solo hipotecas en `datos_completos`. Asigna un valuador al azar y genera el resultado automático "
        "en la misma llamada: valor comercial = valor estimado × factor reproducible [0.85, 1.05] y "
        "conservación según antigüedad. La solicitud queda en `avaluo_completado`."
    ),
    responses=errores(400, 401, 403, 404),
)
def solicitar_avaluo(solicitud_id: int, usuario: Usuario = Depends(cliente_o_analista), db: Session = Depends(get_db)):
    """Solicitud de avalúo."""
    avaluo = evaluacion_service.solicitar_avaluo(db, solicitud_id, usuario)
    return ok(AvaluoOut.model_validate(avaluo), f"Avalúo {avaluo.folio} completado")


@router.get(
    "/avaluos",
    response_model=RespuestaPaginada[AvaluoOut],
    summary="Listar avalúos",
    description="Valuador: los asignados. Analista/admin: todos. Filtro por estado; paginado.",
    responses=errores(401, 403, 422),
)
def listar_avaluos(
    estado: Literal["solicitado", "completado"] | None = Query(None, description="Filtrar por estado"),
    pag: Paginacion = Depends(paginacion),
    usuario: Usuario = Depends(valuador_o_analista),
    db: Session = Depends(get_db),
):
    """Listado de avalúos."""
    filas, total = evaluacion_service.listar_avaluos(db, usuario, estado=estado, offset=pag.offset, limit=pag.limit)
    return paginado([AvaluoOut.model_validate(a) for a in filas], pag.page, pag.limit, total, "Avalúos")


@router.get(
    "/avaluos/{avaluo_id}",
    response_model=Respuesta[AvaluoOut],
    summary="Detalle de avalúo",
    description="Visible para el valuador asignado, el cliente dueño, analistas y admin.",
    responses=errores(401, 403, 404),
)
def obtener_avaluo(avaluo_id: int, usuario: Usuario = Depends(get_usuario_actual), db: Session = Depends(get_db)):
    """Detalle de avalúo."""
    return ok(AvaluoOut.model_validate(evaluacion_service.obtener_avaluo(db, avaluo_id, usuario)), "Avalúo")


@router.patch(
    "/avaluos/{avaluo_id}/resultado",
    response_model=Respuesta[AvaluoOut],
    summary="Ajustar resultado del avalúo",
    description=(
        "El valuador asignado ajusta valor comercial, conservación y observaciones mientras la solicitud no "
        "haya pasado a `en_analisis` (400 AVALUO_NO_EDITABLE)."
    ),
    responses=errores(400, 401, 403, 404, 422),
)
def ajustar_avaluo(
    avaluo_id: int, datos: AvaluoResultadoIn, usuario: Usuario = Depends(solo_valuador), db: Session = Depends(get_db)
):
    """Ajuste del avalúo."""
    avaluo = evaluacion_service.ajustar_avaluo(db, avaluo_id, usuario, datos.model_dump())
    return ok(AvaluoOut.model_validate(avaluo), "Resultado del avalúo actualizado")
