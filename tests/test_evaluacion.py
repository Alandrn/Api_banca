"""Pruebas de inmueble, avalúo, análisis de crédito y resolución."""

from __future__ import annotations

from decimal import Decimal

from app.services.evaluacion import conservacion_por_antiguedad, factor_avaluo
from app.utils.analisis import calcular_puntaje_buro
from tests.conftest import VALUADOR_ID, VALUADOR2_ID
from tests.helpers import (
    API,
    DOCS_HIPOTECA,
    INMUEBLE_OK,
    P_BASICO,
    SOLICITANTE_OK,
    crear_hipoteca,
    crear_prestamo,
    entregar_docs,
    error_code,
    hipoteca_avaluada,
    hipoteca_lista,
    inmueble,
    ok_data,
    prestamo_listo,
    solicitante,
)


def _avaluo_de(client, h, sid):
    return ok_data(client.get(f"{API}/solicitudes/{sid}/inmueble", headers=h))["avaluo"]


def _analisis(client, h, sid):
    return client.post(f"{API}/solicitudes/{sid}/analisis", headers=h)


# --- Inmueble ----------------------------------------------------------------------

def test_registrar_y_consultar_inmueble(client, h_cliente):
    sid = crear_hipoteca(client, h_cliente)["id"]
    r = client.get(f"{API}/solicitudes/{sid}/inmueble", headers=h_cliente)
    assert error_code(r, 404) == "INMUEBLE_NO_REGISTRADO"
    data = ok_data(client.put(f"{API}/solicitudes/{sid}/inmueble", json=INMUEBLE_OK, headers=h_cliente))
    assert data["cp"] == "03100" and data["avaluo"] is None and data["m2Terreno"] == 160
    data = ok_data(client.put(f"{API}/solicitudes/{sid}/inmueble", json=inmueble(recamaras=4), headers=h_cliente))
    assert data["recamaras"] == 4
    assert ok_data(client.get(f"{API}/solicitudes/{sid}/inmueble", headers=h_cliente))["recamaras"] == 4


def test_inmueble_solo_hipoteca(client, h_cliente):
    sid = crear_prestamo(client, h_cliente)["id"]
    r = client.put(f"{API}/solicitudes/{sid}/inmueble", json=INMUEBLE_OK, headers=h_cliente)
    assert error_code(r, 400) == "SOLO_HIPOTECA"


def test_inmueble_validacion(client, h_cliente):
    sid = crear_hipoteca(client, h_cliente)["id"]
    for datos in (inmueble(cp="123"), inmueble(tipo="oficina"), inmueble(valorEstimadoCliente=0),
                  inmueble(m2Construccion=0)):
        r = client.put(f"{API}/solicitudes/{sid}/inmueble", json=datos, headers=h_cliente)
        assert error_code(r, 422) == "ERROR_VALIDACION"
    ok_data(client.put(f"{API}/solicitudes/{sid}/inmueble", json=inmueble(tipo="terreno", m2Construccion=0),
                       headers=h_cliente))


def test_inmueble_permisos_y_404(client, h_cliente, h_cliente2, h_analista):
    sid = crear_hipoteca(client, h_cliente)["id"]
    url = f"{API}/solicitudes/{sid}/inmueble"
    assert error_code(client.put(url, json=INMUEBLE_OK, headers=h_cliente2), 403) == "ACCESO_DENEGADO"
    assert error_code(client.put(url, json=INMUEBLE_OK, headers=h_analista), 403) == "PERMISO_INSUFICIENTE"
    assert error_code(client.get(url, headers=h_cliente2), 403) == "ACCESO_DENEGADO"
    r = client.put(f"{API}/solicitudes/999/inmueble", json=INMUEBLE_OK, headers=h_cliente)
    assert error_code(r, 404) == "SOLICITUD_NO_ENCONTRADA"


# --- Avalúo ------------------------------------------------------------------------

def test_solicitar_avaluo_automatico(client, h_cliente):
    sid = hipoteca_lista(client, h_cliente)
    data = ok_data(client.post(f"{API}/solicitudes/{sid}/avaluo", headers=h_cliente), 201)
    assert data["folio"].startswith("AVA-DEMO-") and data["estado"] == "completado"
    assert data["generadoAutomaticamente"] is True and data["valuadorId"] in (VALUADOR_ID, VALUADOR2_ID)
    assert 2500000 * 0.85 <= data["valorComercial"] <= 2500000 * 1.05
    assert data["estadoConservacion"] == "bueno"  # 8 años
    assert data["solicitudId"] == sid and data["observaciones"]
    detalle = ok_data(client.get(f"{API}/solicitudes/{sid}", headers=h_cliente))
    assert detalle["estado"] == "avaluo_completado"
    estados = [h["estadoNuevo"] for h in ok_data(client.get(f"{API}/solicitudes/{sid}/historial", headers=h_cliente))]
    assert estados[-2:] == ["en_avaluo", "avaluo_completado"]


def test_avaluo_reproducible():
    assert factor_avaluo(5) == factor_avaluo(5)
    for semilla in range(1, 50):
        assert Decimal("0.85") <= factor_avaluo(semilla) <= Decimal("1.05")


def test_conservacion_por_antiguedad():
    assert [conservacion_por_antiguedad(a) for a in (0, 5, 6, 15, 16, 30, 31)] == [
        "excelente", "excelente", "bueno", "bueno", "regular", "regular", "malo"]


def test_avaluo_estado_incorrecto(client, h_cliente):
    sid = crear_hipoteca(client, h_cliente)["id"]
    assert error_code(client.post(f"{API}/solicitudes/{sid}/avaluo", headers=h_cliente), 400) == "TRANSICION_INVALIDA"
    sid_p = prestamo_listo(client, h_cliente)
    assert error_code(client.post(f"{API}/solicitudes/{sid_p}/avaluo", headers=h_cliente), 400) == "SOLO_HIPOTECA"


def test_avaluo_documento_rechazado(client, h_cliente, h_analista):
    sid = hipoteca_lista(client, h_cliente)
    doc_id = ok_data(client.get(f"{API}/solicitudes/{sid}/documentos", headers=h_cliente))[0]["documentoId"]
    ok_data(client.patch(f"{API}/solicitudes/{sid}/documentos/{doc_id}",
                         json={"estado": "rechazado", "observaciones": "Vencida"}, headers=h_analista))
    r = client.post(f"{API}/solicitudes/{sid}/avaluo", headers=h_cliente)
    assert error_code(r, 400) == "DOCUMENTOS_RECHAZADOS"


def test_avaluo_permisos_y_404(client, h_cliente, h_cliente2, h_valuador, h_analista):
    sid = hipoteca_lista(client, h_cliente)
    url = f"{API}/solicitudes/{sid}/avaluo"
    assert error_code(client.post(url, headers=h_valuador), 403) == "PERMISO_INSUFICIENTE"
    assert error_code(client.post(url, headers=h_cliente2), 403) == "ACCESO_DENEGADO"
    assert error_code(client.post(f"{API}/solicitudes/999/avaluo", headers=h_cliente), 404) == "SOLICITUD_NO_ENCONTRADA"
    ok_data(client.post(url, headers=h_analista), 201)  # el analista también puede solicitarlo


def test_listar_avaluos_por_rol(client, h_cliente, h_valuador, h_valuador2, h_analista):
    sid = hipoteca_avaluada(client, h_cliente)
    asignado = _avaluo_de(client, h_cliente, sid)["valuadorId"]
    h_asignado, h_otro = (h_valuador, h_valuador2) if asignado == VALUADOR_ID else (h_valuador2, h_valuador)
    r = client.get(f"{API}/avaluos", headers=h_asignado)
    assert r.json()["meta"]["total"] == 1
    assert client.get(f"{API}/avaluos", headers=h_otro).json()["meta"]["total"] == 0
    assert client.get(f"{API}/avaluos?estado=completado", headers=h_analista).json()["meta"]["total"] == 1
    assert client.get(f"{API}/avaluos?estado=solicitado", headers=h_analista).json()["meta"]["total"] == 0
    assert error_code(client.get(f"{API}/avaluos", headers=h_cliente), 403) == "PERMISO_INSUFICIENTE"
    assert error_code(client.get(f"{API}/avaluos?estado=x", headers=h_analista), 422) == "ERROR_VALIDACION"
    # El valuador asignado puede ver la solicitud; el otro no
    ok_data(client.get(f"{API}/solicitudes/{sid}", headers=h_asignado))
    assert error_code(client.get(f"{API}/solicitudes/{sid}", headers=h_otro), 403) == "ACCESO_DENEGADO"


def test_obtener_avaluo(client, h_cliente, h_cliente2, h_analista):
    sid = hipoteca_avaluada(client, h_cliente)
    avaluo_id = _avaluo_de(client, h_cliente, sid)["id"]
    ok_data(client.get(f"{API}/avaluos/{avaluo_id}", headers=h_cliente))
    ok_data(client.get(f"{API}/avaluos/{avaluo_id}", headers=h_analista))
    assert error_code(client.get(f"{API}/avaluos/{avaluo_id}", headers=h_cliente2), 403) == "ACCESO_DENEGADO"
    assert error_code(client.get(f"{API}/avaluos/999", headers=h_analista), 404) == "AVALUO_NO_ENCONTRADO"


def test_ajustar_avaluo(client, h_cliente, h_valuador, h_valuador2, h_analista):
    sid = hipoteca_avaluada(client, h_cliente)
    avaluo = _avaluo_de(client, h_cliente, sid)
    h_asignado, h_otro = (h_valuador, h_valuador2) if avaluo["valuadorId"] == VALUADOR_ID else (h_valuador2, h_valuador)
    url = f"{API}/avaluos/{avaluo['id']}/resultado"
    cuerpo = {"valorComercial": 2400000, "estadoConservacion": "regular", "observaciones": "Ajuste tras visita."}
    data = ok_data(client.patch(url, json=cuerpo, headers=h_asignado))
    assert data["valorComercial"] == 2400000 and data["generadoAutomaticamente"] is False
    assert error_code(client.patch(url, json=cuerpo, headers=h_otro), 403) == "ACCESO_DENEGADO"
    assert error_code(client.patch(url, json=cuerpo, headers=h_analista), 403) == "PERMISO_INSUFICIENTE"
    assert error_code(client.patch(url, json={"valorComercial": -5}, headers=h_asignado), 422) == "ERROR_VALIDACION"
    r = client.patch(f"{API}/avaluos/999/resultado", json=cuerpo, headers=h_asignado)
    assert error_code(r, 404) == "AVALUO_NO_ENCONTRADO"
    # Tras el análisis ya no se puede ajustar
    ok_data(_analisis(client, h_cliente, sid))
    assert error_code(client.patch(url, json=cuerpo, headers=h_asignado), 400) == "AVALUO_NO_EDITABLE"


# --- Análisis ----------------------------------------------------------------------

def test_puntaje_buro_reproducible_y_en_rango():
    assert calcular_puntaje_buro("SOL-DEMO-2026-000001") == calcular_puntaje_buro("SOL-DEMO-2026-000001")
    valores = {calcular_puntaje_buro(f"SOL-DEMO-2026-{i:06d}") for i in range(1, 300)}
    assert min(valores) >= 400 and max(valores) <= 850 and len(valores) > 50


def test_analisis_prestamo_aprobado(client, h_cliente):
    sid = prestamo_listo(client, h_cliente)
    data = ok_data(_analisis(client, h_cliente, sid))
    assert data["estado"] == "aprobada" and data["puntajeBuro"] == 700
    assert data["montoAprobado"] == 80000 and data["tasaAprobada"] == 18.5 and data["plazoAprobado"] == 24
    reglas = {r["regla"]: r for r in data["resultadoAnalisis"]["reglas"]}
    assert set(reglas) == {"capacidad_pago", "buro", "antiguedad_laboral", "edad_fin_plazo"}
    assert all(set(r) >= {"regla", "valor", "limite", "cumple"} and r["cumple"] for r in reglas.values())
    estados = [h["estadoNuevo"] for h in ok_data(client.get(f"{API}/solicitudes/{sid}/historial", headers=h_cliente))]
    assert estados[-2:] == ["en_analisis", "aprobada"]


def test_analisis_buro_preferente_descuenta_tasa(client, h_cliente, fijar_buro):
    fijar_buro(780)
    sid = prestamo_listo(client, h_cliente)
    data = ok_data(_analisis(client, h_cliente, sid))
    assert data["estado"] == "aprobada" and data["tasaAprobada"] == 17.5


def test_analisis_buro_bajo_rechaza(client, h_cliente, fijar_buro):
    fijar_buro(550)
    sid = prestamo_listo(client, h_cliente)
    data = ok_data(_analisis(client, h_cliente, sid))
    assert data["estado"] == "rechazada" and "buró" in data["motivoResolucion"]
    assert data["montoAprobado"] is None


def test_analisis_antiguedad_baja_rechaza(client, h_cliente):
    sid = prestamo_listo(client, h_cliente, datos_solicitante=solicitante(antiguedadMeses=3))
    data = ok_data(_analisis(client, h_cliente, sid))
    assert data["estado"] == "rechazada" and "antigüedad" in data["motivoResolucion"]


def test_analisis_capacidad_insuficiente_condiciona(client, h_cliente):
    datos = solicitante(ingresoMensual=12000, otrosIngresos=0, deudasMensuales=0)
    sid = prestamo_listo(client, h_cliente, datos_solicitante=datos, monto=100000, plazo=24)
    data = ok_data(_analisis(client, h_cliente, sid))
    assert data["estado"] == "condicionada"
    assert 50000 <= data["montoAprobado"] < 100000 and data["montoAprobado"] % 100 == 0
    assert data["mensualidadAprobada"] <= 12000 * 0.35
    assert "capacidad de pago" in data["motivoResolucion"]


def test_analisis_ingreso_muy_bajo_rechaza(client, h_cliente):
    datos = solicitante(ingresoMensual=3000, otrosIngresos=0, deudasMensuales=0)
    sid = prestamo_listo(client, h_cliente, datos_solicitante=datos, monto=100000, plazo=24)
    data = ok_data(_analisis(client, h_cliente, sid))
    assert data["estado"] == "rechazada" and "mínimo del producto" in data["motivoResolucion"]


def test_analisis_hipoteca_ltv_condiciona(client, h_cliente):
    # Avalúo bajo ajustado por el valuador → LTV > 90%
    sid = hipoteca_avaluada(client, h_cliente)
    avaluo = _avaluo_de(client, h_cliente, sid)
    from app.core.security import crear_token

    token, _ = crear_token(avaluo["valuadorId"], "valuador")
    ok_data(client.patch(f"{API}/avaluos/{avaluo['id']}/resultado",
                         json={"valorComercial": 1900000, "estadoConservacion": "regular",
                               "observaciones": "Valor menor al esperado."},
                         headers={"Authorization": f"Bearer {token}"}))
    data = ok_data(_analisis(client, h_cliente, sid))
    assert data["estado"] == "condicionada"
    assert data["montoAprobado"] == 1710000  # 90% de 1,900,000
    assert data["engancheRequerido"] == 790000
    reglas = {r["regla"]: r for r in data["resultadoAnalisis"]["reglas"]}
    assert reglas["ltv"]["cumple"] is False and reglas["ltv"]["limite"] == 90


def test_analisis_estado_incorrecto(client, h_cliente):
    sid = hipoteca_lista(client, h_cliente)
    assert error_code(_analisis(client, h_cliente, sid), 400) == "TRANSICION_INVALIDA"  # hipoteca sin avalúo
    sid_b = crear_prestamo(client, h_cliente)["id"]
    assert error_code(_analisis(client, h_cliente, sid_b), 400) == "TRANSICION_INVALIDA"  # borrador


def test_analisis_permisos_y_404(client, h_cliente, h_cliente2, h_valuador, h_analista):
    sid = prestamo_listo(client, h_cliente)
    assert error_code(_analisis(client, h_valuador, sid), 403) == "PERMISO_INSUFICIENTE"
    assert error_code(_analisis(client, h_cliente2, sid), 403) == "ACCESO_DENEGADO"
    assert error_code(_analisis(client, h_cliente, 999), 404) == "SOLICITUD_NO_ENCONTRADA"
    assert ok_data(_analisis(client, h_analista, sid))["estado"] == "aprobada"


# --- Resolución --------------------------------------------------------------------

def test_resolucion_sobrescrita_por_analista(client, h_cliente, h_analista, fijar_buro):
    fijar_buro(550)
    sid = prestamo_listo(client, h_cliente)
    ok_data(_analisis(client, h_cliente, sid))
    cuerpo = {"estado": "aprobada", "monto": 70000, "tasa": 17, "plazo": 36, "motivo": "Revisión manual favorable"}
    data = ok_data(client.patch(f"{API}/solicitudes/{sid}/resolucion", json=cuerpo, headers=h_analista))
    assert data["estado"] == "aprobada" and data["montoAprobado"] == 70000 and data["tasaAprobada"] == 17
    assert data["plazoAprobado"] == 36 and data["mensualidadAprobada"] > 0
    assert data["resultadoAnalisis"]["sobrescritura"]["estadoAnterior"] == "rechazada"
    oferta = ok_data(client.get(f"{API}/solicitudes/{sid}/oferta", headers=h_cliente))
    assert oferta["monto"] == 70000
    data = ok_data(client.patch(f"{API}/solicitudes/{sid}/resolucion",
                                json={"estado": "rechazada", "motivo": "Documentación inconsistente"},
                                headers=h_analista))
    assert data["estado"] == "rechazada" and data["montoAprobado"] is None


def test_resolucion_validaciones(client, h_cliente, h_analista):
    sid = prestamo_listo(client, h_cliente)
    url = f"{API}/solicitudes/{sid}/resolucion"
    r = client.patch(url, json={"estado": "aprobada", "motivo": "Antes de tiempo"}, headers=h_analista)
    assert error_code(r, 400) == "RESOLUCION_NO_EDITABLE"
    ok_data(_analisis(client, h_cliente, sid))
    assert error_code(client.patch(url, json={"estado": "formalizada", "motivo": "No válido"}, headers=h_analista),
                      422) == "ERROR_VALIDACION"
    assert error_code(client.patch(url, json={"estado": "aprobada"}, headers=h_analista), 422) == "ERROR_VALIDACION"
    r = client.patch(url, json={"estado": "aprobada", "monto": 999999, "motivo": "Excede"}, headers=h_analista)
    assert error_code(r, 400) == "MONTO_FUERA_DE_RANGO"
    r = client.patch(url, json={"estado": "aprobada", "plazo": 7, "motivo": "Plazo raro"}, headers=h_analista)
    assert error_code(r, 400) == "PLAZO_NO_PERMITIDO"
    cuerpo = {"estado": "aprobada", "motivo": "Sin permiso"}
    assert error_code(client.patch(url, json=cuerpo, headers=h_cliente), 403) == "PERMISO_INSUFICIENTE"
    r = client.patch(f"{API}/solicitudes/999/resolucion", json=cuerpo, headers=h_analista)
    assert error_code(r, 404) == "SOLICITUD_NO_ENCONTRADA"
    # Después de aceptar la oferta ya no se puede sobrescribir
    ok_data(client.post(f"{API}/solicitudes/{sid}/oferta/aceptar", headers=h_cliente))
    assert error_code(client.patch(url, json=cuerpo, headers=h_analista), 400) == "RESOLUCION_NO_EDITABLE"


def test_analisis_prestamo_basico_edad_y_reglas(client, h_cliente):
    sid = prestamo_listo(client, h_cliente, producto_id=P_BASICO, monto=50000, plazo=36)
    data = ok_data(_analisis(client, h_cliente, sid))
    edad = next(r for r in data["resultadoAnalisis"]["reglas"] if r["regla"] == "edad_fin_plazo")
    assert edad["limite"] == 70 and edad["cumple"] is True and edad["valor"] < 70


def test_hipoteca_documentos_completos_lista(client, h_cliente):
    sid = crear_hipoteca(client, h_cliente)["id"]
    client.put(f"{API}/solicitudes/{sid}/solicitante", json=SOLICITANTE_OK, headers=h_cliente)
    entregar_docs(client, h_cliente, sid, DOCS_HIPOTECA[:-1])
    progreso = ok_data(client.get(f"{API}/solicitudes/{sid}", headers=h_cliente))["progreso"]
    assert progreso["documentosPendientes"] == ["predial"] and progreso["inmuebleRegistrado"] is False
