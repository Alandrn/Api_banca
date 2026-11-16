"""Servicio de evaluación: inmueble, avalúo, análisis de crédito y resolución."""

from __future__ import annotations

import random
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ApiError
from app.models.avaluo import Avaluo
from app.models.inmueble import Inmueble
from app.models.solicitud import Solicitud
from app.models.usuario import ROL_ADMIN, ROL_ANALISTA, ROL_CLIENTE, ROL_VALUADOR, Usuario
from app.services.comun import (
    cambiar_estado,
    obtener_o_404,
    obtener_solicitud,
    solicitud_con_acceso,
    solicitud_propia,
    solicitud_propia_o_personal,
    validar_editable,
)
from app.services.progreso import documentos_rechazados, intentar_completar
from app.services.simuladores import validar_monto_plazo
from app.utils import estados as E
from app.utils.analisis import DatosAnalisis, calcular_puntaje_buro, evaluar
from app.utils.fechas import ahora, hoy
from app.utils.finanzas import calcular_mensualidad, redondear
from app.utils.identificadores import folio_avaluo


# ---------------------------------------------------------------------------
# Inmueble
# ---------------------------------------------------------------------------

def _solo_hipoteca(solicitud: Solicitud) -> None:
    if solicitud.tipo != "hipoteca":
        raise ApiError(400, "SOLO_HIPOTECA", "Esta operación solo aplica a solicitudes de hipoteca")


def guardar_inmueble(
    db: Session, solicitud_id: int, usuario: Usuario, datos: dict[str, Any]
) -> tuple[Inmueble, Solicitud, bool]:
    """Crea o reemplaza el inmueble de una hipoteca."""
    solicitud = solicitud_propia(db, solicitud_id, usuario)
    _solo_hipoteca(solicitud)
    validar_editable(solicitud)
    inmueble = solicitud.inmueble
    if inmueble is None:
        inmueble = Inmueble(solicitud_id=solicitud.id, **datos)
        db.add(inmueble)
        solicitud.inmueble = inmueble
    else:
        for campo, valor in datos.items():
            setattr(inmueble, campo, valor)
    solicitud.actualizada_en = ahora()
    db.flush()
    avanzo = intentar_completar(db, solicitud, usuario.id)
    db.commit()
    db.refresh(inmueble)
    return inmueble, solicitud, avanzo


def obtener_inmueble(db: Session, solicitud_id: int, usuario: Usuario) -> Inmueble:
    """Inmueble de la solicitud (404 si no se ha registrado)."""
    solicitud = solicitud_con_acceso(db, solicitud_id, usuario)
    _solo_hipoteca(solicitud)
    if solicitud.inmueble is None:
        raise ApiError(404, "INMUEBLE_NO_REGISTRADO", "La solicitud aún no tiene inmueble registrado")
    return solicitud.inmueble


# ---------------------------------------------------------------------------
# Avalúo
# ---------------------------------------------------------------------------

def conservacion_por_antiguedad(anios: int) -> str:
    """≤5 excelente, ≤15 bueno, ≤30 regular, >30 malo."""
    if anios <= 5:
        return "excelente"
    if anios <= 15:
        return "bueno"
    if anios <= 30:
        return "regular"
    return "malo"


def factor_avaluo(semilla: int) -> Decimal:
    """Factor reproducible entre AVALUO_FACTOR_MIN y AVALUO_FACTOR_MAX (4 decimales)."""
    rng = random.Random(semilla)
    minimo = float(settings.AVALUO_FACTOR_MIN)
    maximo = float(settings.AVALUO_FACTOR_MAX)
    return Decimal(str(round(rng.uniform(minimo, maximo), 4)))


def _observaciones_auto(inmueble: Inmueble, conservacion: str, factor: Decimal) -> str:
    diferencia = (factor - 1) * 100
    tendencia = "por encima" if diferencia > 0 else "por debajo" if diferencia < 0 else "igual"
    return (
        f"Avalúo DEMO generado automáticamente. Inmueble tipo {inmueble.tipo} de {inmueble.antiguedad_anios} "
        f"años en {inmueble.colonia}, {inmueble.ciudad}; estado de conservación {conservacion}. "
        f"Valor comercial {abs(diferencia):.2f}% {tendencia} del valor estimado por el cliente."
    )


def solicitar_avaluo(db: Session, solicitud_id: int, usuario: Usuario) -> Avaluo:
    """Asigna un valuador, genera el avalúo automático y deja la solicitud en avaluo_completado."""
    solicitud = solicitud_propia_o_personal(db, solicitud_id, usuario)
    _solo_hipoteca(solicitud)
    E.validar_transicion(solicitud.estado, E.EN_AVALUO, solicitud.tipo)
    rechazados = documentos_rechazados(solicitud)
    if rechazados:
        raise ApiError(
            400, "DOCUMENTOS_RECHAZADOS", "Hay documentos rechazados; vuelva a entregarlos antes de continuar",
            [{"documentosRechazados": rechazados}],
        )
    inmueble = solicitud.inmueble
    if inmueble is None:
        raise ApiError(400, "INMUEBLE_NO_REGISTRADO", "La solicitud no tiene inmueble registrado")
    valuadores = list(
        db.scalars(select(Usuario).where(Usuario.rol == ROL_VALUADOR, Usuario.activo.is_(True)).order_by(Usuario.id))
    )
    if not valuadores:
        raise ApiError(400, "SIN_VALUADORES", "No hay valuadores activos disponibles")
    valuador = random.Random(solicitud.id * 7919).choice(valuadores)

    fecha = ahora()
    avaluo = Avaluo(
        inmueble_id=inmueble.id, valuador_id=valuador.id, estado="solicitado",
        fecha_solicitud=fecha, generado_automaticamente=True,
    )
    db.add(avaluo)
    db.flush()
    avaluo.folio = folio_avaluo(avaluo.id, fecha.year)
    inmueble.avaluo = avaluo
    cambiar_estado(db, solicitud, E.EN_AVALUO, usuario.id, f"Avalúo {avaluo.folio} asignado a {valuador.codigo}")

    # Resultado automático (reproducible por id de solicitud)
    factor = factor_avaluo(solicitud.id)
    conservacion = conservacion_por_antiguedad(inmueble.antiguedad_anios)
    avaluo.valor_comercial = redondear(inmueble.valor_estimado_cliente * factor)
    avaluo.estado_conservacion = conservacion
    avaluo.observaciones = _observaciones_auto(inmueble, conservacion, factor)
    avaluo.fecha_visita = fecha
    avaluo.estado = "completado"
    cambiar_estado(
        db, solicitud, E.AVALUO_COMPLETADO, valuador.id,
        f"Avalúo completado automáticamente: valor comercial {avaluo.valor_comercial}",
    )
    db.commit()
    db.refresh(avaluo)
    return avaluo


def listar_avaluos(
    db: Session, usuario: Usuario, *, estado: str | None, offset: int, limit: int
) -> tuple[list[Avaluo], int]:
    """Valuador: los asignados. Analista/admin: todos."""
    consulta = select(Avaluo)
    if usuario.rol == ROL_VALUADOR:
        consulta = consulta.where(Avaluo.valuador_id == usuario.id)
    if estado:
        consulta = consulta.where(Avaluo.estado == estado)
    total = db.scalar(select(func.count()).select_from(consulta.subquery())) or 0
    filas = list(db.scalars(consulta.order_by(Avaluo.id.desc()).offset(offset).limit(limit)))
    return filas, total


def obtener_avaluo(db: Session, avaluo_id: int, usuario: Usuario) -> Avaluo:
    """Avalúo visible para el usuario (valuador asignado, cliente dueño, analista o admin)."""
    avaluo = obtener_o_404(db, Avaluo, avaluo_id, "El avalúo", "AVALUO_NO_ENCONTRADO")
    if usuario.rol in (ROL_ANALISTA, ROL_ADMIN):
        return avaluo
    if usuario.rol == ROL_VALUADOR and avaluo.valuador_id == usuario.id:
        return avaluo
    if usuario.rol == ROL_CLIENTE and avaluo.inmueble.solicitud.usuario_id == usuario.id:
        return avaluo
    raise ApiError(403, "ACCESO_DENEGADO", "No tiene permiso para ver este avalúo")


def ajustar_avaluo(db: Session, avaluo_id: int, usuario: Usuario, datos: dict[str, Any]) -> Avaluo:
    """El valuador asignado ajusta el resultado antes de que la solicitud pase a análisis."""
    avaluo = obtener_o_404(db, Avaluo, avaluo_id, "El avalúo", "AVALUO_NO_ENCONTRADO")
    if usuario.rol != ROL_ADMIN and avaluo.valuador_id != usuario.id:
        raise ApiError(403, "ACCESO_DENEGADO", "El avalúo no está asignado a este valuador")
    solicitud = avaluo.inmueble.solicitud
    if solicitud.estado not in (E.EN_AVALUO, E.AVALUO_COMPLETADO):
        raise ApiError(
            400, "AVALUO_NO_EDITABLE",
            f"El avalúo ya no puede ajustarse: la solicitud está en '{solicitud.estado}'",
        )
    anterior = avaluo.valor_comercial
    avaluo.valor_comercial = datos["valor_comercial"]
    avaluo.estado_conservacion = datos["estado_conservacion"]
    avaluo.observaciones = datos["observaciones"]
    avaluo.fecha_visita = ahora()
    avaluo.estado = "completado"
    avaluo.generado_automaticamente = False
    nota = f"Avalúo ajustado por el valuador: {anterior} → {avaluo.valor_comercial}"
    if solicitud.estado == E.EN_AVALUO:
        cambiar_estado(db, solicitud, E.AVALUO_COMPLETADO, usuario.id, nota)
    else:
        solicitud.actualizada_en = ahora()
    db.commit()
    db.refresh(avaluo)
    return avaluo


# ---------------------------------------------------------------------------
# Análisis y resolución
# ---------------------------------------------------------------------------

def ejecutar_analisis(
    db: Session, solicitud_id: int, usuario: Usuario, puntaje_buro: int | None = None
) -> Solicitud:
    """Pasa la solicitud a ``en_analisis`` y la resuelve en la misma llamada.

    ``puntaje_buro`` permite fijar el puntaje (uso interno del seed); si es None se
    calcula de forma reproducible a partir del folio.
    """
    solicitud = solicitud_propia_o_personal(db, solicitud_id, usuario)
    E.validar_transicion(solicitud.estado, E.EN_ANALISIS, solicitud.tipo)
    rechazados = documentos_rechazados(solicitud)
    if rechazados:
        raise ApiError(
            400, "DOCUMENTOS_RECHAZADOS", "Hay documentos rechazados; vuelva a entregarlos antes de continuar",
            [{"documentosRechazados": rechazados}],
        )
    s = solicitud.solicitante
    if s is None:
        raise ApiError(400, "SOLICITANTE_NO_REGISTRADO", "La solicitud no tiene datos del solicitante")
    valor_comercial = None
    if solicitud.tipo == "hipoteca":
        avaluo = solicitud.inmueble.avaluo if solicitud.inmueble else None
        if avaluo is None or avaluo.valor_comercial is None:
            raise ApiError(400, "AVALUO_PENDIENTE", "La hipoteca requiere un avalúo completado")
        valor_comercial = avaluo.valor_comercial

    cambiar_estado(db, solicitud, E.EN_ANALISIS, usuario.id, "Análisis de crédito iniciado")
    puntaje = puntaje_buro if puntaje_buro is not None else calcular_puntaje_buro(solicitud.folio or "")
    resultado = evaluar(
        DatosAnalisis(
            tipo=solicitud.tipo,
            monto=solicitud.monto_solicitado,
            plazo_meses=solicitud.plazo_meses,
            tasa_anual=solicitud.producto.tasa_anual,
            monto_min_producto=solicitud.producto.monto_min,
            ingreso_mensual=s.ingreso_mensual,
            otros_ingresos=s.otros_ingresos,
            deudas_mensuales=s.deudas_mensuales,
            antiguedad_meses=s.antiguedad_meses,
            fecha_nacimiento=s.fecha_nacimiento,
            fecha_analisis=hoy(),
            puntaje_buro=puntaje,
            valor_inmueble=solicitud.valor_inmueble,
            valor_comercial=valor_comercial,
        )
    )
    solicitud.puntaje_buro = puntaje
    solicitud.resultado_analisis = resultado.a_json()
    solicitud.monto_aprobado = resultado.monto_aprobado
    solicitud.tasa_aprobada = resultado.tasa_aprobada
    solicitud.plazo_aprobado = resultado.plazo_aprobado
    solicitud.mensualidad_aprobada = resultado.mensualidad_aprobada
    solicitud.enganche_requerido = resultado.enganche_requerido
    solicitud.motivo_resolucion = resultado.motivo
    solicitud.resuelta_en = ahora()
    cambiar_estado(db, solicitud, resultado.resolucion, usuario.id, resultado.motivo)
    db.commit()
    db.refresh(solicitud)
    return solicitud


def sobrescribir_resolucion(db: Session, solicitud_id: int, analista: Usuario, datos: dict[str, Any]) -> Solicitud:
    """El analista reemplaza la resolución automática (antes de que se acepte la oferta)."""
    solicitud = obtener_solicitud(db, solicitud_id)
    if solicitud.estado not in E.ESTADOS_RESUELTOS:
        raise ApiError(
            400, "RESOLUCION_NO_EDITABLE",
            f"Solo se puede sobrescribir la resolución en estados {sorted(E.ESTADOS_RESUELTOS)} "
            f"(estado actual: '{solicitud.estado}')",
        )
    nuevo = datos["estado"]
    producto = solicitud.producto
    if nuevo == E.RECHAZADA:
        solicitud.monto_aprobado = None
        solicitud.tasa_aprobada = None
        solicitud.plazo_aprobado = None
        solicitud.mensualidad_aprobada = None
        solicitud.enganche_requerido = None
    else:
        monto = redondear(datos.get("monto") or solicitud.monto_aprobado or solicitud.monto_solicitado)
        tasa = redondear(
            datos["tasa"] if datos.get("tasa") is not None
            else (solicitud.tasa_aprobada if solicitud.tasa_aprobada is not None else producto.tasa_anual)
        )
        plazo = datos.get("plazo") or solicitud.plazo_aprobado or solicitud.plazo_meses
        validar_monto_plazo(producto, monto, plazo)
        if solicitud.tipo == "hipoteca" and solicitud.valor_inmueble is not None:
            if monto >= solicitud.valor_inmueble:
                raise ApiError(400, "MONTO_EXCEDE_VALOR", "El monto debe ser menor al valor del inmueble")
            solicitud.enganche_requerido = redondear(solicitud.valor_inmueble - monto)
        solicitud.monto_aprobado = monto
        solicitud.tasa_aprobada = tasa
        solicitud.plazo_aprobado = plazo
        solicitud.mensualidad_aprobada = calcular_mensualidad(monto, tasa, plazo)
    solicitud.motivo_resolucion = datos["motivo"]
    solicitud.resuelta_en = ahora()
    resultado = dict(solicitud.resultado_analisis or {})
    resultado["sobrescritura"] = {
        "analistaId": analista.id,
        "estadoAnterior": solicitud.estado,
        "estadoNuevo": nuevo,
        "motivo": datos["motivo"],
        "fecha": ahora().isoformat(),
    }
    solicitud.resultado_analisis = resultado
    cambiar_estado(
        db, solicitud, nuevo, analista.id, f"Resolución sobrescrita por analista: {datos['motivo']}", validar=False
    )
    db.commit()
    db.refresh(solicitud)
    return solicitud
