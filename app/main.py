"""Punto de entrada de la API Banco Demo (FastAPI).

Ejecutar con::

    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import ENV_FILE, settings
from app.core.database import crear_tablas
from app.core.exceptions import registrar_manejadores
from app.core.middlewares import CabecerasSeguridadMiddleware, RedPermitidaMiddleware, limiter
from app.routers import (
    admin,
    auth,
    cuentas,
    evaluacion,
    expediente,
    health,
    productos,
    simuladores,
    solicitudes,
    usuarios,
)

logger = logging.getLogger("banco_demo")

DESCRIPCION = """
API REST **demostrativa** de un banco simulado para la solicitud de **hipotecas** y
**préstamos personales**. Proyecto académico: **todos los datos son ficticios** y no hay
conexión con bancos reales.

* Autenticación JWT: use `POST /api/v1/auth/login` y el botón **Authorize** con el token.
* Respuestas con el sobre `{ ok, message, data, meta?, demo }` y errores
  `{ ok: false, error: { code, message, details }, demo }`.
* JSON en camelCase; la entrada acepta camelCase y snake_case.
* Usuarios demo: `cliente1@demo-banco.test` … con contraseña `Demo1234!`.
"""

TAGS = [
    {"name": "Sistema", "description": "Salud del servicio."},
    {"name": "Autenticación", "description": "Login JWT y usuario actual."},
    {"name": "Usuarios", "description": "Registro de clientes y perfil."},
    {"name": "Administración", "description": "Gestión de usuarios y estadísticas (admin)."},
    {"name": "Productos", "description": "Catálogo de productos de crédito."},
    {"name": "Simuladores", "description": "Simuladores públicos de préstamo, hipoteca y amortización."},
    {"name": "Solicitudes", "description": "Ciclo de vida de la solicitud: alta, análisis, oferta y formalización."},
    {"name": "Expediente", "description": "Datos del solicitante y documentos simulados."},
    {"name": "Evaluación del inmueble", "description": "Inmueble y avalúos de hipotecas."},
    {"name": "Cuentas", "description": "Consulta de cuentas y movimientos demo."},
]


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Crea las tablas al arrancar y avisa si se usan valores por defecto."""
    if not ENV_FILE.exists():
        logger.warning(
            "No se encontró %s: se usan valores de desarrollo por defecto "
            "(JWT_SECRET aleatorio por proceso, SQLite local). Copie .env.example a .env.",
            ENV_FILE,
        )
        print(f"[AVISO] No existe {ENV_FILE}; usando configuración de desarrollo por defecto.")
    crear_tablas()
    yield


def crear_app() -> FastAPI:
    """Construye la aplicación con middlewares, manejadores y routers."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=DESCRIPCION,
        openapi_tags=TAGS,
        docs_url="/docs" if settings.DOCS_ENABLED else None,
        redoc_url="/redoc" if settings.DOCS_ENABLED else None,
        openapi_url="/openapi.json" if settings.DOCS_ENABLED else None,
        lifespan=lifespan,
    )

    # Rate limit
    app.state.limiter = limiter
    registrar_manejadores(app)

    # Middlewares (el último agregado es el más externo)
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(RedPermitidaMiddleware)
    app.add_middleware(CabecerasSeguridadMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_lista,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    prefijo = settings.API_PREFIX
    for modulo in (health, auth, usuarios, admin, productos, simuladores, solicitudes, expediente, evaluacion, cuentas):
        app.include_router(modulo.router, prefix=prefijo)

    return app


app = crear_app()
