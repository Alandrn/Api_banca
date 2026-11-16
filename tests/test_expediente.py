"""Pruebas del expediente: solicitante y documentos."""

from __future__ import annotations

from datetime import date

from tests.helpers import (
    API,
    DOCS_HIPOTECA,
    DOCS_PRESTAMO,
    INMUEBLE_OK,
    SOLICITANTE_OK,
    crear_hipoteca,
    crear_prestamo,
    entregar_docs,
    error_code,
    ok_data,
    prestamo_listo,
    solicitante,
)


def _put_solicitante(client, h, sid, datos):
    return client.put(f"{API}/solicitudes/{sid}/solicitante", json=datos, headers=h)


# --- Solicitante -----------------------------------------------------------------

def test_guardar_y_consultar_solicitante(client, h_cliente, h_analista):
    sid = crear_prestamo(client, h_cliente)["id"]
    assert error_code(client.get(f"{API}/solicitudes/{sid}/solicitante", headers=h_cliente), 404) == \
        "SOLICITANTE_NO_REGISTRADO"
    data = ok_data(_put_solicitante(client, h_cliente, sid, SOLICITANTE_OK))
    assert data["ingresoMensual"] == 65000 and len(data["referencias"]) == 2
    assert ok_data(client.get(f"{API}/solicitudes/{sid}/solicitante", headers=h_analista))["curpFicticia"] == \
        "DEMO900415HDFXXX01"
    # Reemplazo completo
    data = ok_data(_put_solicitante(client, h_cliente, sid, solicitante(ingresoMensual=70000)))
    assert data["ingresoMensual"] == 70000


def test_solicitante_snake_case(client, h_cliente):
    sid = crear_prestamo(client, h_cliente)["id"]
    datos = {
        "fecha_nacimiento": "1985-01-01", "curp_ficticia": "DEMO850101HDFXXX02", "estado_civil": "soltero",
        "dependientes": 0, "domicilio": "Calle Demo 1", "ciudad": "Puebla", "empresa": "Demo SA", "puesto": "Gerente",
        "tipo_empleo": "independiente", "antiguedad_meses": 24, "ingreso_mensual": 40000,
        "referencias": [{"nombre": "Ana Ruiz", "telefono": "5511110000", "relacion": "amiga"},
                        {"nombre": "Luis Paz", "telefono": "5522220000", "relacion": "primo"}],
    }
    data = ok_data(_put_solicitante(client, h_cliente, sid, datos))
    assert data["tipoEmpleo"] == "independiente" and data["otrosIngresos"] == 0


def test_solicitante_menor_de_edad(client, h_cliente):
    sid = crear_prestamo(client, h_cliente)["id"]
    hace_17 = date(date.today().year - 17, 1, 1).isoformat()
    r = _put_solicitante(client, h_cliente, sid, solicitante(fechaNacimiento=hace_17))
    assert error_code(r, 400) == "EDAD_INSUFICIENTE"


def test_solicitante_edad_excede_plazo(client, h_cliente):
    sid = crear_hipoteca(client, h_cliente)["id"]  # 240 meses
    nacimiento = date(date.today().year - 55, 1, 1).isoformat()  # tendría 75
    r = _put_solicitante(client, h_cliente, sid, solicitante(fechaNacimiento=nacimiento))
    assert error_code(r, 400) == "EDAD_EXCEDE_PLAZO"


def test_solicitante_validaciones_422(client, h_cliente):
    sid = crear_prestamo(client, h_cliente)["id"]
    casos = [
        solicitante(referencias=[SOLICITANTE_OK["referencias"][0]]),
        solicitante(ingresoMensual=0),
        solicitante(curpFicticia="CORTA"),
        solicitante(tipoEmpleo="freelance"),
        solicitante(fechaNacimiento="15/04/1990"),
        solicitante(referencias=[SOLICITANTE_OK["referencias"][0]] * 2),  # teléfonos repetidos
    ]
    for datos in casos:
        assert error_code(_put_solicitante(client, h_cliente, sid, datos), 422) == "ERROR_VALIDACION"


def test_solicitante_antiguedad_baja_se_acepta(client, h_cliente):
    sid = crear_prestamo(client, h_cliente)["id"]
    assert ok_data(_put_solicitante(client, h_cliente, sid, solicitante(antiguedadMeses=3)))["antiguedadMeses"] == 3


def test_solicitante_permisos_y_404(client, h_cliente, h_cliente2, h_analista):
    sid = crear_prestamo(client, h_cliente)["id"]
    assert error_code(_put_solicitante(client, h_cliente2, sid, SOLICITANTE_OK), 403) == "ACCESO_DENEGADO"
    assert error_code(_put_solicitante(client, h_analista, sid, SOLICITANTE_OK), 403) == "PERMISO_INSUFICIENTE"
    assert error_code(_put_solicitante(client, h_cliente, 999, SOLICITANTE_OK), 404) == "SOLICITUD_NO_ENCONTRADA"
    assert error_code(client.get(f"{API}/solicitudes/{sid}/solicitante", headers=h_cliente2), 403) == "ACCESO_DENEGADO"


# --- Documentos --------------------------------------------------------------------

def test_listar_documentos_incluye_pendientes(client, h_cliente):
    sid = crear_hipoteca(client, h_cliente)["id"]
    data = ok_data(client.get(f"{API}/solicitudes/{sid}/documentos", headers=h_cliente))
    assert [d["tipo"] for d in data] == DOCS_HIPOTECA
    assert all(d["estado"] == "pendiente" and d["documentoId"] is None for d in data)
    entregar_docs(client, h_cliente, sid, ["identificacion"])
    data = ok_data(client.get(f"{API}/solicitudes/{sid}/documentos", headers=h_cliente))
    assert data[0]["estado"] == "entregado" and data[0]["nombreArchivoSimulado"] == "identificacion_demo.pdf"


def test_entregar_documento(client, h_cliente):
    sid = crear_prestamo(client, h_cliente)["id"]
    r = client.post(f"{API}/solicitudes/{sid}/documentos",
                    json={"tipo": "identificacion", "nombreArchivoSimulado": "ine_demo.pdf"}, headers=h_cliente)
    data = ok_data(r, 201)
    assert data["estado"] == "entregado" and data["solicitudId"] == sid


def test_entregar_documento_no_requerido(client, h_cliente):
    sid = crear_prestamo(client, h_cliente)["id"]
    r = client.post(f"{API}/solicitudes/{sid}/documentos",
                    json={"tipo": "escrituras", "nombreArchivoSimulado": "escrituras.pdf"}, headers=h_cliente)
    assert error_code(r, 400) == "DOCUMENTO_NO_REQUERIDO"


def test_entregar_documento_duplicado_409(client, h_cliente):
    sid = crear_prestamo(client, h_cliente)["id"]
    entregar_docs(client, h_cliente, sid, ["identificacion"])
    r = client.post(f"{API}/solicitudes/{sid}/documentos",
                    json={"tipo": "identificacion", "nombreArchivoSimulado": "otra.pdf"}, headers=h_cliente)
    assert error_code(r, 409) == "DOCUMENTO_YA_ENTREGADO"


def test_entregar_documento_validacion(client, h_cliente):
    sid = crear_prestamo(client, h_cliente)["id"]
    for cuerpo in ({"tipo": "pasaporte", "nombreArchivoSimulado": "a.pdf"},
                   {"tipo": "identificacion", "nombreArchivoSimulado": "virus.exe"},
                   {"tipo": "identificacion"}):
        r = client.post(f"{API}/solicitudes/{sid}/documentos", json=cuerpo, headers=h_cliente)
        assert error_code(r, 422) == "ERROR_VALIDACION"


def test_entregar_documento_permisos_y_404(client, h_cliente, h_cliente2, h_analista):
    sid = crear_prestamo(client, h_cliente)["id"]
    cuerpo = {"tipo": "identificacion", "nombreArchivoSimulado": "ine.pdf"}
    assert error_code(client.post(f"{API}/solicitudes/{sid}/documentos", json=cuerpo, headers=h_cliente2), 403) == \
        "ACCESO_DENEGADO"
    assert error_code(client.post(f"{API}/solicitudes/{sid}/documentos", json=cuerpo, headers=h_analista), 403) == \
        "PERMISO_INSUFICIENTE"
    assert error_code(client.post(f"{API}/solicitudes/999/documentos", json=cuerpo, headers=h_cliente), 404) == \
        "SOLICITUD_NO_ENCONTRADA"
    assert error_code(client.get(f"{API}/solicitudes/999/documentos", headers=h_cliente), 404) == \
        "SOLICITUD_NO_ENCONTRADA"


def test_avance_automatico_prestamo(client, h_cliente):
    sid = crear_prestamo(client, h_cliente)["id"]
    entregar_docs(client, h_cliente, sid, DOCS_PRESTAMO)
    assert ok_data(client.get(f"{API}/solicitudes/{sid}", headers=h_cliente))["estado"] == "borrador"
    r = _put_solicitante(client, h_cliente, sid, SOLICITANTE_OK)
    assert "datos_completos" in r.json()["message"]
    data = ok_data(client.get(f"{API}/solicitudes/{sid}", headers=h_cliente))
    assert data["estado"] == "datos_completos" and data["progreso"]["porcentaje"] == 40
    historial = ok_data(client.get(f"{API}/solicitudes/{sid}/historial", headers=h_cliente))
    assert [h["estadoNuevo"] for h in historial] == ["borrador", "datos_completos"]


def test_avance_automatico_hipoteca_requiere_inmueble(client, h_cliente):
    sid = crear_hipoteca(client, h_cliente)["id"]
    _put_solicitante(client, h_cliente, sid, SOLICITANTE_OK)
    entregar_docs(client, h_cliente, sid, DOCS_HIPOTECA)
    data = ok_data(client.get(f"{API}/solicitudes/{sid}", headers=h_cliente))
    assert data["estado"] == "borrador" and "inmueble" in data["progreso"]["siguientePaso"]
    ok_data(client.put(f"{API}/solicitudes/{sid}/inmueble", json=INMUEBLE_OK, headers=h_cliente))
    assert ok_data(client.get(f"{API}/solicitudes/{sid}", headers=h_cliente))["estado"] == "datos_completos"


def test_revisar_documento_analista(client, h_cliente, h_analista):
    sid = crear_prestamo(client, h_cliente)["id"]
    entregar_docs(client, h_cliente, sid, ["identificacion"])
    doc_id = ok_data(client.get(f"{API}/solicitudes/{sid}/documentos", headers=h_cliente))[0]["documentoId"]
    data = ok_data(client.patch(f"{API}/solicitudes/{sid}/documentos/{doc_id}", json={"estado": "validado"},
                                headers=h_analista))
    assert data["estado"] == "validado"


def test_documento_rechazado_se_reemplaza(client, h_cliente, h_analista):
    sid = crear_prestamo(client, h_cliente)["id"]
    entregar_docs(client, h_cliente, sid, ["identificacion"])
    doc_id = ok_data(client.get(f"{API}/solicitudes/{sid}/documentos", headers=h_cliente))[0]["documentoId"]
    ok_data(client.patch(f"{API}/solicitudes/{sid}/documentos/{doc_id}",
                         json={"estado": "rechazado", "observaciones": "Ilegible"}, headers=h_analista))
    data = ok_data(client.get(f"{API}/solicitudes/{sid}", headers=h_cliente))
    assert data["progreso"]["documentosRechazados"] == ["identificacion"]
    r = client.post(f"{API}/solicitudes/{sid}/documentos",
                    json={"tipo": "identificacion", "nombreArchivoSimulado": "ine_nueva.pdf"}, headers=h_cliente)
    data = ok_data(r, 201)
    assert data["id"] == doc_id and data["estado"] == "entregado" and data["observaciones"] is None


def test_revisar_documento_validaciones(client, h_cliente, h_cliente2, h_analista):
    sid = crear_prestamo(client, h_cliente)["id"]
    sid2 = crear_prestamo(client, h_cliente2)["id"]
    entregar_docs(client, h_cliente, sid, ["identificacion"])
    doc_id = ok_data(client.get(f"{API}/solicitudes/{sid}/documentos", headers=h_cliente))[0]["documentoId"]
    url = f"{API}/solicitudes/{sid}/documentos/{doc_id}"
    assert error_code(client.patch(url, json={"estado": "rechazado"}, headers=h_analista), 422) == "ERROR_VALIDACION"
    assert error_code(client.patch(url, json={"estado": "otro"}, headers=h_analista), 422) == "ERROR_VALIDACION"
    assert error_code(client.patch(url, json={"estado": "validado"}, headers=h_cliente), 403) == "PERMISO_INSUFICIENTE"
    r = client.patch(f"{API}/solicitudes/{sid}/documentos/999", json={"estado": "validado"}, headers=h_analista)
    assert error_code(r, 404) == "DOCUMENTO_NO_ENCONTRADO"
    r = client.patch(f"{API}/solicitudes/{sid2}/documentos/{doc_id}", json={"estado": "validado"}, headers=h_analista)
    assert error_code(r, 404) == "DOCUMENTO_NO_ENCONTRADO"


def test_no_editable_despues_de_analisis(client, h_cliente):
    sid = prestamo_listo(client, h_cliente)
    ok_data(client.post(f"{API}/solicitudes/{sid}/analisis", headers=h_cliente))
    assert error_code(_put_solicitante(client, h_cliente, sid, SOLICITANTE_OK), 400) == "SOLICITUD_NO_EDITABLE"
    r = client.post(f"{API}/solicitudes/{sid}/documentos",
                    json={"tipo": "identificacion", "nombreArchivoSimulado": "a.pdf"}, headers=h_cliente)
    assert error_code(r, 400) == "SOLICITUD_NO_EDITABLE"
