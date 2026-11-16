"""Esquemas comunes: base camelCase, tipos de dinero y sobres de respuesta."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Generic, TypeVar

from email_validator import EmailNotValidError, validate_email
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, PlainSerializer
from pydantic.alias_generators import to_camel

T = TypeVar("T")


def _decimal_a_float(valor: Decimal | None) -> float | None:
    """Serializa Decimal como número JSON (los montos ya vienen a 2 decimales)."""
    return None if valor is None else float(valor)


# Dinero: Decimal con 2 decimales, se serializa como número en JSON.
Dinero = Annotated[
    Decimal,
    Field(max_digits=12, decimal_places=2),
    PlainSerializer(_decimal_a_float, return_type=float, when_used="json"),
]
# Porcentaje / tasa: Decimal con 2 decimales.
Porcentaje = Annotated[
    Decimal,
    Field(max_digits=6, decimal_places=2),
    PlainSerializer(_decimal_a_float, return_type=float, when_used="json"),
]
# Decimal de salida sin restricción de dígitos (ya redondeado por el servicio).
DecimalSalida = Annotated[
    Decimal,
    PlainSerializer(_decimal_a_float, return_type=float, when_used="json"),
]


def _validar_correo(valor: str) -> str:
    """Valida el formato del correo (sin DNS) y lo normaliza a minúsculas.

    ``test_environment=True`` permite dominios reservados como ``.test``, usados
    por los usuarios demo (``@demo-banco.test``).
    """
    try:
        resultado = validate_email(valor, check_deliverability=False, test_environment=True)
    except EmailNotValidError as exc:
        raise ValueError("Correo electrónico no válido") from exc
    return resultado.normalized.lower()


# Correo electrónico validado y en minúsculas.
Correo = Annotated[
    str,
    Field(min_length=5, max_length=160, json_schema_extra={"format": "email"}),
    AfterValidator(_validar_correo),
]


class SchemaBase(BaseModel):
    """Base de todos los esquemas: JSON en camelCase, acepta camelCase y snake_case."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        str_strip_whitespace=True,
    )


class Meta(SchemaBase):
    """Metadatos de paginación."""

    page: int
    limit: int
    total: int


class Respuesta(SchemaBase, Generic[T]):
    """Sobre estándar de respuesta exitosa."""

    ok: bool = True
    message: str
    data: T | None = None
    demo: bool = True


class RespuestaPaginada(SchemaBase, Generic[T]):
    """Sobre estándar de respuesta exitosa con paginación."""

    ok: bool = True
    message: str
    data: list[T]
    meta: Meta
    demo: bool = True


class MensajeSimple(SchemaBase):
    """Datos mínimos para respuestas sin contenido relevante."""

    id: int | None = None
    estado: str | None = None
