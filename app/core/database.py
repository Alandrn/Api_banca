"""Conexión a la base de datos con SQLAlchemy 2.0.

La URL se toma de ``DATABASE_URL``; cambiarla a PostgreSQL no requiere tocar código.
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

_es_sqlite = settings.DATABASE_URL.startswith("sqlite")

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if _es_sqlite else {},
    pool_pre_ping=not _es_sqlite,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Clase base declarativa de todos los modelos."""


def get_db() -> Generator[Session, None, None]:
    """Dependencia de FastAPI que entrega una sesión y la cierra al terminar."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def crear_tablas() -> None:
    """Crea las tablas que no existan (importa los modelos para registrarlos)."""
    import app.models  # noqa: F401  (registra los modelos en el metadata)

    Base.metadata.create_all(bind=engine)
