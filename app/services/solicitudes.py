"""Servicio de solicitudes: alta, consulta, cancelación, oferta y formalización."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ApiError
from app.models.cuenta import Cuenta
from app.models.historial import HistorialEstado
from app.models.movimiento import Movimiento
from app.models.solicitud import Solicitud
from app.models.usuario import Usuario
from app.services import productos as productos_service
from app.services.comun import (
    cambiar_estado,
    es_personal,
    solicitud_con_acceso,
    solicitud_propia,
)
from app.services.progreso import calcular_progreso, documentos_estado
from app.services.simuladores import validar_monto_plazo
from app.utils import estados as E
from app.utils.fechas import ahora, sumar_meses
from app.utils.finanzas import cat_demo, redondear, resumen_credito, tabla_amortizacion
from app.utils.identificadores import folio_solicitud, referencia_movimiento


# ---------------------------------------------------------------------------
# Alta y consulta
# ---------------------------------------------------------------------------

def contar_activas(db: Session, usuario_id: int) -> int:
    """Número de solicitudes no finales del usuario."""
    return db.scalar(
        select(func.count(Solicitud.id)).where(
            Solicitud.usuario_id == usuario_id, Solicitud.estado.not_in(list(E.ESTADOS_FINALES))
        )
    ) or 0


def crear(db: Session, usuario: Usuario, datos: dict) -> Solicitud:
    """Crea una solicitud en ``borrador`` aplicando las reglas de alta."""
    producto = productos_service.obtener(db, datos["producto_id"])
    if not producto.activo:
        raise ApiError(400, "PRODUCTO_INACTIVO", "El producto no está disponible para nuevas solicitudes")
    activas = contar_activas(db, usuario.id)
    if activas >= settings.MAX_SOLICITUDES_ACTIVAS:
        raise ApiError(
            400,
            "LIMITE_SOLICITUDES",
            f"No puede tener más de {settings.MAX_SOLICITUDES_ACTIVAS} solicitudes activas",
            [{"activas": activas, "maximo": settings.MAX_SOLICITUDES_ACTIVAS}],
        )
    monto: Decimal = redondear(datos["monto_solicitado"])
    plazo: int = datos["plazo_meses"]
    validar_monto_plazo(producto, monto, plazo)

    valor_inmueble = None
    enganche = None
    if producto.tipo == "hipoteca":
        valor_inmueble = datos.get("valor_inmueble")
        if valor_inmueble is None:
            raise ApiError(400, "VALOR_INMUEBLE_REQUERIDO", "El valor del inmueble es obligatorio en hipotecas")
        valor_inmueble = redondear(valor_inmueble)
        if monto >= valor_inmueble:
            raise ApiError(400, "MONTO_EXCEDE_VALOR", "El monto solicitado debe ser menor al valor del inmueble")
        enganche = redondear(valor_inmueble - monto)
        minimo = redondear(valor_inmueble * (producto.enganche_min_pct or 0) / 100)
        if enganche < minimo:
            raise ApiError(
                400,
                "ENGANCHE_INSUFICIENTE",
                f"El enganche ({enganche}) es menor al mínimo requerido ({minimo}, "
                f"{producto.enganche_min_pct}% del valor del inmueble)",
                [{"enganche": float(enganche), "engancheMinimo": float(minimo),
                  "engancheMinPct": float(producto.enganche_min_pct or 0)}],
            )

    fecha = ahora()
    solicitud = Solicitud(
        usuario_id=usuario.id,
        producto_id=producto.id,
        tipo=producto.tipo,
        monto_solicitado=monto,
        plazo_meses=plazo,
        valor_inmueble=valor_inmueble,
        enganche=enganche,
        estado=E.BORRADOR,
        creada_en=fecha,
        actualizada_en=fecha,
    )
    db.add(solicitud)
    db.flush()
    solicitud.folio = folio_solicitud(solicitud.id, fecha.year)
    db.add(
        HistorialEstado(
            solicitud_id=solicitud.id, estado_anterior=None, estado_nuevo=E.BORRADOR,
            usuario_id=usuario.id, nota="Solicitud creada", fecha=fecha,
        )
    )
    db.commit()
    db.refresh(solicitud)
    return solicitud


def listar(
    db: Session, usuario: Usuario, *, estado: str | None, tipo: str | None, offset: int, limit: int
) -> tuple[list[Solicitud], int]:
    """Cliente: sus solicitudes. Analista/admin: todas."""
    consulta = select(Solicitud)
    if not es_personal(usuario):
        consulta = consulta.where(Solicitud.usuario_id == usuario.id)
    if estado:
        consulta = consulta.where(Solicitud.estado == estado)
    if tipo:
        consulta = consulta.where(Solicitud.tipo == tipo)
    total = db.scalar(select(func.count()).select_from(consulta.subquery())) or 0
    filas = list(db.scalars(consulta.order_by(Solicitud.id.desc()).offset(offset).limit(limit)))
    return filas, total


def detalle(solicitud: Solicitud) -> dict[str, Any]:
    """Detalle completo con solicitante, inmueble, documentos y progreso."""
    datos = {c.name: getattr(solicitud, c.name) for c in Solicitud.__table__.columns}
    datos.update(
        {
            "producto": solicitud.producto,
            "solicitante": solicitud.solicitante,
            "inmueble": solicitud.inmueble,
            "documentos": documentos_estado(solicitud),
            "progreso": calcular_progreso(solicitud),
        }
    )
    return datos


def obtener_detalle(db: Session, solicitud_id: int, usuario: Usuario) -> dict[str, Any]:
    """Detalle de una solicitud validando el acceso."""
    return detalle(solicitud_con_acceso(db, solicitud_id, usuario))


def historial(db: Session, solicitud_id: int, usuario: Usuario) -> list[HistorialEstado]:
    """Historial de estados de la solicitud."""
    return list(solicitud_con_acceso(db, solicitud_id, usuario).historial)


def cancelar(db: Session, solicitud_id: int, usuario: Usuario, motivo: str | None) -> Solicitud:
    """Cancela una solicitud propia si el estado lo permite."""
    solicitud = solicitud_propia(db, solicitud_id, usuario)
    cambiar_estado(db, solicitud, E.CANCELADA, usuario.id, motivo or "Cancelada por el cliente")
    db.commit()
    db.refresh(solicitud)
    return solicitud


# ---------------------------------------------------------------------------
# Oferta y formalización
# ---------------------------------------------------------------------------

def _vigente_hasta(solicitud: Solicitud):
    emision = solicitud.resuelta_en or solicitud.actualizada_en
    return emision, emision + timedelta(days=settings.OFERTA_VIGENCIA_DIAS)


def construir_oferta(solicitud: Solicitud) -> dict[str, Any]:
    """Oferta demostrativa a partir de la resolución vigente."""
    if solicitud.estado not in (E.APROBADA, E.CONDICIONADA, E.OFERTA_ACEPTADA, E.FORMALIZADA) or (
        solicitud.monto_aprobado is None
    ):
        raise ApiError(
            400, "OFERTA_NO_DISPONIBLE",
            f"La solicitud en estado '{solicitud.estado}' no tiene una oferta disponible",
        )
    monto = solicitud.monto_aprobado
    tasa = solicitud.tasa_aprobada
    plazo = solicitud.plazo_aprobado
    resumen = resumen_credito(monto, tasa, plazo)
    emision, vence = _vigente_hasta(solicitud)
    return {
        "solicitud_id": solicitud.id,
        "folio": solicitud.folio,
        "estado": solicitud.estado,
        "producto": solicitud.producto.nombre,
        "monto": monto,
        "tasa_anual": tasa,
        "plazo_meses": plazo,
        "mensualidad": resumen["mensualidad"],
        "total_pagar": resumen["total_pagar"],
        "total_intereses": resumen["total_intereses"],
        "cat_demo": cat_demo(tasa, plazo, settings.CAT_COMISION_APERTURA_PCT),
        "enganche_requerido": solicitud.enganche_requerido,
        "condicionada": _fue_condicionada(solicitud),
        "condiciones": solicitud.motivo_resolucion,
        "fecha_emision": emision,
        "vigente_hasta": vence,
        "vigente": ahora() <= vence,
    }


def _fue_condicionada(solicitud: Solicitud) -> bool:
    if solicitud.estado == E.CONDICIONADA:
        return True
    for registro in reversed(solicitud.historial):
        if registro.estado_nuevo in E.ESTADOS_RESUELTOS:
            return registro.estado_nuevo == E.CONDICIONADA
    return False


def oferta(db: Session, solicitud_id: int, usuario: Usuario) -> dict[str, Any]:
    """Oferta de una solicitud propia."""
    return construir_oferta(solicitud_propia(db, solicitud_id, usuario))


def aceptar_oferta(db: Session, solicitud_id: int, usuario: Usuario) -> Solicitud:
    """Acepta la oferta vigente."""
    solicitud = solicitud_propia(db, solicitud_id, usuario)
    E.validar_transicion(solicitud.estado, E.OFERTA_ACEPTADA, solicitud.tipo)
    _, vence = _vigente_hasta(solicitud)
    if ahora() > vence:
        raise ApiError(400, "OFERTA_VENCIDA", f"La oferta venció el {vence.isoformat()}")
    cambiar_estado(db, solicitud, E.OFERTA_ACEPTADA, usuario.id, "Oferta aceptada por el cliente")
    db.commit()
    db.refresh(solicitud)
    return solicitud


def rechazar_oferta(db: Session, solicitud_id: int, usuario: Usuario, motivo: str | None) -> Solicitud:
    """Rechaza la oferta."""
    solicitud = solicitud_propia(db, solicitud_id, usuario)
    cambiar_estado(db, solicitud, E.OFERTA_RECHAZADA, usuario.id, motivo or "Oferta rechazada por el cliente")
    db.commit()
    db.refresh(solicitud)
    return solicitud


def formalizar(db: Session, solicitud_id: int, usuario: Usuario) -> Solicitud:
    """Formaliza el crédito. En préstamos deposita el monto en la cuenta del cliente (demo)."""
    solicitud = solicitud_propia(db, solicitud_id, usuario)
    cambiar_estado(db, solicitud, E.FORMALIZADA, usuario.id, "Crédito formalizado (demo)")
    fecha = ahora()
    solicitud.formalizada_en = fecha
    if solicitud.tipo == "prestamo" and solicitud.monto_aprobado:
        cuenta = db.scalar(
            select(Cuenta)
            .where(Cuenta.usuario_id == solicitud.usuario_id, Cuenta.estado == "activa")
            .order_by(Cuenta.tipo, Cuenta.id)
        )
        if cuenta is not None:
            cuenta.saldo = redondear(cuenta.saldo + solicitud.monto_aprobado)
            db.add(
                Movimiento(
                    cuenta_id=cuenta.id,
                    tipo="deposito",
                    concepto=f"Disposición de préstamo {solicitud.folio} (demo)",
                    monto=solicitud.monto_aprobado,
                    saldo_resultante=cuenta.saldo,
                    referencia=referencia_movimiento(fecha),
                    fecha=fecha,
                )
            )
    db.commit()
    db.refresh(solicitud)
    return solicitud


def amortizacion(db: Session, solicitud_id: int, usuario: Usuario) -> dict[str, Any]:
    """Tabla de amortización del crédito formalizado con fechas de pago."""
    solicitud = solicitud_propia(db, solicitud_id, usuario)
    if solicitud.estado != E.FORMALIZADA or solicitud.formalizada_en is None:
        raise ApiError(
            400, "CREDITO_NO_FORMALIZADO", "La tabla de amortización solo está disponible para créditos formalizados"
        )
    monto, tasa, plazo = solicitud.monto_aprobado, solicitud.tasa_aprobada, solicitud.plazo_aprobado
    resumen = resumen_credito(monto, tasa, plazo)
    tabla = tabla_amortizacion(monto, tasa, plazo)
    inicio = solicitud.formalizada_en.date()
    for fila in tabla:
        fila["fecha_pago"] = sumar_meses(inicio, fila["numero"]).isoformat()
    return {
        "monto": monto,
        "tasa_anual": tasa,
        "plazo_meses": plazo,
        "mensualidad": resumen["mensualidad"],
        "total_intereses": resumen["total_intereses"],
        "total_pagar": resumen["total_pagar"],
        "tabla": tabla,
        "leyenda": f"CRÉDITO DEMOSTRATIVO {solicitud.folio} - SIN VALIDEZ REAL",
    }


__all__ = [
    "aceptar_oferta",
    "amortizacion",
    "cancelar",
    "construir_oferta",
    "crear",
    "detalle",
    "formalizar",
    "historial",
    "listar",
    "obtener_detalle",
    "oferta",
    "rechazar_oferta",
]
