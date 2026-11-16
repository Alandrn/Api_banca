"""Pruebas de autenticación, sistema, formato de errores y seguridad transversal."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from app.core.config import settings
from tests.conftest import INACTIVO_ID, PASSWORD
from tests.helpers import API, error_code, ok_data


# --- Sistema -----------------------------------------------------------------

def test_health_ok(client):
    data = ok_data(client.get(f"{API}/health"))
    assert data["estado"] == "ok" and data["baseDatos"] == "ok"


def test_ruta_inexistente_formato_estandar(client):
    assert error_code(client.get(f"{API}/no-existe"), 404) == "RUTA_NO_ENCONTRADA"


def test_metodo_no_permitido(client):
    assert error_code(client.delete(f"{API}/health"), 405) == "METODO_NO_PERMITIDO"


def test_json_mal_formado_422(client):
    r = client.post(f"{API}/auth/login", content="{no es json", headers={"Content-Type": "application/json"})
    assert error_code(r, 422) == "ERROR_VALIDACION"
    assert r.json()["error"]["details"][0]["mensaje"] == "El cuerpo no es un JSON válido"


def test_error_interno_500_sin_traza(monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import app

    def _explota(*args, **kwargs):
        raise RuntimeError("detalle interno secreto")

    monkeypatch.setattr("app.services.productos.listar", _explota)
    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get(f"{API}/productos")
    assert error_code(r, 500) == "ERROR_INTERNO"
    assert "secreto" not in r.text


def test_red_no_permitida(client, monkeypatch):
    monkeypatch.setattr(settings, "ALLOWED_NETWORKS", "10.0.0.0/8")
    assert error_code(client.get(f"{API}/health"), 403) == "RED_NO_PERMITIDA"
    monkeypatch.setattr(settings, "ALLOWED_NETWORKS", "")
    ok_data(client.get(f"{API}/health"))


def test_docs_disponibles(client):
    assert client.get("/docs").status_code == 200
    esquema = client.get("/openapi.json").json()
    assert "/api/v1/solicitudes" in esquema["paths"]


def test_cabecera_demo(client):
    assert client.get(f"{API}/health").headers["X-Demo"] == "true"


# --- Login ---------------------------------------------------------------------

def test_login_exitoso(client):
    data = ok_data(client.post(f"{API}/auth/login", json={"email": "cliente1@demo-banco.test", "password": PASSWORD}))
    assert data["accessToken"] and data["tokenType"] == "bearer" and data["expiresIn"] == 3600
    assert data["usuario"]["rol"] == "cliente"
    assert "passwordHash" not in data["usuario"] and "password_hash" not in str(data)
    payload = jwt.decode(data["accessToken"], settings.JWT_SECRET, algorithms=["HS256"])
    assert payload["sub"] == str(data["usuario"]["id"]) and payload["rol"] == "cliente"


def test_login_email_mayusculas(client):
    ok_data(client.post(f"{API}/auth/login", json={"email": "CLIENTE1@demo-banco.test", "password": PASSWORD}))


def test_login_password_incorrecta(client):
    r = client.post(f"{API}/auth/login", json={"email": "cliente1@demo-banco.test", "password": "Mala1234"})
    assert error_code(r, 401) == "CREDENCIALES_INVALIDAS"


def test_login_usuario_inexistente(client):
    r = client.post(f"{API}/auth/login", json={"email": "nadie@demo-banco.test", "password": PASSWORD})
    assert error_code(r, 401) == "CREDENCIALES_INVALIDAS"


def test_login_usuario_inactivo(client):
    r = client.post(f"{API}/auth/login", json={"email": "inactivo@demo-banco.test", "password": PASSWORD})
    assert error_code(r, 403) == "USUARIO_INACTIVO"


def test_login_validacion(client):
    r = client.post(f"{API}/auth/login", json={"email": "no-es-correo"})
    assert error_code(r, 422) == "ERROR_VALIDACION"
    campos = {d["campo"] for d in r.json()["error"]["details"]}
    assert {"email", "password"} <= campos


def test_login_rate_limit_429(client):
    cuerpo = {"email": "cliente1@demo-banco.test", "password": "Incorrecta1"}
    for _ in range(5):
        assert client.post(f"{API}/auth/login", json=cuerpo).status_code == 401
    r = client.post(f"{API}/auth/login", json=cuerpo)
    assert error_code(r, 429) == "LIMITE_PETICIONES_EXCEDIDO"


# --- /auth/me ------------------------------------------------------------------

def test_me_exitoso(client, h_cliente):
    assert ok_data(client.get(f"{API}/auth/me", headers=h_cliente))["email"] == "cliente1@demo-banco.test"


def test_me_sin_token(client):
    assert error_code(client.get(f"{API}/auth/me"), 401) == "NO_AUTENTICADO"


def test_me_token_invalido(client):
    r = client.get(f"{API}/auth/me", headers={"Authorization": "Bearer abc.def.ghi"})
    assert error_code(r, 401) == "TOKEN_INVALIDO"


def test_me_token_expirado(client):
    pasado = datetime.now(timezone.utc) - timedelta(minutes=5)
    token = jwt.encode({"sub": "4", "rol": "cliente", "exp": int(pasado.timestamp())}, settings.JWT_SECRET,
                       algorithm="HS256")
    r = client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert error_code(r, 401) == "TOKEN_EXPIRADO"


def test_me_usuario_inexistente(client):
    from app.core.security import crear_token

    token, _ = crear_token(9999, "cliente")
    r = client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert error_code(r, 401) == "TOKEN_INVALIDO"


def test_me_usuario_inactivo(client):
    from app.core.security import crear_token

    token, _ = crear_token(INACTIVO_ID, "cliente")
    r = client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert error_code(r, 403) == "USUARIO_INACTIVO"


# --- Todos los endpoints protegidos exigen token -------------------------------

PROTEGIDOS = [
    ("get", "/auth/me"),
    ("get", "/usuarios/perfil"),
    ("patch", "/usuarios/perfil"),
    ("patch", "/usuarios/perfil/password"),
    ("get", "/admin/usuarios"),
    ("get", "/admin/usuarios/1"),
    ("post", "/admin/usuarios"),
    ("patch", "/admin/usuarios/1/estado"),
    ("get", "/admin/estadisticas"),
    ("post", "/productos"),
    ("put", "/productos/1"),
    ("delete", "/productos/1"),
    ("post", "/solicitudes"),
    ("get", "/solicitudes"),
    ("get", "/solicitudes/1"),
    ("post", "/solicitudes/1/cancelar"),
    ("get", "/solicitudes/1/historial"),
    ("post", "/solicitudes/1/analisis"),
    ("patch", "/solicitudes/1/resolucion"),
    ("get", "/solicitudes/1/oferta"),
    ("post", "/solicitudes/1/oferta/aceptar"),
    ("post", "/solicitudes/1/oferta/rechazar"),
    ("post", "/solicitudes/1/formalizar"),
    ("get", "/solicitudes/1/amortizacion"),
    ("put", "/solicitudes/1/solicitante"),
    ("get", "/solicitudes/1/solicitante"),
    ("get", "/solicitudes/1/documentos"),
    ("post", "/solicitudes/1/documentos"),
    ("patch", "/solicitudes/1/documentos/1"),
    ("put", "/solicitudes/1/inmueble"),
    ("get", "/solicitudes/1/inmueble"),
    ("post", "/solicitudes/1/avaluo"),
    ("get", "/avaluos"),
    ("get", "/avaluos/1"),
    ("patch", "/avaluos/1/resultado"),
    ("get", "/cuentas"),
    ("get", "/cuentas/1"),
    ("get", "/cuentas/1/movimientos"),
]


@pytest.mark.parametrize("metodo,ruta", PROTEGIDOS)
def test_endpoints_protegidos_sin_token_401(client, metodo, ruta):
    r = client.request(metodo.upper(), f"{API}{ruta}", json={})
    assert r.status_code == 401, (metodo, ruta, r.text)
    assert r.json()["error"]["code"] == "NO_AUTENTICADO"
