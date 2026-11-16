"""Servicio del expediente: datos del solicitante y documentos simulados."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ApiError
from app.models.documento import DocumentoSolicitud
from app.models.solicitante import Solicitante
from app.models.solicitud import Solicitud
from app.models.usuario import Usuario
from app.services.comun import (
    obtener_o_404,
    obtener_solicitud,
    solicitud_con_acceso,
    solicitud_propia,
    validar_editable,
)
from app.services.progreso import documentos_estado, intentar_completar
from app.utils.estados import es_final
from app.utils.fechas import ahora, edad_en, hoy, sumar_meses


def _validar_edad(fecha_nacimiento, plazo_meses: int) -> None:
    """Mayor de edad hoy y menor de 70 años al terminar el plazo."""
    fecha_hoy = hoy()
    if fecha_nacimiento >= fecha_hoy:
        raise ApiError(400, "FECHA_NACIMIENTO_INVALIDA", "La fecha de nacimiento debe ser anterior a hoy")
    edad = edad_en(fecha_nacimiento, fecha_hoy)
    if edad < settings.EDAD_MINIMA:
        raise ApiError(
            400, "EDAD_INSUFICIENTE", f"El solicitante debe ser mayor de {settings.EDAD_MINIMA} años",
            [{"edad": edad, "edadMinima": settings.EDAD_MINIMA}],
        )
    edad_fin = edad_en(fecha_nacimiento, sumar_meses(fecha_hoy, plazo_meses))
    if edad_fin >= settings.EDAD_MAXIMA_FIN_PLAZO:
        raise ApiError(
            400,
            "EDAD_EXCEDE_PLAZO",
            f"El solicitante debe tener menos de {settings.EDAD_MAXIMA_FIN_PLAZO} años al terminar el plazo "
            f"(tendría {edad_fin})",
            [{"edadAlTerminar": edad_fin, "edadMaxima": settings.EDAD_MAXIMA_FIN_PLAZO}],
        )


def guardar_solicitante(
    db: Session, solicitud_id: int, usuario: Usuario, datos: dict[str, Any]
) -> tuple[Solicitante, Solicitud, bool]:
    """Crea o reemplaza los datos del solicitante. Devuelve (solicitante, solicitud, avanzó)."""
    solicitud = solicitud_propia(db, solicitud_id, usuario)
    validar_editable(solicitud)
    _validar_edad(datos["fecha_nacimiento"], solicitud.plazo_meses)
    datos = dict(datos)
    datos["referencias"] = [dict(r) for r in datos["referencias"]]
    solicitante = solicitud.solicitante
    if solicitante is None:
        solicitante = Solicitante(solicitud_id=solicitud.id, **datos)
        db.add(solicitante)
        solicitud.solicitante = solicitante
    else:
        for campo, valor in datos.items():
            setattr(solicitante, campo, valor)
    solicitud.actualizada_en = ahora()
    db.flush()
    avanzo = intentar_completar(db, solicitud, usuario.id)
    db.commit()
    db.refresh(solicitante)
    return solicitante, solicitud, avanzo


def obtener_solicitante(db: Session, solicitud_id: int, usuario: Usuario) -> Solicitante:
    """Datos del solicitante (404 si aún no se capturan)."""
    solicitud = solicitud_con_acceso(db, solicitud_id, usuario)
    if solicitud.solicitante is None:
        raise ApiError(404, "SOLICITANTE_NO_REGISTRADO", "La solicitud aún no tiene datos del solicitante")
    return solicitud.solicitante


def listar_documentos(db: Session, solicitud_id: int, usuario: Usuario) -> list[dict[str, Any]]:
    """Documentos requeridos con su estado, incluyendo pendientes."""
    return documentos_estado(solicitud_con_acceso(db, solicitud_id, usuario))


def entregar_documento(
    db: Session, solicitud_id: int, usuario: Usuario, tipo: str, nombre_archivo: str
) -> tuple[DocumentoSolicitud, Solicitud, bool]:
    """Registra la entrega simulada de un documento (reemplaza si estaba rechazado)."""
    solicitud = solicitud_propia(db, solicitud_id, usuario)
    validar_editable(solicitud)
    requeridos = solicitud.producto.documentos_requeridos
    if tipo not in requeridos:
        raise ApiError(
            400, "DOCUMENTO_NO_REQUERIDO", f"El documento '{tipo}' no es requerido por este producto",
            [{"documentosRequeridos": requeridos}],
        )
    documento = next((d for d in solicitud.documentos if d.tipo == tipo), None)
    if documento is not None:
        if documento.estado != "rechazado":
            raise ApiError(
                409, "DOCUMENTO_YA_ENTREGADO",
                f"El documento '{tipo}' ya fue entregado (estado: {documento.estado})",
            )
        documento.nombre_archivo_simulado = nombre_archivo
        documento.estado = "entregado"
        documento.observaciones = None
        documento.fecha = ahora()
    else:
        documento = DocumentoSolicitud(
            solicitud_id=solicitud.id, tipo=tipo, nombre_archivo_simulado=nombre_archivo,
            estado="entregado", fecha=ahora(),
        )
        db.add(documento)
        solicitud.documentos.append(documento)
    solicitud.actualizada_en = ahora()
    db.flush()
    avanzo = intentar_completar(db, solicitud, usuario.id)
    db.commit()
    db.refresh(documento)
    return documento, solicitud, avanzo


def revisar_documento(
    db: Session, solicitud_id: int, documento_id: int, estado: str, observaciones: str | None
) -> DocumentoSolicitud:
    """El analista valida o rechaza un documento."""
    solicitud = obtener_solicitud(db, solicitud_id)
    documento = obtener_o_404(db, DocumentoSolicitud, documento_id, "El documento", "DOCUMENTO_NO_ENCONTRADO")
    if documento.solicitud_id != solicitud.id:
        raise ApiError(404, "DOCUMENTO_NO_ENCONTRADO", "El documento no pertenece a esta solicitud")
    if es_final(solicitud.estado):
        raise ApiError(400, "SOLICITUD_FINALIZADA", "La solicitud está en un estado final")
    documento.estado = estado
    documento.observaciones = observaciones
    documento.fecha = ahora()
    solicitud.actualizada_en = ahora()
    db.commit()
    db.refresh(documento)
    return documento
