"""Configuración de pruebas: BD SQLite temporal, cliente HTTP y tokens por rol.

Las variables de entorno se fijan ANTES de importar la aplicación para que el
motor de base de datos apunte a un archivo temporal y nunca toque banco_demo.db.
"""

from __future__ import annotations

import os
import tempfile
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="banco_demo_tests_"))
os.environ.update(
    {
        "DATABASE_URL": f"sqlite:///{(_TMP / 'pruebas.db').as_posix()}",
        "JWT_SECRET": "secreto-exclusivo-de-pruebas-0123456789-abcdefghijklmnop",
        "JWT_EXPIRE_MINUTES": "60",
        "BCRYPT_ROUNDS": "4",
        "ALLOWED_NETWORKS": "",
        "DOCS_ENABLED": "true",
        "CORS_ORIGINS": "http://localhost:3000",
        "RATE_LIMIT_LOGIN": "5/minute",
        "RATE_LIMIT_DEFAULT": "100/minute",
        "RATE_LIMIT_ENABLED": "true",
    }
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import app.models  # noqa: E402,F401
from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.core.middlewares import limiter  # noqa: E402
from app.core.security import crear_token, hash_password  # noqa: E402
from app.main import app  # noqa: E402
from app.models.cuenta import Cuenta  # noqa: E402
from app.models.movimiento import Movimiento  # noqa: E402
from app.models.producto import ProductoCredito  # noqa: E402
from app.models.usuario import Usuario  # noqa: E402
from app.utils.fechas import ahora  # noqa: E402
from app.utils.identificadores import codigo_usuario  # noqa: E402
from seeds.seed import PRODUCTOS  # noqa: E402

PASSWORD = "Demo1234!"
_HASH = hash_password(PASSWORD)

# Ids fijos de los datos base (se insertan en este orden en cada prueba)
ADMIN_ID, VALUADOR_ID, ANALISTA_ID, CLIENTE_ID, CLIENTE2_ID, VALUADOR2_ID, INACTIVO_ID = range(1, 8)
CUENTA_CLIENTE_ID, CUENTA_CLIENTE2_ID = 1, 2

_USUARIOS = [
    ("Ada", "Admin Demo", "admin@demo-banco.test", "admin", True),
    ("Victor", "Valuador Demo", "valuador1@demo-banco.test", "valuador", True),
    ("Ana", "Analista Demo", "analista1@demo-banco.test", "analista", True),
    ("Carla", "Cliente Demo", "cliente1@demo-banco.test", "cliente", True),
    ("Carlos", "Cliente Dos", "cliente2@demo-banco.test", "cliente", True),
    ("Valeria", "Valuadora Dos", "valuador2@demo-banco.test", "valuador", True),
    ("Ivan", "Inactivo Demo", "inactivo@demo-banco.test", "cliente", False),
]


def _cargar_datos_base() -> None:
    db = SessionLocal()
    try:
        for nombre, apellidos, email, rol, activo in _USUARIOS:
            u = Usuario(nombre=nombre, apellidos=apellidos, email=email, password_hash=_HASH,
                        telefono="5512345678", rol=rol, activo=activo, creado_en=ahora())
            db.add(u)
            db.flush()
            u.codigo = codigo_usuario(u.id)
        db.add_all([ProductoCredito(**p, activo=True) for p in PRODUCTOS])
        fecha = ahora()
        c1 = Cuenta(usuario_id=CLIENTE_ID, numero="DEMO-1111-2222-7712", tipo="debito",
                    saldo=Decimal("8500.00"), moneda="MXN", estado="activa", creada_en=fecha)
        c2 = Cuenta(usuario_id=CLIENTE2_ID, numero="DEMO-3333-4444-5566", tipo="ahorro",
                    saldo=Decimal("1000.00"), moneda="MXN", estado="activa", creada_en=fecha)
        db.add_all([c1, c2])
        db.flush()
        movs = [
            ("deposito", "Depósito de nómina (demo)", "10000.00", "10000.00", 40),
            ("compra", "Compra supermercado demo", "-1000.00", "9000.00", 20),
            ("pago", "Pago de luz demo", "-500.00", "8500.00", 5),
        ]
        for i, (tipo, concepto, monto, saldo, dias) in enumerate(movs):
            db.add(Movimiento(cuenta_id=c1.id, tipo=tipo, concepto=concepto, monto=Decimal(monto),
                              saldo_resultante=Decimal(saldo), referencia=f"MOV-DEMO-TEST-{i:04d}",
                              fecha=fecha - timedelta(days=dias)))
        db.add(Movimiento(cuenta_id=c2.id, tipo="deposito", concepto="Apertura demo", monto=Decimal("1000.00"),
                          saldo_resultante=Decimal("1000.00"), referencia="MOV-DEMO-TEST-9999", fecha=fecha))
        db.commit()
    finally:
        db.close()


@pytest.fixture(autouse=True)
def bd_limpia():
    """Recrea la BD y los datos base antes de cada prueba; reinicia el rate limit."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    _cargar_datos_base()
    limiter.reset()
    yield


@pytest.fixture(autouse=True)
def buro_por_defecto(monkeypatch):
    """Por defecto el buró ficticio vale 700 (aprobable sin descuento) para pruebas deterministas."""
    monkeypatch.setattr("app.services.evaluacion.calcular_puntaje_buro", lambda folio: 700)


@pytest.fixture
def fijar_buro(monkeypatch):
    """Permite fijar el puntaje de buró dentro de una prueba: ``fijar_buro(550)``."""

    def _fijar(valor: int) -> None:
        monkeypatch.setattr("app.services.evaluacion.calcular_puntaje_buro", lambda folio: valor)

    return _fijar


@pytest.fixture
def client():
    """Cliente HTTP de pruebas (ejecuta el lifespan de la app)."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db():
    """Sesión directa a la BD de pruebas para preparar escenarios."""
    sesion = SessionLocal()
    try:
        yield sesion
    finally:
        sesion.close()


def _headers(usuario_id: int, rol: str) -> dict[str, str]:
    token, _ = crear_token(usuario_id, rol)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def h_admin():
    return _headers(ADMIN_ID, "admin")


@pytest.fixture
def h_valuador():
    return _headers(VALUADOR_ID, "valuador")


@pytest.fixture
def h_valuador2():
    return _headers(VALUADOR2_ID, "valuador")


@pytest.fixture
def h_analista():
    return _headers(ANALISTA_ID, "analista")


@pytest.fixture
def h_cliente():
    return _headers(CLIENTE_ID, "cliente")


@pytest.fixture
def h_cliente2():
    return _headers(CLIENTE2_ID, "cliente")
