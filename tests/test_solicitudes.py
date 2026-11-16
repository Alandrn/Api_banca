"""Pruebas de alta, consulta, cancelación e historial de solicitudes."""

from __future__ import annotations

import re

from tests.conftest import CLIENTE_ID
from tests.helpers import (
    API,
    DOCS_PRESTAMO,
    H_FIJA,
    H_PLUS,
    P_BASICO,
    P_PLUS,
    crear_hipoteca,
    crear_prestamo,
    error_code,
    ok_data,
)


def _post(client, h, **datos):
    return client.post(f"{API}/solicitudes", json=datos, headers=h)


# --- Alta ------------------------------------------------------------------------

def test_crear_prestamo(client, h_cliente):
    data = crear_prestamo(client, h_cliente)
    assert data["estado"] == "borrador" and data["tipo"] == "prestamo"
    assert re.fullmatch(r"SOL-DEMO-\d{4}-000001", data["folio"])
    assert data["usuarioId"] == CLIENTE_ID and data["montoSolicitado"] == 80000
    assert data["valorInmueble"] is None and data["enganche"] is None
    assert data["progreso"]["documentosPendientes"] == DOCS_PRESTAMO
    assert data["progreso"]["porcentaje"] == 0
    historial = ok_data(client.get(f"{API}/solicitudes/{data['id']}/historial", headers=h_cliente))
    assert len(historial) == 1 and historial[0]["estadoNuevo"] == "borrador" and historial[0]["estadoAnterior"] is None


def test_crear_hipoteca_calcula_enganche(client, h_cliente):
    data = crear_hipoteca(client, h_cliente, monto=2000000, valor=2500000)
    assert data["tipo"] == "hipoteca" and data["enganche"] == 500000 and data["valorInmueble"] == 2500000
    assert data["progreso"]["inmuebleRequerido"] is True


def test_crear_acepta_snake_case(client, h_cliente):
    r = client.post(f"{API}/solicitudes", json={"producto_id": P_PLUS, "monto_solicitado": 60000, "plazo_meses": 12},
                    headers=h_cliente)
    assert ok_data(r, 201)["plazoMeses"] == 12


def test_crear_permisos(client, h_analista, h_valuador):
    cuerpo = {"productoId": P_PLUS, "montoSolicitado": 60000, "plazoMeses": 12}
    for h in (h_analista, h_valuador):
        assert error_code(client.post(f"{API}/solicitudes", json=cuerpo, headers=h), 403) == "PERMISO_INSUFICIENTE"


def test_crear_validacion_422(client, h_cliente):
    r = _post(client, h_cliente, montoSolicitado=0, plazoMeses=12)
    assert error_code(r, 422) == "ERROR_VALIDACION"
    campos = {d["campo"] for d in r.json()["error"]["details"]}
    assert {"productoId", "montoSolicitado"} <= campos


def test_crear_producto_inexistente(client, h_cliente):
    r = _post(client, h_cliente, productoId=999, montoSolicitado=60000, plazoMeses=12)
    assert error_code(r, 404) == "PRODUCTO_NO_ENCONTRADO"


def test_crear_monto_y_plazo_fuera_de_producto(client, h_cliente):
    r = _post(client, h_cliente, productoId=P_BASICO, montoSolicitado=500000, plazoMeses=12)
    assert error_code(r, 400) == "MONTO_FUERA_DE_RANGO"
    r = _post(client, h_cliente, productoId=P_BASICO, montoSolicitado=50000, plazoMeses=18)
    assert error_code(r, 400) == "PLAZO_NO_PERMITIDO"


def test_crear_hipoteca_reglas(client, h_cliente):
    r = _post(client, h_cliente, productoId=H_FIJA, montoSolicitado=1000000, plazoMeses=240)
    assert error_code(r, 400) == "VALOR_INMUEBLE_REQUERIDO"
    r = _post(client, h_cliente, productoId=H_FIJA, montoSolicitado=1000000, plazoMeses=240, valorInmueble=1000000)
    assert error_code(r, 400) == "MONTO_EXCEDE_VALOR"
    r = _post(client, h_cliente, productoId=H_FIJA, montoSolicitado=950000, plazoMeses=240, valorInmueble=1000000)
    assert error_code(r, 400) == "ENGANCHE_INSUFICIENTE"
    r = _post(client, h_cliente, productoId=H_PLUS, montoSolicitado=1700000, plazoMeses=240, valorInmueble=2000000)
    assert error_code(r, 400) == "ENGANCHE_INSUFICIENTE"  # Plus exige 20%
    r = _post(client, h_cliente, productoId=H_FIJA, montoSolicitado=900000, plazoMeses=240, valorInmueble=1000000)
    assert ok_data(r, 201)["enganche"] == 100000  # exactamente 10%


def test_limite_tres_solicitudes_activas(client, h_cliente):
    ids = [crear_prestamo(client, h_cliente)["id"] for _ in range(3)]
    r = _post(client, h_cliente, productoId=P_PLUS, montoSolicitado=60000, plazoMeses=12)
    assert error_code(r, 400) == "LIMITE_SOLICITUDES"
    ok_data(client.post(f"{API}/solicitudes/{ids[0]}/cancelar", headers=h_cliente))
    crear_prestamo(client, h_cliente)


# --- Consulta --------------------------------------------------------------------

def test_listar_cliente_solo_las_suyas(client, h_cliente, h_cliente2):
    crear_prestamo(client, h_cliente)
    crear_prestamo(client, h_cliente2)
    r = client.get(f"{API}/solicitudes", headers=h_cliente)
    cuerpo = r.json()
    assert r.status_code == 200 and cuerpo["meta"]["total"] == 1
    assert all(s["usuarioId"] == CLIENTE_ID for s in cuerpo["data"])


def test_listar_analista_ve_todas_con_filtros(client, h_cliente, h_cliente2, h_analista):
    crear_prestamo(client, h_cliente)
    crear_hipoteca(client, h_cliente2)
    assert client.get(f"{API}/solicitudes", headers=h_analista).json()["meta"]["total"] == 2
    data = ok_data(client.get(f"{API}/solicitudes?tipo=hipoteca", headers=h_analista))
    assert len(data) == 1 and data[0]["tipo"] == "hipoteca"
    assert ok_data(client.get(f"{API}/solicitudes?estado=aprobada", headers=h_analista)) == []
    r = client.get(f"{API}/solicitudes?limit=1&page=2", headers=h_analista)
    assert r.json()["meta"] == {"page": 2, "limit": 1, "total": 2} and len(r.json()["data"]) == 1


def test_listar_validacion_y_permiso(client, h_analista, h_valuador):
    assert error_code(client.get(f"{API}/solicitudes?estado=xyz", headers=h_analista), 422) == "ERROR_VALIDACION"
    assert error_code(client.get(f"{API}/solicitudes", headers=h_valuador), 403) == "PERMISO_INSUFICIENTE"


def test_detalle(client, h_cliente, h_analista):
    sid = crear_prestamo(client, h_cliente)["id"]
    data = ok_data(client.get(f"{API}/solicitudes/{sid}", headers=h_cliente))
    assert data["producto"]["nombre"] == "Préstamo Personal Demo Plus"
    assert len(data["documentos"]) == 4 and all(d["estado"] == "pendiente" for d in data["documentos"])
    assert data["solicitante"] is None and data["progreso"]["editable"] is True
    assert "solicitante" in data["progreso"]["siguientePaso"]
    ok_data(client.get(f"{API}/solicitudes/{sid}", headers=h_analista))


def test_detalle_otro_cliente_403(client, h_cliente, h_cliente2, h_valuador):
    sid = crear_prestamo(client, h_cliente)["id"]
    assert error_code(client.get(f"{API}/solicitudes/{sid}", headers=h_cliente2), 403) == "ACCESO_DENEGADO"
    assert error_code(client.get(f"{API}/solicitudes/{sid}", headers=h_valuador), 403) == "ACCESO_DENEGADO"


def test_detalle_404(client, h_cliente):
    assert error_code(client.get(f"{API}/solicitudes/999", headers=h_cliente), 404) == "SOLICITUD_NO_ENCONTRADA"


# --- Cancelación e historial -----------------------------------------------------

def test_cancelar(client, h_cliente):
    sid = crear_prestamo(client, h_cliente)["id"]
    data = ok_data(client.post(f"{API}/solicitudes/{sid}/cancelar", json={"motivo": "Ya no lo necesito"},
                               headers=h_cliente))
    assert data["estado"] == "cancelada" and data["progreso"]["porcentaje"] == 100
    historial = ok_data(client.get(f"{API}/solicitudes/{sid}/historial", headers=h_cliente))
    assert historial[-1]["estadoNuevo"] == "cancelada" and historial[-1]["nota"] == "Ya no lo necesito"
    r = client.post(f"{API}/solicitudes/{sid}/cancelar", headers=h_cliente)
    assert error_code(r, 400) == "TRANSICION_INVALIDA"


def test_cancelar_permisos_y_404(client, h_cliente, h_cliente2, h_analista):
    sid = crear_prestamo(client, h_cliente)["id"]
    assert error_code(client.post(f"{API}/solicitudes/{sid}/cancelar", headers=h_cliente2), 403) == "ACCESO_DENEGADO"
    assert error_code(client.post(f"{API}/solicitudes/{sid}/cancelar", headers=h_analista), 403) == "PERMISO_INSUFICIENTE"
    assert error_code(client.post(f"{API}/solicitudes/999/cancelar", headers=h_cliente), 404) == "SOLICITUD_NO_ENCONTRADA"


def test_cancelar_validacion(client, h_cliente):
    sid = crear_prestamo(client, h_cliente)["id"]
    r = client.post(f"{API}/solicitudes/{sid}/cancelar", json={"motivo": "x" * 501}, headers=h_cliente)
    assert error_code(r, 422) == "ERROR_VALIDACION"


def test_historial_permisos_y_404(client, h_cliente, h_cliente2):
    sid = crear_prestamo(client, h_cliente)["id"]
    assert error_code(client.get(f"{API}/solicitudes/{sid}/historial", headers=h_cliente2), 403) == "ACCESO_DENEGADO"
    assert error_code(client.get(f"{API}/solicitudes/999/historial", headers=h_cliente), 404) == "SOLICITUD_NO_ENCONTRADA"


def test_admin_puede_operar(client, h_admin):
    data = crear_prestamo(client, h_admin)
    assert data["estado"] == "borrador"


# --- Oferta / formalización fuera de estado --------------------------------------

def test_oferta_y_formalizacion_fuera_de_estado(client, h_cliente):
    sid = crear_prestamo(client, h_cliente)["id"]
    assert error_code(client.get(f"{API}/solicitudes/{sid}/oferta", headers=h_cliente), 400) == "OFERTA_NO_DISPONIBLE"
    for accion in ("oferta/aceptar", "oferta/rechazar", "formalizar"):
        r = client.post(f"{API}/solicitudes/{sid}/{accion}", headers=h_cliente)
        assert error_code(r, 400) == "TRANSICION_INVALIDA", accion
    r = client.get(f"{API}/solicitudes/{sid}/amortizacion", headers=h_cliente)
    assert error_code(r, 400) == "CREDITO_NO_FORMALIZADO"


def test_oferta_permisos_y_404(client, h_cliente, h_cliente2, h_analista):
    sid = crear_prestamo(client, h_cliente)["id"]
    for metodo, ruta in [("get", "oferta"), ("post", "oferta/aceptar"), ("post", "oferta/rechazar"),
                         ("post", "formalizar"), ("get", "amortizacion")]:
        r = client.request(metodo.upper(), f"{API}/solicitudes/{sid}/{ruta}", headers=h_cliente2)
        assert error_code(r, 403) == "ACCESO_DENEGADO", ruta
        r = client.request(metodo.upper(), f"{API}/solicitudes/{sid}/{ruta}", headers=h_analista)
        assert error_code(r, 403) == "PERMISO_INSUFICIENTE", ruta
        r = client.request(metodo.upper(), f"{API}/solicitudes/999/{ruta}", headers=h_cliente)
        assert error_code(r, 404) == "SOLICITUD_NO_ENCONTRADA", ruta
