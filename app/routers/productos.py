"""Router de productos de crédito."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.responses import errores, ok
from app.dependencies.auth import require_roles
from app.models.usuario import ROL_ADMIN, Usuario
from app.schemas.common import Respuesta
from app.schemas.productos import ProductoIn, ProductoOut, RequisitosOut
from app.services import productos as productos_service

router = APIRouter(prefix="/productos", tags=["Productos"])
solo_admin = require_roles(ROL_ADMIN)


@router.get(
    "",
    response_model=Respuesta[list[ProductoOut]],
    summary="Catálogo de productos",
    description="Lista los productos. Sin filtro `activo` solo se muestran los activos. Público.",
    responses=errores(422),
)
def listar(
    tipo: Literal["prestamo", "hipoteca"] | None = Query(None, description="Filtrar por tipo"),
    activo: bool | None = Query(None, description="Filtrar por activo (por defecto solo activos)"),
    db: Session = Depends(get_db),
):
    """Catálogo público."""
    productos = productos_service.listar(db, tipo, activo)
    return ok([ProductoOut.model_validate(p) for p in productos], "Catálogo de productos")


@router.get(
    "/{producto_id}",
    response_model=Respuesta[ProductoOut],
    summary="Detalle de producto",
    description="Detalle de un producto por id. Público.",
    responses=errores(404, 422),
)
def obtener(producto_id: int, db: Session = Depends(get_db)):
    """Detalle de producto."""
    return ok(ProductoOut.model_validate(productos_service.obtener(db, producto_id)), "Producto")


@router.get(
    "/{producto_id}/requisitos",
    response_model=Respuesta[RequisitosOut],
    summary="Requisitos del producto",
    description="Requisitos legibles, documentos requeridos, rangos de monto y plazos. Público.",
    responses=errores(404, 422),
)
def requisitos(producto_id: int, db: Session = Depends(get_db)):
    """Requisitos del producto."""
    return ok(RequisitosOut.model_validate(productos_service.requisitos(db, producto_id)), "Requisitos del producto")


@router.post(
    "",
    status_code=201,
    response_model=Respuesta[ProductoOut],
    summary="Crear producto",
    description="Alta de un producto. Hipotecas requieren `engancheMinPct`. Solo admin.",
    responses=errores(401, 403, 409, 422),
)
def crear(datos: ProductoIn, _: Usuario = Depends(solo_admin), db: Session = Depends(get_db)):
    """Alta de producto."""
    return ok(ProductoOut.model_validate(productos_service.crear(db, datos.model_dump())), "Producto creado")


@router.put(
    "/{producto_id}",
    response_model=Respuesta[ProductoOut],
    summary="Reemplazar producto",
    description="Reemplaza todos los campos del producto. Solo admin.",
    responses=errores(401, 403, 404, 409, 422),
)
def actualizar(producto_id: int, datos: ProductoIn, _: Usuario = Depends(solo_admin), db: Session = Depends(get_db)):
    """Actualización completa."""
    producto = productos_service.actualizar(db, producto_id, datos.model_dump())
    return ok(ProductoOut.model_validate(producto), "Producto actualizado")


@router.delete(
    "/{producto_id}",
    status_code=204,
    response_class=Response,
    summary="Desactivar producto",
    description="Borrado lógico: el producto queda inactivo y no admite nuevas solicitudes. Solo admin.",
    responses=errores(401, 403, 404),
)
def eliminar(producto_id: int, _: Usuario = Depends(solo_admin), db: Session = Depends(get_db)):
    """Borrado lógico."""
    productos_service.eliminar(db, producto_id)
    return Response(status_code=204)
