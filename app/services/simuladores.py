"""Servicio de simuladores de préstamo, hipoteca y amortización."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ApiError
from app.models.producto import ProductoCredito
from app.services import productos as productos_service
from app.utils.finanzas import cat_demo, redondear, resumen_credito, tabla_amortizacion

ENGANCHE_MIN_DEFECTO = Decimal("10.00")


def _producto_para(db: Session, producto_id: int, tipo: str, monto: Decimal, plazo: int) -> ProductoCredito:
    """Valida que el producto exista, sea del tipo y admita el monto y plazo."""
    producto = productos_service.obtener(db, producto_id)
    if not producto.activo:
        raise ApiError(400, "PRODUCTO_INACTIVO", "El producto no está disponible")
    if producto.tipo != tipo:
        raise ApiError(400, "TIPO_PRODUCTO_INVALIDO", f"El producto indicado no es de tipo {tipo}")
    validar_monto_plazo(producto, monto, plazo)
    return producto


def validar_monto_plazo(producto: ProductoCredito, monto: Decimal, plazo: int) -> None:
    """Monto dentro de [monto_min, monto_max] y plazo dentro de plazos_meses."""
    if monto < producto.monto_min or monto > producto.monto_max:
        raise ApiError(
            400,
            "MONTO_FUERA_DE_RANGO",
            f"El monto debe estar entre {producto.monto_min} y {producto.monto_max}",
            [{"montoMin": float(producto.monto_min), "montoMax": float(producto.monto_max)}],
        )
    if plazo not in producto.plazos_meses:
        raise ApiError(
            400,
            "PLAZO_NO_PERMITIDO",
            f"El plazo debe ser uno de {producto.plazos_meses} meses",
            [{"plazosPermitidos": producto.plazos_meses}],
        )


def _resultado_base(monto: Decimal, tasa: Decimal, plazo: int, producto: ProductoCredito | None) -> dict:
    resumen = resumen_credito(monto, tasa, plazo)
    return {
        "monto": redondear(monto),
        "tasa_anual": redondear(tasa),
        "plazo_meses": plazo,
        "mensualidad": resumen["mensualidad"],
        "total_intereses": resumen["total_intereses"],
        "total_pagar": resumen["total_pagar"],
        "cat_demo": cat_demo(tasa, plazo, settings.CAT_COMISION_APERTURA_PCT),
        "producto_id": producto.id if producto else None,
        "producto_nombre": producto.nombre if producto else None,
    }


def simular_prestamo(db: Session, datos: dict) -> dict:
    """Mensualidad, intereses, total y CAT demo de un préstamo."""
    monto, plazo = datos["monto"], datos["plazo_meses"]
    producto = None
    tasa = datos.get("tasa_anual")
    if datos.get("producto_id"):
        producto = _producto_para(db, datos["producto_id"], "prestamo", monto, plazo)
        tasa = producto.tasa_anual
    return _resultado_base(monto, tasa, plazo, producto)


def simular_hipoteca(db: Session, datos: dict) -> dict:
    """Simulación de hipoteca con validación de enganche mínimo."""
    valor, enganche, plazo = datos["valor_inmueble"], datos["enganche"], datos["plazo_meses"]
    monto = redondear(valor - enganche)
    producto = None
    tasa = datos.get("tasa_anual")
    enganche_min_pct = datos.get("enganche_min_pct")
    if datos.get("producto_id"):
        producto = _producto_para(db, datos["producto_id"], "hipoteca", monto, plazo)
        tasa = producto.tasa_anual
        enganche_min_pct = producto.enganche_min_pct
    if enganche_min_pct is None:
        enganche_min_pct = ENGANCHE_MIN_DEFECTO
    enganche_minimo = redondear(valor * enganche_min_pct / 100)
    enganche_pct = redondear(enganche / valor * 100)
    cumple = enganche >= enganche_minimo
    mensaje = (
        "El enganche cumple con el mínimo requerido"
        if cumple
        else f"El enganche es insuficiente: se requiere al menos {enganche_minimo} ({enganche_min_pct}%)"
    )
    resultado = _resultado_base(monto, tasa, plazo, producto)
    resultado.update(
        {
            "valor_inmueble": redondear(valor),
            "enganche": redondear(enganche),
            "enganche_pct": enganche_pct,
            "enganche_min_pct": redondear(enganche_min_pct),
            "enganche_minimo": enganche_minimo,
            "cumple_enganche_minimo": cumple,
            "mensaje_enganche": mensaje,
        }
    )
    return resultado


def simular_amortizacion(datos: dict) -> dict:
    """Tabla de amortización mes a mes con resumen."""
    monto, tasa, plazo = datos["monto"], datos["tasa_anual"], datos["plazo_meses"]
    resumen = resumen_credito(monto, tasa, plazo)
    return {
        "monto": redondear(monto),
        "tasa_anual": redondear(tasa),
        "plazo_meses": plazo,
        "mensualidad": resumen["mensualidad"],
        "total_intereses": resumen["total_intereses"],
        "total_pagar": resumen["total_pagar"],
        "tabla": tabla_amortizacion(monto, tasa, plazo),
    }
