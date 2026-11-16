"""Cálculo del progreso del expediente y avance automático a ``datos_completos``."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.producto import DESCRIPCION_DOCUMENTOS
from app.models.solicitud import Solicitud
from app.services.comun import cambiar_estado
from app.utils import estados as E

ESTADOS_DOC_VALIDOS = ("entregado", "validado")

_PORCENTAJE_ESTADO = {
    E.DATOS_COMPLETOS: 40,
    E.EN_AVALUO: 50,
    E.AVALUO_COMPLETADO: 60,
    E.EN_ANALISIS: 70,
    E.APROBADA: 80,
    E.CONDICIONADA: 80,
    E.OFERTA_ACEPTADA: 90,
    E.FORMALIZADA: 100,
    E.RECHAZADA: 100,
    E.OFERTA_RECHAZADA: 100,
    E.CANCELADA: 100,
}


def documentos_estado(solicitud: Solicitud) -> list[dict[str, Any]]:
    """Lista de documentos requeridos con su estado (``pendiente`` si no se ha entregado)."""
    por_tipo = {d.tipo: d for d in solicitud.documentos}
    resultado = []
    for tipo in solicitud.producto.documentos_requeridos:
        doc = por_tipo.get(tipo)
        resultado.append(
            {
                "tipo": tipo,
                "descripcion": DESCRIPCION_DOCUMENTOS.get(tipo, tipo),
                "estado": doc.estado if doc else "pendiente",
                "documento_id": doc.id if doc else None,
                "nombre_archivo_simulado": doc.nombre_archivo_simulado if doc else None,
                "observaciones": doc.observaciones if doc else None,
                "fecha": doc.fecha if doc else None,
            }
        )
    return resultado


def documentos_rechazados(solicitud: Solicitud) -> list[str]:
    """Tipos de documento requeridos que están rechazados."""
    requeridos = set(solicitud.producto.documentos_requeridos)
    return [d.tipo for d in solicitud.documentos if d.tipo in requeridos and d.estado == "rechazado"]


def expediente_completo(solicitud: Solicitud) -> bool:
    """Solicitante + todos los documentos entregados/validados + inmueble si es hipoteca."""
    if solicitud.solicitante is None:
        return False
    entregados = {d.tipo for d in solicitud.documentos if d.estado in ESTADOS_DOC_VALIDOS}
    if not set(solicitud.producto.documentos_requeridos) <= entregados:
        return False
    return not (solicitud.tipo == "hipoteca" and solicitud.inmueble is None)


def intentar_completar(db: Session, solicitud: Solicitud, usuario_id: int | None) -> bool:
    """Si está en borrador y el expediente está completo, avanza a ``datos_completos``."""
    if solicitud.estado == E.BORRADOR and expediente_completo(solicitud):
        cambiar_estado(
            db, solicitud, E.DATOS_COMPLETOS, usuario_id,
            "Expediente completo: avance automático a datos_completos",
        )
        return True
    return False


def _siguiente_paso(solicitud: Solicitud, pendientes: list[str], rechazados: list[str]) -> str:
    es_hipoteca = solicitud.tipo == "hipoteca"
    estado = solicitud.estado
    if estado == E.BORRADOR:
        faltantes = []
        if solicitud.solicitante is None:
            faltantes.append("capturar datos del solicitante (PUT /solicitante)")
        if pendientes or rechazados:
            faltantes.append(f"entregar documentos: {', '.join(pendientes + rechazados)}")
        if es_hipoteca and solicitud.inmueble is None:
            faltantes.append("registrar el inmueble (PUT /inmueble)")
        return "Falta " + "; ".join(faltantes)
    if estado == E.DATOS_COMPLETOS:
        if rechazados:
            return f"Volver a entregar documentos rechazados: {', '.join(rechazados)}"
        return "Solicitar avalúo (POST /avaluo)" if es_hipoteca else "Ejecutar análisis (POST /analisis)"
    textos = {
        E.EN_AVALUO: "Esperar el resultado del avalúo",
        E.AVALUO_COMPLETADO: "Ejecutar análisis de crédito (POST /analisis)",
        E.EN_ANALISIS: "Esperar la resolución del análisis",
        E.APROBADA: "Revisar la oferta y aceptarla o rechazarla",
        E.CONDICIONADA: "Revisar la oferta condicionada y aceptarla o rechazarla",
        E.OFERTA_ACEPTADA: "Formalizar el crédito (POST /formalizar)",
        E.FORMALIZADA: "Crédito formalizado: consultar la tabla de amortización",
        E.RECHAZADA: "Solicitud rechazada: proceso terminado",
        E.OFERTA_RECHAZADA: "Oferta rechazada: proceso terminado",
        E.CANCELADA: "Solicitud cancelada: proceso terminado",
    }
    return textos.get(estado, "")


def calcular_progreso(solicitud: Solicitud) -> dict[str, Any]:
    """Resumen de qué falta para avanzar."""
    requeridos = list(solicitud.producto.documentos_requeridos)
    docs = {d.tipo: d for d in solicitud.documentos}
    entregados = [t for t in requeridos if t in docs and docs[t].estado in ESTADOS_DOC_VALIDOS]
    rechazados = [t for t in requeridos if t in docs and docs[t].estado == "rechazado"]
    pendientes = [t for t in requeridos if t not in docs]
    es_hipoteca = solicitud.tipo == "hipoteca"
    avaluo = solicitud.inmueble.avaluo if solicitud.inmueble else None

    if solicitud.estado == E.BORRADOR:
        total = 1 + len(requeridos) + (1 if es_hipoteca else 0)
        hechos = (1 if solicitud.solicitante else 0) + len(entregados)
        hechos += 1 if es_hipoteca and solicitud.inmueble else 0
        porcentaje = int(hechos * 40 / total) if total else 0
    else:
        porcentaje = _PORCENTAJE_ESTADO.get(solicitud.estado, 0)

    return {
        "porcentaje": porcentaje,
        "solicitante_completo": solicitud.solicitante is not None,
        "documentos_requeridos": requeridos,
        "documentos_entregados": entregados,
        "documentos_pendientes": pendientes,
        "documentos_rechazados": rechazados,
        "inmueble_requerido": es_hipoteca,
        "inmueble_registrado": solicitud.inmueble is not None,
        "avaluo_requerido": es_hipoteca,
        "avaluo_estado": avaluo.estado if avaluo else None,
        "editable": solicitud.estado in E.ESTADOS_EDITABLES,
        "siguiente_paso": _siguiente_paso(solicitud, pendientes, rechazados),
    }
