"""Modelos ORM. Importarlos aquí registra todas las tablas en ``Base.metadata``."""

from app.models.avaluo import Avaluo
from app.models.cuenta import Cuenta
from app.models.documento import DocumentoSolicitud
from app.models.historial import HistorialEstado
from app.models.inmueble import Inmueble
from app.models.movimiento import Movimiento
from app.models.producto import ProductoCredito
from app.models.solicitante import Solicitante
from app.models.solicitud import Solicitud
from app.models.usuario import Usuario

__all__ = [
    "Avaluo",
    "Cuenta",
    "DocumentoSolicitud",
    "HistorialEstado",
    "Inmueble",
    "Movimiento",
    "ProductoCredito",
    "Solicitante",
    "Solicitud",
    "Usuario",
]
