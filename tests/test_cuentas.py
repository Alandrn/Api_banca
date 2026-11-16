"""Pruebas de consulta de cuentas y movimientos."""

from __future__ import annotations

from datetime import date, timedelta

from tests.conftest import CUENTA_CLIENTE2_ID, CUENTA_CLIENTE_ID
from tests.helpers import API, error_code, ok_data


def test_listar_cuentas_propias(client, h_cliente):
    data = ok_data(client.get(f"{API}/cuentas", headers=h_cliente))
    assert len(data) == 1 and data[0]["id"] == CUENTA_CLIENTE_ID
    assert data[0]["numeroEnmascarado"] == "****7712" and data[0]["saldo"] == 8500


def test_numero_completo_nunca_se_expone(client, h_cliente):
    r = client.get(f"{API}/cuentas/{CUENTA_CLIENTE_ID}", headers=h_cliente)
    assert "1111-2222" not in r.text and "DEMO-1111" not in r.text
    assert "numero" not in r.json()["data"]


def test_cuentas_permisos(client, h_analista, h_valuador):
    assert error_code(client.get(f"{API}/cuentas", headers=h_analista), 403) == "PERMISO_INSUFICIENTE"
    assert error_code(client.get(f"{API}/cuentas/1", headers=h_valuador), 403) == "PERMISO_INSUFICIENTE"


def test_admin_ve_todas_las_cuentas(client, h_admin):
    assert len(ok_data(client.get(f"{API}/cuentas", headers=h_admin))) == 2


def test_detalle_cuenta(client, h_cliente):
    data = ok_data(client.get(f"{API}/cuentas/{CUENTA_CLIENTE_ID}", headers=h_cliente))
    assert data["tipo"] == "debito" and data["estado"] == "activa" and data["moneda"] == "MXN"


def test_detalle_cuenta_de_otro_cliente_403(client, h_cliente):
    assert error_code(client.get(f"{API}/cuentas/{CUENTA_CLIENTE2_ID}", headers=h_cliente), 403) == "ACCESO_DENEGADO"
    r = client.get(f"{API}/cuentas/{CUENTA_CLIENTE2_ID}/movimientos", headers=h_cliente)
    assert error_code(r, 403) == "ACCESO_DENEGADO"


def test_detalle_cuenta_404_y_422(client, h_cliente):
    assert error_code(client.get(f"{API}/cuentas/999", headers=h_cliente), 404) == "CUENTA_NO_ENCONTRADA"
    assert error_code(client.get(f"{API}/cuentas/abc", headers=h_cliente), 422) == "ERROR_VALIDACION"
    assert error_code(client.get(f"{API}/cuentas/999/movimientos", headers=h_cliente), 404) == "CUENTA_NO_ENCONTRADA"


def test_movimientos_paginados_orden_desc(client, h_cliente):
    r = client.get(f"{API}/cuentas/{CUENTA_CLIENTE_ID}/movimientos?limit=2", headers=h_cliente)
    cuerpo = r.json()
    assert r.status_code == 200 and cuerpo["meta"] == {"page": 1, "limit": 2, "total": 3}
    fechas = [m["fecha"] for m in cuerpo["data"]]
    assert fechas == sorted(fechas, reverse=True)
    assert cuerpo["data"][0]["saldoResultante"] == 8500 and cuerpo["data"][0]["monto"] == -500


def test_movimientos_filtros(client, h_cliente):
    url = f"{API}/cuentas/{CUENTA_CLIENTE_ID}/movimientos"
    data = ok_data(client.get(f"{url}?tipo=compra", headers=h_cliente))
    assert len(data) == 1 and data[0]["tipo"] == "compra"
    desde = (date.today() - timedelta(days=10)).isoformat()
    data = ok_data(client.get(f"{url}?desde={desde}", headers=h_cliente))
    assert [m["tipo"] for m in data] == ["pago"]
    hasta = (date.today() - timedelta(days=30)).isoformat()
    data = ok_data(client.get(f"{url}?hasta={hasta}", headers=h_cliente))
    assert [m["tipo"] for m in data] == ["deposito"]


def test_movimientos_rango_invalido(client, h_cliente):
    url = f"{API}/cuentas/{CUENTA_CLIENTE_ID}/movimientos?desde=2026-06-01&hasta=2026-01-01"
    assert error_code(client.get(url, headers=h_cliente), 400) == "RANGO_FECHAS_INVALIDO"


def test_movimientos_validacion(client, h_cliente):
    url = f"{API}/cuentas/{CUENTA_CLIENTE_ID}/movimientos"
    assert error_code(client.get(f"{url}?desde=01-01-2026", headers=h_cliente), 422) == "ERROR_VALIDACION"
    assert error_code(client.get(f"{url}?tipo=regalo", headers=h_cliente), 422) == "ERROR_VALIDACION"
    assert error_code(client.get(f"{url}?limit=500", headers=h_cliente), 422) == "ERROR_VALIDACION"
