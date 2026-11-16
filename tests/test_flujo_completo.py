"""Flujos completos de punta a punta usando login real."""

from __future__ import annotations

from datetime import timedelta

from app.models.solicitud import Solicitud
from tests.conftest import CUENTA_CLIENTE_ID, PASSWORD
from tests.helpers import (
    API,
    DOCS_HIPOTECA,
    DOCS_PRESTAMO,
    INMUEBLE_OK,
    SOLICITANTE_OK,
    crear_prestamo,
    entregar_docs,
    error_code,
    ok_data,
    prestamo_listo,
    solicitante,
)


def _login(client, email: str) -> dict[str, str]:
    data = ok_data(client.post(f"{API}/auth/login", json={"email": email, "password": PASSWORD}))
    return {"Authorization": f"Bearer {data['accessToken']}"}


def test_flujo_hipoteca_completo(client):
    h = _login(client, "cliente1@demo-banco.test")

    # 1. Crear solicitud
    s = ok_data(client.post(f"{API}/solicitudes", json={"productoId": 4, "montoSolicitado": 1800000,
                                                         "plazoMeses": 240, "valorInmueble": 2500000}, headers=h), 201)
    sid = s["id"]
    assert s["estado"] == "borrador" and s["enganche"] == 700000

    # 2. Datos del solicitante
    ok_data(client.put(f"{API}/solicitudes/{sid}/solicitante", json=SOLICITANTE_OK, headers=h))

    # 3. Documentos
    entregar_docs(client, h, sid, DOCS_HIPOTECA)
    assert ok_data(client.get(f"{API}/solicitudes/{sid}", headers=h))["estado"] == "borrador"

    # 4. Inmueble → avance automático
    r = client.put(f"{API}/solicitudes/{sid}/inmueble", json=INMUEBLE_OK, headers=h)
    assert "datos_completos" in r.json()["message"]

    # 5. Avalúo automático
    avaluo = ok_data(client.post(f"{API}/solicitudes/{sid}/avaluo", headers=h), 201)
    assert avaluo["estado"] == "completado"

    # 6. Análisis
    analizada = ok_data(client.post(f"{API}/solicitudes/{sid}/analisis", headers=h))
    assert analizada["estado"] == "aprobada", analizada["motivoResolucion"]

    # 7. Oferta
    oferta = ok_data(client.get(f"{API}/solicitudes/{sid}/oferta", headers=h))
    assert oferta["leyenda"] == "OFERTA DEMOSTRATIVA - NO ES UNA OFERTA REAL"
    assert oferta["monto"] == 1800000 and oferta["plazoMeses"] == 240 and oferta["vigente"] is True
    assert oferta["totalPagar"] > oferta["monto"] and oferta["catDemo"] > oferta["tasaAnual"]
    assert oferta["engancheRequerido"] == 700000

    # 8. Aceptar
    assert ok_data(client.post(f"{API}/solicitudes/{sid}/oferta/aceptar", headers=h))["estado"] == "oferta_aceptada"

    # 9. Formalizar
    formal = ok_data(client.post(f"{API}/solicitudes/{sid}/formalizar", headers=h))
    assert formal["estado"] == "formalizada" and formal["formalizadaEn"]

    # 10. Amortización
    tabla = ok_data(client.get(f"{API}/solicitudes/{sid}/amortizacion", headers=h))
    assert len(tabla["tabla"]) == 240 and tabla["tabla"][-1]["saldo"] == 0
    assert tabla["tabla"][0]["fechaPago"]

    estados = [x["estadoNuevo"] for x in ok_data(client.get(f"{API}/solicitudes/{sid}/historial", headers=h))]
    assert estados == ["borrador", "datos_completos", "en_avaluo", "avaluo_completado", "en_analisis", "aprobada",
                       "oferta_aceptada", "formalizada"]


def test_flujo_prestamo_completo_deposita_en_cuenta(client):
    h = _login(client, "cliente1@demo-banco.test")
    saldo_inicial = ok_data(client.get(f"{API}/cuentas/{CUENTA_CLIENTE_ID}", headers=h))["saldo"]
    sid = crear_prestamo(client, h, monto=80000, plazo=24)["id"]
    ok_data(client.put(f"{API}/solicitudes/{sid}/solicitante", json=SOLICITANTE_OK, headers=h))
    entregar_docs(client, h, sid, DOCS_PRESTAMO)
    assert ok_data(client.post(f"{API}/solicitudes/{sid}/analisis", headers=h))["estado"] == "aprobada"
    ok_data(client.post(f"{API}/solicitudes/{sid}/oferta/aceptar", headers=h))
    ok_data(client.post(f"{API}/solicitudes/{sid}/formalizar", headers=h))
    cuenta = ok_data(client.get(f"{API}/cuentas/{CUENTA_CLIENTE_ID}", headers=h))
    assert cuenta["saldo"] == saldo_inicial + 80000
    movs = ok_data(client.get(f"{API}/cuentas/{CUENTA_CLIENTE_ID}/movimientos?limit=1", headers=h))
    assert movs[0]["monto"] == 80000 and "Disposición" in movs[0]["concepto"]
    tabla = ok_data(client.get(f"{API}/solicitudes/{sid}/amortizacion", headers=h))
    assert len(tabla["tabla"]) == 24 and tabla["tabla"][-1]["saldo"] == 0


def test_flujo_rechazado(client, fijar_buro):
    fijar_buro(520)
    h = _login(client, "cliente2@demo-banco.test")
    sid = prestamo_listo(client, h)
    data = ok_data(client.post(f"{API}/solicitudes/{sid}/analisis", headers=h))
    assert data["estado"] == "rechazada" and data["puntajeBuro"] == 520
    assert error_code(client.get(f"{API}/solicitudes/{sid}/oferta", headers=h), 400) == "OFERTA_NO_DISPONIBLE"
    assert error_code(client.post(f"{API}/solicitudes/{sid}/cancelar", headers=h), 400) == "TRANSICION_INVALIDA"


def test_flujo_condicionado_aceptado(client):
    h = _login(client, "cliente1@demo-banco.test")
    datos = solicitante(ingresoMensual=12000, otrosIngresos=0, deudasMensuales=0)
    sid = prestamo_listo(client, h, datos_solicitante=datos, monto=100000, plazo=24)
    data = ok_data(client.post(f"{API}/solicitudes/{sid}/analisis", headers=h))
    assert data["estado"] == "condicionada"
    oferta = ok_data(client.get(f"{API}/solicitudes/{sid}/oferta", headers=h))
    assert oferta["condicionada"] is True and oferta["monto"] < 100000 and oferta["condiciones"]
    ok_data(client.post(f"{API}/solicitudes/{sid}/oferta/aceptar", headers=h))
    formal = ok_data(client.post(f"{API}/solicitudes/{sid}/formalizar", headers=h))
    assert formal["montoAprobado"] == oferta["monto"]


def test_flujo_oferta_rechazada(client):
    h = _login(client, "cliente1@demo-banco.test")
    sid = prestamo_listo(client, h)
    ok_data(client.post(f"{API}/solicitudes/{sid}/analisis", headers=h))
    data = ok_data(client.post(f"{API}/solicitudes/{sid}/oferta/rechazar", json={"motivo": "Tasa alta"}, headers=h))
    assert data["estado"] == "oferta_rechazada"
    assert error_code(client.post(f"{API}/solicitudes/{sid}/oferta/aceptar", headers=h), 400) == "TRANSICION_INVALIDA"


def test_oferta_vencida(client, db):
    h = _login(client, "cliente1@demo-banco.test")
    sid = prestamo_listo(client, h)
    ok_data(client.post(f"{API}/solicitudes/{sid}/analisis", headers=h))
    solicitud = db.get(Solicitud, sid)
    solicitud.resuelta_en = solicitud.resuelta_en - timedelta(days=16)
    db.commit()
    assert ok_data(client.get(f"{API}/solicitudes/{sid}/oferta", headers=h))["vigente"] is False
    assert error_code(client.post(f"{API}/solicitudes/{sid}/oferta/aceptar", headers=h), 400) == "OFERTA_VENCIDA"


def test_cliente_no_ve_recursos_de_otro(client):
    h1 = _login(client, "cliente1@demo-banco.test")
    h2 = _login(client, "cliente2@demo-banco.test")
    sid = crear_prestamo(client, h1)["id"]
    for ruta in (f"/solicitudes/{sid}", f"/solicitudes/{sid}/historial", f"/solicitudes/{sid}/documentos",
                 f"/solicitudes/{sid}/oferta", f"/cuentas/{CUENTA_CLIENTE_ID}",
                 f"/cuentas/{CUENTA_CLIENTE_ID}/movimientos"):
        assert error_code(client.get(f"{API}{ruta}", headers=h2), 403) == "ACCESO_DENEGADO", ruta
    assert ok_data(client.get(f"{API}/solicitudes", headers=h2)) == []
