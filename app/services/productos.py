"""Servicio de productos de crédito."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ApiError
from app.models.producto import DESCRIPCION_DOCUMENTOS, ProductoCredito
from app.services.comun import obtener_o_404


def listar(db: Session, tipo: str | None, activo: bool | None) -> list[ProductoCredito]:
    """Lista productos. Si no se filtra por ``activo`` solo devuelve los activos."""
    consulta = select(ProductoCredito)
    if tipo:
        consulta = consulta.where(ProductoCredito.tipo == tipo)
    consulta = consulta.where(ProductoCredito.activo == (True if activo is None else activo))
    return list(db.scalars(consulta.order_by(ProductoCredito.id)))


def obtener(db: Session, producto_id: int) -> ProductoCredito:
    """Obtiene un producto o 404 PRODUCTO_NO_ENCONTRADO."""
    return obtener_o_404(db, ProductoCredito, producto_id, "El producto", "PRODUCTO_NO_ENCONTRADO")


def requisitos(db: Session, producto_id: int) -> dict:
    """Requisitos legibles y documentos requeridos de un producto."""
    producto = obtener(db, producto_id)
    return {
        "producto_id": producto.id,
        "nombre": producto.nombre,
        "tipo": producto.tipo,
        "requisitos": producto.requisitos,
        "documentos_requeridos": [
            {"tipo": t, "descripcion": DESCRIPCION_DOCUMENTOS.get(t, t)} for t in producto.documentos_requeridos
        ],
        "enganche_min_pct": producto.enganche_min_pct,
        "monto_min": producto.monto_min,
        "monto_max": producto.monto_max,
        "plazos_meses": producto.plazos_meses,
        "condiciones": producto.condiciones,
    }


def _validar_nombre_unico(db: Session, nombre: str, excluir_id: int | None = None) -> None:
    consulta = select(ProductoCredito.id).where(ProductoCredito.nombre == nombre)
    if excluir_id is not None:
        consulta = consulta.where(ProductoCredito.id != excluir_id)
    if db.scalar(consulta) is not None:
        raise ApiError(409, "PRODUCTO_DUPLICADO", f"Ya existe un producto con el nombre '{nombre}'")


def crear(db: Session, datos: dict) -> ProductoCredito:
    """Crea un producto."""
    _validar_nombre_unico(db, datos["nombre"])
    producto = ProductoCredito(**datos)
    db.add(producto)
    db.commit()
    db.refresh(producto)
    return producto


def actualizar(db: Session, producto_id: int, datos: dict) -> ProductoCredito:
    """Reemplaza todos los campos de un producto (PUT)."""
    producto = obtener(db, producto_id)
    _validar_nombre_unico(db, datos["nombre"], excluir_id=producto_id)
    for campo, valor in datos.items():
        setattr(producto, campo, valor)
    db.commit()
    db.refresh(producto)
    return producto


def eliminar(db: Session, producto_id: int) -> None:
    """Borrado lógico (activo = False)."""
    producto = obtener(db, producto_id)
    producto.activo = False
    db.commit()
