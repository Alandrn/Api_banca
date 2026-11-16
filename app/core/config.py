"""Configuración central de la aplicación.

Los valores se leen de variables de entorno y del archivo ``.env`` en la raíz del
proyecto. Si el archivo no existe la aplicación arranca con valores de desarrollo
seguros por defecto (secreto JWT aleatorio por proceso) y lo avisa en consola.
"""

from __future__ import annotations

import ipaddress
import secrets
from decimal import Decimal
from functools import cached_property
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Ruta absoluta al archivo .env (raíz del proyecto)
RAIZ_PROYECTO = Path(__file__).resolve().parents[2]
ENV_FILE = RAIZ_PROYECTO / ".env"


class Settings(BaseSettings):
    """Parámetros configurables de la API (todos con valor por defecto de desarrollo)."""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Aplicación ---
    APP_NAME: str = "API Banco Demo"
    APP_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"

    # --- Base de datos ---
    DATABASE_URL: str = f"sqlite:///{(RAIZ_PROYECTO / 'banco_demo.db').as_posix()}"

    # --- Seguridad ---
    JWT_SECRET: str = Field(default_factory=lambda: secrets.token_urlsafe(48))
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60
    BCRYPT_ROUNDS: int = 12

    # Orígenes CORS separados por coma
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
    # Redes permitidas en notación CIDR separadas por coma. Vacío = permitir todo.
    ALLOWED_NETWORKS: str = ""
    DOCS_ENABLED: bool = True

    # --- Rate limit (sintaxis de slowapi/limits) ---
    RATE_LIMIT_LOGIN: str = "5/minute"
    RATE_LIMIT_DEFAULT: str = "100/minute"
    RATE_LIMIT_ENABLED: bool = True

    # --- Reglas de negocio de solicitudes ---
    MAX_SOLICITUDES_ACTIVAS: int = 3
    OFERTA_VIGENCIA_DIAS: int = 15
    EDAD_MINIMA: int = 18
    EDAD_MAXIMA_FIN_PLAZO: int = 70
    REFERENCIAS_MINIMAS: int = 2

    # --- Reglas del análisis de crédito ---
    ANALISIS_MAX_RELACION_PAGO: Decimal = Decimal("0.35")
    ANALISIS_MAX_LTV: Decimal = Decimal("0.90")
    ANALISIS_BURO_MINIMO: int = 600
    ANALISIS_BURO_PREFERENTE: int = 750
    ANALISIS_DESCUENTO_PREFERENTE: Decimal = Decimal("1.00")
    ANALISIS_ANTIGUEDAD_MIN_MESES: int = 6
    ANALISIS_REDONDEO_MONTO_CONDICIONADO: Decimal = Decimal("100")

    # --- Avalúo automático ---
    AVALUO_FACTOR_MIN: Decimal = Decimal("0.85")
    AVALUO_FACTOR_MAX: Decimal = Decimal("1.05")

    # --- CAT demostrativo ---
    CAT_COMISION_APERTURA_PCT: Decimal = Decimal("1.00")

    @property
    def cors_origins_lista(self) -> list[str]:
        """Lista de orígenes CORS permitidos."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def redes_permitidas(self) -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
        """Lista de redes CIDR permitidas (vacía = sin restricción)."""
        redes = []
        for valor in self.ALLOWED_NETWORKS.split(","):
            valor = valor.strip()
            if valor:
                redes.append(ipaddress.ip_network(valor, strict=False))
        return redes

    @cached_property
    def env_file_existe(self) -> bool:
        """Indica si se encontró el archivo .env al arrancar."""
        return ENV_FILE.exists()


settings = Settings()
