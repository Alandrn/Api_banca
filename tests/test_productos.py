"""Pruebas del catálogo de productos."""

from __future__ import annotations

import copy

from tests.helpers import API, H_FIJA, P_BASICO, error_code, ok_data

NUEVO = {
    "nombre": "Préstamo Auto Demo",
    "tipo": "prestamo",
    "descripcion": "Préstamo demostrativo para compra de auto.",
    "tasaAnual": 16.9,
    "montoMin": 30000,
    "montoMax": 400000,
    "plazosMeses": [48, 12, 24],
    "documentosRequeridos": ["identificacion", "comprobante_ingresos"],
    "requisitos": ["Ser mayor de edad"],
    "condiciones": "Tasa fija. Producto demostrativo.",
}


def nuevo(**cambios):
    datos = copy.deepcopy(NUEVO)
    datos.update(cambios)
    return datos


def test_listar_productos_publico(client):
    data = ok_data(client.get(f"{API}/productos"))
    assert len(data) == 6 and all("Demo" in p["nombre"] for p in data)
    assert data[0]["tasaAnual"] == 24.0 and data[0]["plazosMeses"] == [12, 24, 36]


def test_listar_filtro_tipo(client):
    data = ok_data(client.get(f"{API}/productos?tipo=hipoteca"))
    assert len(data) == 3 and all(p["tipo"] == "hipoteca" and p["engancheMinPct"] for p in data)


def test_listar_filtro_invalido(client):
    assert error_code(client.get(f"{API}/productos?tipo=auto"), 422) == "ERROR_VALIDACION"


def test_obtener_producto(client):
    data = ok_data(client.get(f"{API}/productos/{H_FIJA}"))
    assert data["nombre"] == "Hipoteca Fija Demo" and data["engancheMinPct"] == 10.0


def test_obtener_producto_404_y_422(client):
    assert error_code(client.get(f"{API}/productos/999"), 404) == "PRODUCTO_NO_ENCONTRADO"
    assert error_code(client.get(f"{API}/productos/abc"), 422) == "ERROR_VALIDACION"


def test_requisitos(client):
    data = ok_data(client.get(f"{API}/productos/{H_FIJA}/requisitos"))
    tipos = [d["tipo"] for d in data["documentosRequeridos"]]
    assert "escrituras" in tipos and data["requisitos"]
    assert all(d["descripcion"] for d in data["documentosRequeridos"])


def test_requisitos_404(client):
    assert error_code(client.get(f"{API}/productos/999/requisitos"), 404) == "PRODUCTO_NO_ENCONTRADO"


def test_crear_producto_admin(client, h_admin):
    data = ok_data(client.post(f"{API}/productos", json=NUEVO, headers=h_admin), 201)
    assert data["id"] == 7 and data["plazosMeses"] == [12, 24, 48] and data["engancheMinPct"] is None


def test_crear_producto_sin_permiso(client, h_cliente, h_analista):
    assert error_code(client.post(f"{API}/productos", json=NUEVO, headers=h_cliente), 403) == "PERMISO_INSUFICIENTE"
    assert error_code(client.post(f"{API}/productos", json=NUEVO, headers=h_analista), 403) == "PERMISO_INSUFICIENTE"


def test_crear_producto_validaciones(client, h_admin):
    casos = [
        nuevo(montoMin=500000),  # min >= max
        nuevo(tipo="hipoteca"),  # hipoteca sin enganche
        nuevo(documentosRequeridos=["identificacion", "escrituras"]),  # escrituras en préstamo
        nuevo(engancheMinPct=10),  # enganche en préstamo
        nuevo(plazosMeses=[]),
        nuevo(plazosMeses=[12, 12]),
        nuevo(tasaAnual=-1),
        nuevo(documentosRequeridos=["pasaporte"]),
    ]
    for datos in casos:
        r = client.post(f"{API}/productos", json=datos, headers=h_admin)
        assert error_code(r, 422) == "ERROR_VALIDACION", datos


def test_crear_producto_nombre_duplicado(client, h_admin):
    r = client.post(f"{API}/productos", json=nuevo(nombre="Préstamo Nómina Demo"), headers=h_admin)
    assert error_code(r, 409) == "PRODUCTO_DUPLICADO"


def test_actualizar_producto(client, h_admin):
    data = ok_data(client.put(f"{API}/productos/{P_BASICO}", json=nuevo(nombre="Préstamo Personal Demo Básico"),
                              headers=h_admin))
    assert data["tasaAnual"] == 16.9 and data["montoMax"] == 400000


def test_actualizar_producto_404_422_403(client, h_admin, h_cliente):
    assert error_code(client.put(f"{API}/productos/999", json=NUEVO, headers=h_admin), 404) == "PRODUCTO_NO_ENCONTRADO"
    assert error_code(client.put(f"{API}/productos/1", json={"nombre": "x"}, headers=h_admin), 422) == "ERROR_VALIDACION"
    assert error_code(client.put(f"{API}/productos/1", json=NUEVO, headers=h_cliente), 403) == "PERMISO_INSUFICIENTE"


def test_actualizar_producto_nombre_de_otro(client, h_admin):
    r = client.put(f"{API}/productos/1", json=nuevo(nombre="Hipoteca Fija Demo"), headers=h_admin)
    assert error_code(r, 409) == "PRODUCTO_DUPLICADO"


def test_eliminar_producto_logico(client, h_admin, h_cliente):
    r = client.delete(f"{API}/productos/{P_BASICO}", headers=h_admin)
    assert r.status_code == 204 and r.content == b""
    assert ok_data(client.get(f"{API}/productos/{P_BASICO}"))["activo"] is False
    assert len(ok_data(client.get(f"{API}/productos"))) == 5
    inactivos = ok_data(client.get(f"{API}/productos?activo=false"))
    assert [p["id"] for p in inactivos] == [P_BASICO]
    r = client.post(f"{API}/solicitudes", json={"productoId": P_BASICO, "montoSolicitado": 50000, "plazoMeses": 12},
                    headers=h_cliente)
    assert error_code(r, 400) == "PRODUCTO_INACTIVO"


def test_eliminar_producto_404_403(client, h_admin, h_cliente):
    assert error_code(client.delete(f"{API}/productos/999", headers=h_admin), 404) == "PRODUCTO_NO_ENCONTRADO"
    assert error_code(client.delete(f"{API}/productos/1", headers=h_cliente), 403) == "PERMISO_INSUFICIENTE"
