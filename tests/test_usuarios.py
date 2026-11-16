"""Pruebas de registro, perfil y administración de usuarios."""

from __future__ import annotations

import pytest

from tests.conftest import ADMIN_ID, CLIENTE_ID, PASSWORD
from tests.helpers import API, error_code, ok_data

REGISTRO = {
    "nombre": "Laura",
    "apellidos": "Martínez Ruiz",
    "email": "laura@demo-banco.test",
    "password": "Segura2026",
    "telefono": "5511223344",
}


# --- Registro --------------------------------------------------------------------

def test_registro_exitoso_crea_cuenta(client):
    data = ok_data(client.post(f"{API}/usuarios/registro", json=REGISTRO), 201)
    assert data["usuario"]["rol"] == "cliente"
    assert data["usuario"]["codigo"].startswith("USR-DEMO-")
    assert "password" not in str(data["usuario"]).lower()
    cuenta = data["cuenta"]
    assert cuenta["tipo"] == "debito" and cuenta["moneda"] == "MXN"
    assert cuenta["numeroEnmascarado"].startswith("****") and len(cuenta["numeroEnmascarado"]) == 8
    assert 1000 <= cuenta["saldo"] <= 50000
    login = client.post(f"{API}/auth/login", json={"email": REGISTRO["email"], "password": REGISTRO["password"]})
    ok_data(login)


def test_registro_acepta_snake_case(client):
    datos = dict(REGISTRO, email="snake@demo-banco.test")
    ok_data(client.post(f"{API}/usuarios/registro", json=datos), 201)


def test_registro_email_duplicado_409(client):
    r = client.post(f"{API}/usuarios/registro", json=dict(REGISTRO, email="cliente1@demo-banco.test"))
    assert error_code(r, 409) == "EMAIL_REGISTRADO"


@pytest.mark.parametrize(
    "password,mensaje",
    [("Ab1", "al menos 8"), ("minuscula123", "mayúscula"), ("SinNumeros", "número")],
)
def test_registro_password_debil_422(client, password, mensaje):
    r = client.post(f"{API}/usuarios/registro", json=dict(REGISTRO, password=password))
    assert error_code(r, 422) == "ERROR_VALIDACION"
    detalle = r.json()["error"]["details"][0]
    assert detalle["campo"] == "password" and mensaje in detalle["mensaje"]


def test_registro_validacion_campos(client):
    r = client.post(f"{API}/usuarios/registro", json={"email": "x"})
    assert error_code(r, 422) == "ERROR_VALIDACION"
    campos = {d["campo"] for d in r.json()["error"]["details"]}
    assert {"nombre", "apellidos", "email", "password"} <= campos


# --- Perfil ------------------------------------------------------------------------

def test_perfil_exitoso(client, h_cliente):
    data = ok_data(client.get(f"{API}/usuarios/perfil", headers=h_cliente))
    assert data["id"] == CLIENTE_ID


def test_actualizar_perfil(client, h_cliente):
    data = ok_data(client.patch(f"{API}/usuarios/perfil", json={"telefono": "5599887766", "nombre": "Carla María"},
                                headers=h_cliente))
    assert data["telefono"] == "5599887766" and data["nombre"] == "Carla María"
    assert data["apellidos"] == "Cliente Demo"


def test_actualizar_perfil_sin_campos_400(client, h_cliente):
    assert error_code(client.patch(f"{API}/usuarios/perfil", json={}, headers=h_cliente), 400) == "SIN_CAMBIOS"


def test_actualizar_perfil_validacion(client, h_cliente):
    r = client.patch(f"{API}/usuarios/perfil", json={"telefono": "12ab"}, headers=h_cliente)
    assert error_code(r, 422) == "ERROR_VALIDACION"


def test_cambiar_password_exitoso(client, h_cliente):
    r = client.patch(f"{API}/usuarios/perfil/password",
                     json={"passwordActual": PASSWORD, "passwordNueva": "NuevaClave2026"}, headers=h_cliente)
    ok_data(r)
    assert client.post(f"{API}/auth/login", json={"email": "cliente1@demo-banco.test",
                                                  "password": "NuevaClave2026"}).status_code == 200
    assert client.post(f"{API}/auth/login", json={"email": "cliente1@demo-banco.test",
                                                  "password": PASSWORD}).status_code == 401


def test_cambiar_password_actual_incorrecta(client, h_cliente):
    r = client.patch(f"{API}/usuarios/perfil/password",
                     json={"passwordActual": "Otra1234", "passwordNueva": "NuevaClave2026"}, headers=h_cliente)
    assert error_code(r, 400) == "PASSWORD_INCORRECTA"


def test_cambiar_password_repetida(client, h_cliente):
    r = client.patch(f"{API}/usuarios/perfil/password",
                     json={"passwordActual": PASSWORD, "passwordNueva": PASSWORD}, headers=h_cliente)
    assert error_code(r, 400) == "PASSWORD_REPETIDA"


def test_cambiar_password_debil(client, h_cliente):
    r = client.patch(f"{API}/usuarios/perfil/password",
                     json={"passwordActual": PASSWORD, "passwordNueva": "debil"}, headers=h_cliente)
    assert error_code(r, 422) == "ERROR_VALIDACION"


# --- Admin: usuarios ---------------------------------------------------------------

def test_admin_listar_usuarios(client, h_admin):
    r = client.get(f"{API}/admin/usuarios?limit=3", headers=h_admin)
    cuerpo = r.json()
    assert r.status_code == 200 and len(cuerpo["data"]) == 3
    assert cuerpo["meta"] == {"page": 1, "limit": 3, "total": 7}


def test_admin_listar_filtros(client, h_admin):
    data = ok_data(client.get(f"{API}/admin/usuarios?rol=cliente&activo=true", headers=h_admin))
    assert {u["email"] for u in data} == {"cliente1@demo-banco.test", "cliente2@demo-banco.test"}
    data = ok_data(client.get(f"{API}/admin/usuarios?busqueda=valuador", headers=h_admin))
    assert all(u["rol"] == "valuador" for u in data) and len(data) == 2


def test_admin_listar_paginacion_invalida(client, h_admin):
    assert error_code(client.get(f"{API}/admin/usuarios?limit=101", headers=h_admin), 422) == "ERROR_VALIDACION"
    assert error_code(client.get(f"{API}/admin/usuarios?page=0", headers=h_admin), 422) == "ERROR_VALIDACION"


@pytest.mark.parametrize("fixture", ["h_cliente", "h_analista", "h_valuador"])
def test_admin_endpoints_requieren_admin(client, request, fixture):
    h = request.getfixturevalue(fixture)
    for metodo, ruta in [("get", "/admin/usuarios"), ("get", "/admin/usuarios/1"), ("get", "/admin/estadisticas"),
                         ("patch", "/admin/usuarios/1/estado"), ("post", "/admin/usuarios")]:
        r = client.request(metodo.upper(), f"{API}{ruta}", json={"activo": False}, headers=h)
        assert error_code(r, 403) == "PERMISO_INSUFICIENTE"


def test_admin_obtener_usuario(client, h_admin):
    assert ok_data(client.get(f"{API}/admin/usuarios/{CLIENTE_ID}", headers=h_admin))["rol"] == "cliente"


def test_admin_obtener_usuario_404(client, h_admin):
    assert error_code(client.get(f"{API}/admin/usuarios/999", headers=h_admin), 404) == "USUARIO_NO_ENCONTRADO"


def test_admin_crear_personal(client, h_admin):
    datos = {"nombre": "Jorge", "apellidos": "Valdez", "email": "valuador9@demo-banco.test",
             "password": "Valuador2026", "rol": "valuador"}
    data = ok_data(client.post(f"{API}/admin/usuarios", json=datos, headers=h_admin), 201)
    assert data["rol"] == "valuador"
    ok_data(client.post(f"{API}/auth/login", json={"email": datos["email"], "password": datos["password"]}))


def test_admin_crear_personal_validacion(client, h_admin):
    datos = {"nombre": "Jorge", "apellidos": "Valdez", "email": "x@demo-banco.test",
             "password": "Valuador2026", "rol": "cliente"}
    assert error_code(client.post(f"{API}/admin/usuarios", json=datos, headers=h_admin), 422) == "ERROR_VALIDACION"


def test_admin_crear_personal_email_duplicado(client, h_admin):
    datos = {"nombre": "Jorge", "apellidos": "Valdez", "email": "analista1@demo-banco.test",
             "password": "Valuador2026", "rol": "analista"}
    assert error_code(client.post(f"{API}/admin/usuarios", json=datos, headers=h_admin), 409) == "EMAIL_REGISTRADO"


def test_admin_desactivar_usuario_impide_login(client, h_admin):
    data = ok_data(client.patch(f"{API}/admin/usuarios/{CLIENTE_ID}/estado", json={"activo": False}, headers=h_admin))
    assert data["activo"] is False
    r = client.post(f"{API}/auth/login", json={"email": "cliente1@demo-banco.test", "password": PASSWORD})
    assert error_code(r, 403) == "USUARIO_INACTIVO"
    ok_data(client.patch(f"{API}/admin/usuarios/{CLIENTE_ID}/estado", json={"activo": True}, headers=h_admin))


def test_admin_no_puede_desactivarse(client, h_admin):
    r = client.patch(f"{API}/admin/usuarios/{ADMIN_ID}/estado", json={"activo": False}, headers=h_admin)
    assert error_code(r, 400) == "OPERACION_NO_PERMITIDA"


def test_admin_estado_validacion_y_404(client, h_admin):
    assert error_code(client.patch(f"{API}/admin/usuarios/4/estado", json={}, headers=h_admin), 422) == "ERROR_VALIDACION"
    r = client.patch(f"{API}/admin/usuarios/999/estado", json={"activo": True}, headers=h_admin)
    assert error_code(r, 404) == "USUARIO_NO_ENCONTRADO"


def test_admin_estadisticas(client, h_admin, h_cliente):
    from tests.helpers import crear_prestamo

    crear_prestamo(client, h_cliente)
    data = ok_data(client.get(f"{API}/admin/estadisticas", headers=h_admin))
    assert data["totalSolicitudes"] == 1
    assert data["solicitudesPorEstado"]["borrador"] == 1
    assert data["solicitudesPorTipo"] == {"prestamo": 1, "hipoteca": 0}
    assert data["tasaAprobacionPct"] == 0 and data["montoTotalAprobado"] == 0
    assert data["usuariosPorRol"]["cliente"] == 3
