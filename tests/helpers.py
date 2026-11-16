"""Funciones auxiliares para construir escenarios en las pruebas."""

from __future__ import annotations

import copy
from typing import Any

API = "/api/v1"

# Ids de productos (orden de seeds.PRODUCTOS)
P_BASICO, P_PLUS, P_NOMINA, H_FIJA, H_PLUS, H_JOVEN = range(1, 7)

DOCS_PRESTAMO = ["identificacion", "comprobante_domicilio", "comprobante_ingresos", "estados_cuenta"]
DOCS_NOMINA = ["identificacion", "comprobante_domicilio", "comprobante_ingresos"]
DOCS_HIPOTECA = DOCS_PRESTAMO + ["escrituras", "predial"]

SOLICITANTE_OK: dict[str, Any] = {
    "fechaNacimiento": "1990-04-15",
    "curpFicticia": "DEMO900415HDFXXX01",
    "estadoCivil": "casado",
    "dependientes": 2,
    "domicilio": "Av. Demo 123, Col. Centro",
    "ciudad": "Ciudad de México",
    "empresa": "Empresa Demo SA de CV",
    "puesto": "Ingeniero de software",
    "tipoEmpleo": "asalariado",
    "antiguedadMeses": 48,
    "ingresoMensual": 65000,
    "otrosIngresos": 5000,
    "gastosMensuales": 20000,
    "deudasMensuales": 3000,
    "referencias": [
        {"nombre": "María Gómez", "telefono": "5511112222", "relacion": "hermana"},
        {"nombre": "Pedro Ruiz", "telefono": "5533334444", "relacion": "amigo"},
    ],
}

INMUEBLE_OK: dict[str, Any] = {
    "tipo": "casa",
    "direccion": "Calle Demo 45",
    "colonia": "Del Valle",
    "ciudad": "Ciudad de México",
    "estado": "Ciudad de México",
    "cp": "03100",
    "m2Terreno": 160,
    "m2Construccion": 140,
    "antiguedadAnios": 8,
    "recamaras": 3,
    "banos": 2,
    "valorEstimadoCliente": 2500000,
}


def solicitante(**cambios: Any) -> dict[str, Any]:
    """Copia de SOLICITANTE_OK con cambios."""
    datos = copy.deepcopy(SOLICITANTE_OK)
    datos.update(cambios)
    return datos


def inmueble(**cambios: Any) -> dict[str, Any]:
    """Copia de INMUEBLE_OK con cambios."""
    datos = copy.deepcopy(INMUEBLE_OK)
    datos.update(cambios)
    return datos


def ok_data(resp, status: int = 200) -> Any:
    """Verifica el sobre de éxito y devuelve ``data``."""
    assert resp.status_code == status, resp.text
    cuerpo = resp.json()
    assert cuerpo["ok"] is True and cuerpo["demo"] is True
    return cuerpo["data"]


def error_code(resp, status: int) -> str:
    """Verifica el sobre de error y devuelve el código."""
    assert resp.status_code == status, resp.text
    cuerpo = resp.json()
    assert cuerpo["ok"] is False and cuerpo["demo"] is True
    assert set(cuerpo["error"]) == {"code", "message", "details"}
    return cuerpo["error"]["code"]


def crear_prestamo(client, h, producto_id: int = P_PLUS, monto: int = 80000, plazo: int = 24) -> dict:
    """Crea un préstamo en borrador y devuelve su ``data``."""
    r = client.post(f"{API}/solicitudes", json={"productoId": producto_id, "montoSolicitado": monto,
                                                 "plazoMeses": plazo}, headers=h)
    return ok_data(r, 201)


def crear_hipoteca(client, h, producto_id: int = H_FIJA, monto: int = 1800000, plazo: int = 240,
                   valor: int = 2500000) -> dict:
    """Crea una hipoteca en borrador y devuelve su ``data``."""
    r = client.post(f"{API}/solicitudes", json={"productoId": producto_id, "montoSolicitado": monto,
                                                 "plazoMeses": plazo, "valorInmueble": valor}, headers=h)
    return ok_data(r, 201)


def entregar_docs(client, h, sid: int, tipos: list[str]) -> None:
    """Entrega documentos simulados."""
    for tipo in tipos:
        r = client.post(f"{API}/solicitudes/{sid}/documentos",
                        json={"tipo": tipo, "nombreArchivoSimulado": f"{tipo}_demo.pdf"}, headers=h)
        ok_data(r, 201)


def prestamo_listo(client, h, datos_solicitante: dict | None = None, **kw) -> int:
    """Préstamo en ``datos_completos``. Devuelve el id."""
    s = crear_prestamo(client, h, **kw)
    sid = s["id"]
    ok_data(client.put(f"{API}/solicitudes/{sid}/solicitante", json=datos_solicitante or SOLICITANTE_OK, headers=h))
    docs = DOCS_NOMINA if kw.get("producto_id") == P_NOMINA else DOCS_PRESTAMO
    entregar_docs(client, h, sid, docs)
    detalle = ok_data(client.get(f"{API}/solicitudes/{sid}", headers=h))
    assert detalle["estado"] == "datos_completos"
    return sid


def hipoteca_lista(client, h, datos_solicitante: dict | None = None, datos_inmueble: dict | None = None,
                   **kw) -> int:
    """Hipoteca en ``datos_completos``. Devuelve el id."""
    s = crear_hipoteca(client, h, **kw)
    sid = s["id"]
    ok_data(client.put(f"{API}/solicitudes/{sid}/solicitante", json=datos_solicitante or SOLICITANTE_OK, headers=h))
    entregar_docs(client, h, sid, DOCS_HIPOTECA)
    ok_data(client.put(f"{API}/solicitudes/{sid}/inmueble", json=datos_inmueble or INMUEBLE_OK, headers=h))
    detalle = ok_data(client.get(f"{API}/solicitudes/{sid}", headers=h))
    assert detalle["estado"] == "datos_completos"
    return sid


def hipoteca_avaluada(client, h, **kw) -> int:
    """Hipoteca en ``avaluo_completado``. Devuelve el id."""
    sid = hipoteca_lista(client, h, **kw)
    ok_data(client.post(f"{API}/solicitudes/{sid}/avaluo", headers=h), 201)
    return sid
