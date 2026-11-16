"""Pruebas de los simuladores públicos."""

from __future__ import annotations

from tests.helpers import API, H_FIJA, H_PLUS, P_BASICO, P_PLUS, error_code, ok_data


def test_simular_prestamo_valor_conocido(client):
    data = ok_data(client.post(f"{API}/simuladores/prestamo",
                               json={"monto": 50000, "tasaAnual": 18.5, "plazoMeses": 24}))
    # Método francés: 50,000 a 18.5% anual en 24 meses = 2,508.30 (ver test_finanzas)
    assert data["mensualidad"] == 2508.30
    assert data["leyenda"] == "SIMULACIÓN DEMOSTRATIVA - NO ES UNA OFERTA REAL"
    assert round(data["totalPagar"] - data["monto"], 2) == data["totalIntereses"]
    assert data["catDemo"] > data["tasaAnual"]


def test_simular_prestamo_con_producto(client):
    data = ok_data(client.post(f"{API}/simuladores/prestamo",
                               json={"monto": 80000, "productoId": P_PLUS, "plazoMeses": 36}))
    assert data["tasaAnual"] == 18.5 and data["productoNombre"] == "Préstamo Personal Demo Plus"


def test_simular_prestamo_reglas_producto(client):
    r = client.post(f"{API}/simuladores/prestamo", json={"monto": 5000, "productoId": P_BASICO, "plazoMeses": 12})
    assert error_code(r, 400) == "MONTO_FUERA_DE_RANGO"
    r = client.post(f"{API}/simuladores/prestamo", json={"monto": 50000, "productoId": P_BASICO, "plazoMeses": 60})
    assert error_code(r, 400) == "PLAZO_NO_PERMITIDO"
    r = client.post(f"{API}/simuladores/prestamo", json={"monto": 600000, "productoId": H_FIJA, "plazoMeses": 120})
    assert error_code(r, 400) == "TIPO_PRODUCTO_INVALIDO"
    r = client.post(f"{API}/simuladores/prestamo", json={"monto": 50000, "productoId": 999, "plazoMeses": 12})
    assert error_code(r, 404) == "PRODUCTO_NO_ENCONTRADO"


def test_simular_prestamo_validacion(client):
    r = client.post(f"{API}/simuladores/prestamo", json={"monto": 50000, "plazoMeses": 12})
    assert error_code(r, 422) == "ERROR_VALIDACION"
    assert "tasaAnual o productoId" in r.json()["error"]["details"][0]["mensaje"]
    r = client.post(f"{API}/simuladores/prestamo", json={"monto": -1, "tasaAnual": 10, "plazoMeses": 0})
    campos = {d["campo"] for d in r.json()["error"]["details"]}
    assert r.status_code == 422 and {"monto", "plazoMeses"} <= campos


def test_simular_hipoteca_cumple_enganche(client):
    data = ok_data(client.post(f"{API}/simuladores/hipoteca",
                               json={"valorInmueble": 2500000, "enganche": 500000, "tasaAnual": 10.5,
                                     "plazoMeses": 240}))
    assert data["monto"] == 2000000 and data["enganchePct"] == 20.0
    assert data["cumpleEngancheMinimo"] is True and data["engancheMinPct"] == 10.0
    assert data["mensualidad"] > 0


def test_simular_hipoteca_enganche_insuficiente_producto(client):
    data = ok_data(client.post(f"{API}/simuladores/hipoteca",
                               json={"valorInmueble": 2500000, "enganche": 300000, "productoId": H_PLUS,
                                     "plazoMeses": 240}))
    assert data["engancheMinPct"] == 20.0 and data["engancheMinimo"] == 500000
    assert data["cumpleEngancheMinimo"] is False and "insuficiente" in data["mensajeEnganche"]


def test_simular_hipoteca_validacion(client):
    r = client.post(f"{API}/simuladores/hipoteca",
                    json={"valorInmueble": 1000000, "enganche": 1000000, "tasaAnual": 10, "plazoMeses": 120})
    assert error_code(r, 422) == "ERROR_VALIDACION"


def test_simular_hipoteca_producto_inexistente(client):
    r = client.post(f"{API}/simuladores/hipoteca",
                    json={"valorInmueble": 2000000, "enganche": 400000, "productoId": 999, "plazoMeses": 120})
    assert error_code(r, 404) == "PRODUCTO_NO_ENCONTRADO"


def test_amortizacion(client):
    data = ok_data(client.post(f"{API}/simuladores/amortizacion",
                               json={"monto": 50000, "tasaAnual": 18.5, "plazoMeses": 12}))
    tabla = data["tabla"]
    assert len(tabla) == 12 and tabla[0]["numero"] == 1
    assert tabla[-1]["saldo"] == 0.0
    assert round(sum(f["capital"] for f in tabla), 2) == 50000
    assert set(tabla[0]) >= {"numero", "pago", "capital", "interes", "saldo"}


def test_amortizacion_tasa_cero(client):
    data = ok_data(client.post(f"{API}/simuladores/amortizacion",
                               json={"monto": 1200, "tasaAnual": 0, "plazoMeses": 12}))
    assert data["mensualidad"] == 100 and data["totalIntereses"] == 0
    assert all(f["interes"] == 0 for f in data["tabla"])


def test_amortizacion_validacion(client):
    r = client.post(f"{API}/simuladores/amortizacion", json={"monto": 1000, "tasaAnual": 10, "plazoMeses": 0})
    assert error_code(r, 422) == "ERROR_VALIDACION"
    r = client.post(f"{API}/simuladores/amortizacion", json={"monto": 1000.123, "tasaAnual": 10, "plazoMeses": 12})
    assert error_code(r, 422) == "ERROR_VALIDACION"
