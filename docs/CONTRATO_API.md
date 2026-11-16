# Contrato de la API — Banco Demo v1

> Todos los datos son ficticios. Proyecto académico.

## 1. Generalidades

| Concepto | Valor |
|---|---|
| URL base | `http://localhost:8000/api/v1` |
| Formato | JSON UTF-8. **Salida en camelCase**; la entrada acepta camelCase o snake_case |
| Autenticación | `Authorization: Bearer <token>` (JWT HS256, 60 min, payload `sub` y `rol`) |
| Fechas | ISO 8601 en UTC (`2026-11-15T21:39:45`, `1990-04-15`) |
| Dinero | número con 2 decimales (internamente `Decimal`, redondeo ROUND_HALF_UP), moneda MXN |
| Rate limit | `POST /auth/login`: 5/min por IP · resto: 100/min por IP |
| Documentación viva | `/docs` (Swagger) y `/redoc` |

### Roles

| Rol | Alcance |
|---|---|
| `cliente` | Crea y gestiona **sus** solicitudes, consulta **sus** cuentas |
| `valuador` | Ve los avalúos que tiene asignados y ajusta su resultado |
| `analista` | Ve todas las solicitudes, valida documentos, ejecuta análisis y sobrescribe resoluciones |
| `admin` | Todo lo anterior + usuarios y productos |

Reglas de acceso: si el rol no corresponde → `403 PERMISO_INSUFICIENTE`. Si el recurso es de otro cliente → `403 ACCESO_DENEGADO`. Primero se valida la existencia del recurso (404) y después la pertenencia (403).

## 2. Formato de respuestas

**Éxito**

```json
{ "ok": true, "message": "Solicitud SOL-DEMO-2026-000011 creada", "data": { }, "demo": true }
```

**Éxito paginado** (`?page=1&limit=10`, `limit` máximo 100)

```json
{ "ok": true, "message": "Solicitudes", "data": [ ], "meta": { "page": 1, "limit": 10, "total": 42 }, "demo": true }
```

**Error**

```json
{ "ok": false, "error": { "code": "ENGANCHE_INSUFICIENTE", "message": "El enganche (50000.00) es menor al mínimo requerido (100000.00, 10.00% del valor del inmueble)", "details": [ { "enganche": 50000.0, "engancheMinimo": 100000.0, "engancheMinPct": 10.0 } ] }, "demo": true }
```

**Error 422** — `details` es una lista `{campo, mensaje}` en español:

```json
{ "ok": false, "error": { "code": "ERROR_VALIDACION", "message": "Los datos enviados no son válidos",
  "details": [ { "campo": "montoSolicitado", "mensaje": "Debe ser mayor que 0" },
               { "campo": "referencias", "mensaje": "Debe contener al menos 2 elementos" } ] }, "demo": true }
```

### Códigos HTTP

`200` OK · `201` creado · `204` sin contenido · `400` regla de negocio · `401` sin autenticación o token inválido · `403` sin permiso · `404` no existe · `409` conflicto · `422` validación · `429` límite de peticiones · `500` error interno (sin traza).

## 3. Catálogo de códigos de error

| HTTP | Código | Cuándo |
|---|---|---|
| 400 | `TRANSICION_INVALIDA` | La transición de estado no está permitida (details: estado actual, solicitado y permitidos) |
| 400 | `SOLICITUD_NO_EDITABLE` | Se edita el expediente fuera de `borrador`/`datos_completos` |
| 400 | `LIMITE_SOLICITUDES` | El cliente ya tiene 3 solicitudes activas |
| 400 | `PRODUCTO_INACTIVO` | El producto está dado de baja |
| 400 | `TIPO_PRODUCTO_INVALIDO` | Simulador con un producto de otro tipo |
| 400 | `MONTO_FUERA_DE_RANGO` | Monto fuera de `[montoMin, montoMax]` |
| 400 | `PLAZO_NO_PERMITIDO` | El plazo no está en `plazosMeses` |
| 400 | `VALOR_INMUEBLE_REQUERIDO` | Hipoteca sin `valorInmueble` |
| 400 | `MONTO_EXCEDE_VALOR` | Monto ≥ valor del inmueble |
| 400 | `ENGANCHE_INSUFICIENTE` | Enganche < enganche mínimo del producto |
| 400 | `FECHA_NACIMIENTO_INVALIDA` | Fecha de nacimiento igual o posterior a hoy |
| 400 | `EDAD_INSUFICIENTE` | Solicitante menor de 18 años |
| 400 | `EDAD_EXCEDE_PLAZO` | Tendría 70 años o más al terminar el plazo |
| 400 | `DOCUMENTO_NO_REQUERIDO` | El tipo de documento no lo pide el producto |
| 400 | `DOCUMENTOS_RECHAZADOS` | Hay documentos rechazados pendientes de reentrega |
| 400 | `SOLICITUD_FINALIZADA` | Se revisa un documento de una solicitud en estado final |
| 400 | `SOLO_HIPOTECA` | Operación de inmueble/avalúo sobre un préstamo |
| 400 | `INMUEBLE_NO_REGISTRADO` | Se pide avalúo sin inmueble |
| 400 | `SIN_VALUADORES` | No hay valuadores activos para asignar |
| 400 | `AVALUO_PENDIENTE` | Análisis de hipoteca sin avalúo completado |
| 400 | `AVALUO_NO_EDITABLE` | Ajuste de avalúo después de pasar a análisis |
| 400 | `SOLICITANTE_NO_REGISTRADO` | Análisis sin datos del solicitante |
| 400 | `RESOLUCION_NO_EDITABLE` | Sobrescritura fuera de aprobada/condicionada/rechazada |
| 400 | `OFERTA_NO_DISPONIBLE` | La solicitud no tiene oferta en su estado actual |
| 400 | `OFERTA_VENCIDA` | Aceptación después de los 15 días de vigencia |
| 400 | `CREDITO_NO_FORMALIZADO` | Amortización de un crédito no formalizado |
| 400 | `RANGO_FECHAS_INVALIDO` | `desde` > `hasta` en movimientos |
| 400 | `SIN_CAMBIOS` | `PATCH /usuarios/perfil` sin campos |
| 400 | `CAMPO_OBLIGATORIO` | Se intenta vaciar nombre o apellidos |
| 400 | `PASSWORD_INCORRECTA` | La contraseña actual no coincide |
| 400 | `PASSWORD_REPETIDA` | La nueva contraseña es igual a la actual |
| 400 | `OPERACION_NO_PERMITIDA` | El admin intenta desactivarse a sí mismo |
| 401 | `NO_AUTENTICADO` | Falta el header Authorization |
| 401 | `TOKEN_INVALIDO` | Token mal formado, con firma inválida o de un usuario inexistente |
| 401 | `TOKEN_EXPIRADO` | Token vencido |
| 401 | `CREDENCIALES_INVALIDAS` | Correo o contraseña incorrectos |
| 403 | `USUARIO_INACTIVO` | Usuario desactivado (login o token) |
| 403 | `PERMISO_INSUFICIENTE` | El rol no puede usar el endpoint |
| 403 | `ACCESO_DENEGADO` | El recurso pertenece a otro usuario |
| 403 | `RED_NO_PERMITIDA` | La IP está fuera de `ALLOWED_NETWORKS` |
| 404 | `RUTA_NO_ENCONTRADA` | La ruta no existe |
| 404 | `USUARIO_NO_ENCONTRADO` · `PRODUCTO_NO_ENCONTRADO` · `SOLICITUD_NO_ENCONTRADA` · `DOCUMENTO_NO_ENCONTRADO` · `AVALUO_NO_ENCONTRADO` · `CUENTA_NO_ENCONTRADA` | El recurso no existe |
| 404 | `SOLICITANTE_NO_REGISTRADO` · `INMUEBLE_NO_REGISTRADO` | Se consulta antes de capturarlo |
| 405 | `METODO_NO_PERMITIDO` | Método HTTP no soportado por la ruta |
| 409 | `EMAIL_REGISTRADO` | El correo ya existe |
| 409 | `PRODUCTO_DUPLICADO` | Ya existe un producto con ese nombre |
| 409 | `DOCUMENTO_YA_ENTREGADO` | El documento ya se entregó y no está rechazado |
| 422 | `ERROR_VALIDACION` | Cuerpo, query o path inválidos (incluye JSON mal formado) |
| 429 | `LIMITE_PETICIONES_EXCEDIDO` | Se superó el rate limit (header `Retry-After: 60`) |
| 500 | `ERROR_INTERNO` | Error no controlado |

## 4. Máquina de estados de la solicitud

```
borrador ──(expediente completo, automático)──► datos_completos
   │                                              │
   │                       hipoteca ──────────────┼──► en_avaluo ──► avaluo_completado ──┐
   │                       préstamo ──────────────┴──────────────────────────────────────┼──► en_analisis
   ▼                                                                                     │       │
cancelada ◄── (desde borrador, datos_completos, en_avaluo, avaluo_completado,            │       ├─► aprobada ─────┐
               aprobada, condicionada)                                                   │       ├─► condicionada ─┤
                                                                                                  └─► rechazada (final)
aprobada | condicionada ──► oferta_aceptada ──► formalizada (final)
                       └──► oferta_rechazada (final)
```

Estados finales: `rechazada`, `oferta_rechazada`, `formalizada`, `cancelada`. Expediente editable solo en `borrador` y `datos_completos`.
El paso `borrador → datos_completos` es **automático** cuando hay: datos del solicitante + todos los documentos requeridos entregados o validados + inmueble (si es hipoteca).

---

## 5. Endpoints

Abreviaturas: **Rol** público / autenticado / cliente / valuador / analista / admin (admin puede todo).
Todos los errores siguen el formato de la sección 2. Los ejemplos de respuesta muestran solo `data`.

### 5.1 Sistema

#### `GET /health` — público
Estado de la API y de la base de datos.
```json
{ "estado": "ok", "servicio": "API Banco Demo", "version": "1.0.0", "baseDatos": "ok", "fecha": "2026-11-15T21:39:43" }
```
Errores: 429.

### 5.2 Autenticación

#### `POST /auth/login` — público (5/min)
Cuerpo: `{ "email": "cliente11@demo-banco.test", "password": "Demo1234!" }`
```json
{ "accessToken": "eyJhbGciOi...", "tokenType": "bearer", "expiresIn": 3600,
  "usuario": { "id": 16, "codigo": "USR-DEMO-000016", "nombre": "Ana", "apellidos": "López Pérez",
               "email": "cliente11@demo-banco.test", "telefono": "5512345678", "rol": "cliente",
               "activo": true, "creadoEn": "2026-11-15T21:30:00" } }
```
Errores: 401 `CREDENCIALES_INVALIDAS`, 403 `USUARIO_INACTIVO`, 422, 429.

#### `GET /auth/me` — autenticado
Devuelve el objeto `usuario`. Errores: 401 `NO_AUTENTICADO`/`TOKEN_INVALIDO`/`TOKEN_EXPIRADO`, 403 `USUARIO_INACTIVO`.

### 5.3 Usuarios

#### `POST /usuarios/registro` — público → 201
Crea un cliente y una cuenta de débito demo con saldo inicial aleatorio (1,000–50,000).
```json
{ "nombre": "Laura", "apellidos": "Martínez Ruiz", "email": "laura@demo-banco.test", "password": "Segura2026", "telefono": "5511223344" }
```
Respuesta: `{ "usuario": {…}, "cuenta": { "id": 23, "numeroEnmascarado": "****4821", "tipo": "debito", "saldo": 27310.55, "moneda": "MXN", "estado": "activa", "creadaEn": "…" } }`
Errores: 409 `EMAIL_REGISTRADO`, 422 (contraseña: mín. 8 caracteres, una mayúscula y un número; teléfono de 10 a 15 dígitos).

#### `GET /usuarios/perfil` — autenticado
Devuelve el `usuario`. Errores: 401.

#### `PATCH /usuarios/perfil` — autenticado
Cuerpo parcial: `{ "telefono": "5599887766", "nombre": "Ana María", "apellidos": "López" }` → `usuario` actualizado.
Errores: 400 `SIN_CAMBIOS`/`CAMPO_OBLIGATORIO`, 401, 422.

#### `PATCH /usuarios/perfil/password` — autenticado
`{ "passwordActual": "Demo1234!", "passwordNueva": "NuevaClave2026" }` → `{ "id": 16, "estado": null }`
Errores: 400 `PASSWORD_INCORRECTA`/`PASSWORD_REPETIDA`, 401, 422.

### 5.4 Administración (admin)

#### `GET /admin/usuarios` — paginado
Query: `rol` (cliente|valuador|analista|admin), `activo` (bool), `busqueda` (2–80 caracteres; nombre, apellidos, email, código), `page`, `limit`.
Respuesta: lista de `usuario` + `meta`. Errores: 401, 403, 422.

#### `GET /admin/usuarios/{id}`
Errores: 401, 403, 404 `USUARIO_NO_ENCONTRADO`.

#### `POST /admin/usuarios` → 201
`{ "nombre": "Jorge", "apellidos": "Valdez Soto", "email": "valuador3@demo-banco.test", "password": "Valuador2026", "telefono": "5544332211", "rol": "valuador" }`
`rol` ∈ valuador | analista | admin. Errores: 401, 403, 409 `EMAIL_REGISTRADO`, 422.

#### `PATCH /admin/usuarios/{id}/estado`
`{ "activo": false }` → `usuario`. Errores: 400 `OPERACION_NO_PERMITIDA`, 401, 403, 404, 422.

#### `GET /admin/estadisticas`
```json
{ "totalSolicitudes": 10,
  "solicitudesPorEstado": { "borrador": 1, "datos_completos": 1, "en_avaluo": 1, "avaluo_completado": 1, "en_analisis": 0,
    "aprobada": 1, "condicionada": 1, "rechazada": 1, "oferta_aceptada": 1, "oferta_rechazada": 0, "formalizada": 1, "cancelada": 1 },
  "solicitudesPorTipo": { "prestamo": 6, "hipoteca": 4 },
  "montoTotalAprobado": 2643900.0, "solicitudesResueltas": 5, "solicitudesFavorables": 4, "tasaAprobacionPct": 80.0,
  "usuariosPorRol": { "cliente": 15, "valuador": 2, "analista": 2, "admin": 1 }, "totalCuentas": 22 }
```
`montoTotalAprobado` suma aprobada, condicionada, oferta_aceptada y formalizada. Tasa = favorables / (favorables + rechazadas) × 100. Errores: 401, 403.

### 5.5 Productos

Objeto `producto`:
```json
{ "id": 4, "nombre": "Hipoteca Fija Demo", "tipo": "hipoteca", "descripcion": "…", "tasaAnual": 10.5,
  "montoMin": 500000.0, "montoMax": 5000000.0, "plazosMeses": [120, 180, 240], "engancheMinPct": 10.0,
  "documentosRequeridos": ["identificacion", "comprobante_domicilio", "comprobante_ingresos", "estados_cuenta", "escrituras", "predial"],
  "requisitos": ["Ser mayor de 18 años y menor de 70 al terminar el plazo", "…"], "condiciones": "…", "activo": true }
```

| Método y ruta | Rol | Notas | Errores |
|---|---|---|---|
| `GET /productos` | público | Query `tipo`, `activo`. Sin `activo` solo devuelve los activos | 422 |
| `GET /productos/{id}` | público | | 404 `PRODUCTO_NO_ENCONTRADO`, 422 |
| `GET /productos/{id}/requisitos` | público | `{productoId, nombre, tipo, requisitos, documentosRequeridos:[{tipo, descripcion}], engancheMinPct, montoMin, montoMax, plazosMeses, condiciones}` | 404 |
| `POST /productos` | admin | 201. Cuerpo = producto sin `id` | 401, 403, 409 `PRODUCTO_DUPLICADO`, 422 |
| `PUT /productos/{id}` | admin | Reemplazo completo | 401, 403, 404, 409, 422 |
| `DELETE /productos/{id}` | admin | 204. Borrado lógico (`activo=false`) | 401, 403, 404 |

Validaciones de `POST`/`PUT`: `montoMin < montoMax`; plazos entre 1 y 480 sin repetir; hipoteca exige `engancheMinPct`; préstamo no admite `engancheMinPct` ni los documentos `escrituras`/`predial`.

Ejemplo de cuerpo:
```json
{ "nombre": "Préstamo Auto Demo", "tipo": "prestamo", "descripcion": "Préstamo demostrativo para auto.", "tasaAnual": 16.9,
  "montoMin": 30000, "montoMax": 400000, "plazosMeses": [12, 24, 36, 48], "engancheMinPct": null,
  "documentosRequeridos": ["identificacion", "comprobante_domicilio", "comprobante_ingresos"],
  "requisitos": ["Ser mayor de edad"], "condiciones": "Tasa fija. Producto demostrativo.", "activo": true }
```

### 5.6 Simuladores (públicos)

#### `POST /simuladores/prestamo`
`{ "monto": 50000, "tasaAnual": 18.5, "plazoMeses": 24 }` o `{ "monto": 80000, "productoId": 2, "plazoMeses": 36 }`
```json
{ "monto": 50000.0, "tasaAnual": 18.5, "plazoMeses": 24, "mensualidad": 2508.3, "totalIntereses": 10199.24,
  "totalPagar": 60199.24, "catDemo": 20.65, "productoId": null, "productoNombre": null,
  "leyenda": "SIMULACIÓN DEMOSTRATIVA - NO ES UNA OFERTA REAL" }
```
Con `productoId` se valida el producto, su tipo, el monto y el plazo. Errores: 400 `MONTO_FUERA_DE_RANGO`/`PLAZO_NO_PERMITIDO`/`TIPO_PRODUCTO_INVALIDO`/`PRODUCTO_INACTIVO`, 404, 422 (requiere `tasaAnual` o `productoId`).

#### `POST /simuladores/hipoteca`
`{ "valorInmueble": 2500000, "enganche": 500000, "productoId": 4, "plazoMeses": 240 }`
Agrega a la respuesta del préstamo: `valorInmueble`, `enganche`, `enganchePct`, `engancheMinPct` (del producto, del cuerpo o 10% por defecto), `engancheMinimo`, `cumpleEngancheMinimo` (bool) y `mensajeEnganche`. El monto del crédito es `valorInmueble − enganche`.
Errores: igual que préstamo; 422 si `enganche ≥ valorInmueble`.

#### `POST /simuladores/amortizacion`
`{ "monto": 50000, "tasaAnual": 18.5, "plazoMeses": 12 }`
```json
{ "monto": 50000.0, "tasaAnual": 18.5, "plazoMeses": 12, "mensualidad": 4595.91, "totalIntereses": 5150.85, "totalPagar": 55150.85,
  "tabla": [ { "numero": 1, "pago": 4595.91, "capital": 3825.08, "interes": 770.83, "saldo": 46174.92, "fechaPago": null }, "…",
             { "numero": 12, "pago": 4595.84, "capital": 4526.06, "interes": 69.78, "saldo": 0.0, "fechaPago": null } ],
  "leyenda": "SIMULACIÓN DEMOSTRATIVA - NO ES UNA OFERTA REAL" }
```
Errores: 422.

### 5.7 Solicitudes

Objeto **detalle de solicitud** (lo devuelven todas las acciones que cambian estado):
```json
{ "id": 11, "folio": "SOL-DEMO-2026-000011", "usuarioId": 16,
  "producto": { "id": 4, "nombre": "Hipoteca Fija Demo", "tipo": "hipoteca", "tasaAnual": 10.5 },
  "tipo": "hipoteca", "montoSolicitado": 1800000.0, "plazoMeses": 240, "valorInmueble": 2500000.0, "enganche": 700000.0,
  "estado": "aprobada", "puntajeBuro": 792,
  "resultadoAnalisis": { "resolucion": "aprobada",
     "reglas": [ { "regla": "capacidad_pago", "descripcion": "…", "valor": 21.51, "limite": 35.0, "cumple": true },
                 { "regla": "ltv", "valor": 76.56, "limite": 90.0, "cumple": true },
                 { "regla": "buro", "valor": 792, "limite": 600, "cumple": true },
                 { "regla": "antiguedad_laboral", "valor": 60, "limite": 6, "cumple": true },
                 { "regla": "edad_fin_plazo", "valor": 58, "limite": 70, "cumple": true } ],
     "puntajeBuro": 792, "ingresoNeto": 78000.0, "pagoMaximo": 27300.0, "mensualidadSolicitada": 16778.36,
     "tasaAplicada": 9.5, "fechaAnalisis": "2026-11-15" },
  "montoAprobado": 1800000.0, "tasaAprobada": 9.5, "plazoAprobado": 240, "mensualidadAprobada": 16778.36,
  "engancheRequerido": 700000.0, "motivoResolucion": "Solicitud aprobada: cumple todas las reglas del análisis.",
  "creadaEn": "…", "actualizadaEn": "…", "resueltaEn": "…", "formalizadaEn": null,
  "solicitante": { }, "inmueble": { "…": "…", "avaluo": { } },
  "documentos": [ { "tipo": "identificacion", "descripcion": "…", "estado": "entregado", "documentoId": 31,
                    "nombreArchivoSimulado": "identificacion.pdf", "observaciones": null, "fecha": "…" } ],
  "progreso": { "porcentaje": 80, "solicitanteCompleto": true, "documentosRequeridos": ["…"], "documentosEntregados": ["…"],
                "documentosPendientes": [], "documentosRechazados": [], "inmuebleRequerido": true, "inmuebleRegistrado": true,
                "avaluoRequerido": true, "avaluoEstado": "completado", "editable": false,
                "siguientePaso": "Revisar la oferta y aceptarla o rechazarla" } }
```

| Método y ruta | Rol | Descripción | Errores |
|---|---|---|---|
| `POST /solicitudes` | cliente | 201. Crea en `borrador` | 400 `PRODUCTO_INACTIVO`, `LIMITE_SOLICITUDES`, `MONTO_FUERA_DE_RANGO`, `PLAZO_NO_PERMITIDO`, `VALOR_INMUEBLE_REQUERIDO`, `MONTO_EXCEDE_VALOR`, `ENGANCHE_INSUFICIENTE`; 401; 403; 404 `PRODUCTO_NO_ENCONTRADO`; 422 |
| `GET /solicitudes` | cliente (las suyas), analista/admin (todas) | Paginado; query `estado`, `tipo`. Devuelve un resumen sin expediente | 401, 403 (valuador), 422 |
| `GET /solicitudes/{id}` | dueño, analista, admin, valuador asignado | Detalle + progreso | 401, 403 `ACCESO_DENEGADO`, 404 |
| `POST /solicitudes/{id}/cancelar` | cliente dueño | Cuerpo opcional `{ "motivo": "…" }` | 400 `TRANSICION_INVALIDA`, 401, 403, 404, 422 |
| `GET /solicitudes/{id}/historial` | igual que el detalle | `[{id, estadoAnterior, estadoNuevo, usuarioId, nota, fecha}]` | 401, 403, 404 |
| `POST /solicitudes/{id}/analisis` | cliente dueño o analista | Préstamo desde `datos_completos`; hipoteca desde `avaluo_completado`. Resuelve en la misma llamada | 400 `TRANSICION_INVALIDA`, `DOCUMENTOS_RECHAZADOS`, `AVALUO_PENDIENTE`; 401; 403; 404 |
| `PATCH /solicitudes/{id}/resolucion` | analista | Sobrescribe la resolución | 400 `RESOLUCION_NO_EDITABLE`, `MONTO_FUERA_DE_RANGO`, `PLAZO_NO_PERMITIDO`, `MONTO_EXCEDE_VALOR`; 401; 403; 404; 422 |
| `GET /solicitudes/{id}/oferta` | cliente dueño | Oferta (ver abajo) | 400 `OFERTA_NO_DISPONIBLE`, 401, 403, 404 |
| `POST /solicitudes/{id}/oferta/aceptar` | cliente dueño | → `oferta_aceptada` | 400 `TRANSICION_INVALIDA`, `OFERTA_VENCIDA`; 401; 403; 404 |
| `POST /solicitudes/{id}/oferta/rechazar` | cliente dueño | → `oferta_rechazada`; motivo opcional | 400, 401, 403, 404, 422 |
| `POST /solicitudes/{id}/formalizar` | cliente dueño | → `formalizada`, fija `formalizadaEn`; en préstamos deposita el monto en la cuenta demo | 400, 401, 403, 404 |
| `GET /solicitudes/{id}/amortizacion` | cliente dueño | Tabla con `fechaPago` (mensual desde la formalización) | 400 `CREDITO_NO_FORMALIZADO`, 401, 403, 404 |

Cuerpo de `POST /solicitudes`:
```json
{ "productoId": 4, "montoSolicitado": 1800000, "plazoMeses": 240, "valorInmueble": 2500000 }
```
En préstamos `valorInmueble` se ignora.

Cuerpo de `PATCH /resolucion`:
```json
{ "estado": "aprobada", "monto": 1700000, "tasa": 10.0, "plazo": 240, "motivo": "Revisión manual: ingresos adicionales comprobados." }
```
`estado` ∈ aprobada | condicionada | rechazada. Los campos omitidos conservan el valor anterior (o el solicitado). `rechazada` limpia monto, tasa, plazo y mensualidad. Queda constancia en `resultadoAnalisis.sobrescritura` y en el historial.

Respuesta de `GET /oferta`:
```json
{ "solicitudId": 11, "folio": "SOL-DEMO-2026-000011", "estado": "aprobada", "producto": "Hipoteca Fija Demo",
  "monto": 1800000.0, "tasaAnual": 9.5, "plazoMeses": 240, "mensualidad": 16778.36, "totalPagar": 4026807.27,
  "totalIntereses": 2226807.27, "catDemo": 9.97, "engancheRequerido": 700000.0, "condicionada": false,
  "condiciones": "Solicitud aprobada: …", "fechaEmision": "2026-11-15T21:39:45", "vigenteHasta": "2026-11-30T21:39:45",
  "vigente": true, "leyenda": "OFERTA DEMOSTRATIVA - NO ES UNA OFERTA REAL" }
```

### 5.8 Expediente

| Método y ruta | Rol | Descripción | Errores |
|---|---|---|---|
| `PUT /solicitudes/{id}/solicitante` | cliente dueño | Crea o reemplaza los datos; puede avanzar a `datos_completos` | 400 `SOLICITUD_NO_EDITABLE`, `EDAD_INSUFICIENTE`, `EDAD_EXCEDE_PLAZO`, `FECHA_NACIMIENTO_INVALIDA`; 401; 403; 404; 422 |
| `GET /solicitudes/{id}/solicitante` | dueño, analista, admin, valuador asignado | | 401, 403, 404 `SOLICITANTE_NO_REGISTRADO` |
| `GET /solicitudes/{id}/documentos` | igual | Todos los documentos requeridos, con estado `pendiente`/`entregado`/`validado`/`rechazado` | 401, 403, 404 |
| `POST /solicitudes/{id}/documentos` | cliente dueño | 201. Entrega simulada; si estaba rechazado, lo reemplaza | 400 `DOCUMENTO_NO_REQUERIDO`, `SOLICITUD_NO_EDITABLE`; 401; 403; 404; 409 `DOCUMENTO_YA_ENTREGADO`; 422 |
| `PATCH /solicitudes/{id}/documentos/{docId}` | analista | `{ "estado": "rechazado", "observaciones": "Ilegible" }` (observaciones obligatorias al rechazar) | 400 `SOLICITUD_FINALIZADA`, 401, 403, 404 `DOCUMENTO_NO_ENCONTRADO`, 422 |

Cuerpo de `PUT /solicitante`:
```json
{ "fechaNacimiento": "1990-04-15", "curpFicticia": "DEMO900415HDFXXX01", "estadoCivil": "casado", "dependientes": 2,
  "domicilio": "Av. Demo 123, Col. Centro", "ciudad": "Ciudad de México", "empresa": "Empresa Demo SA de CV",
  "puesto": "Ingeniero de software", "tipoEmpleo": "asalariado", "antiguedadMeses": 48, "ingresoMensual": 65000,
  "otrosIngresos": 5000, "gastosMensuales": 20000, "deudasMensuales": 3000,
  "referencias": [ { "nombre": "María Gómez", "telefono": "5511112222", "relacion": "hermana" },
                   { "nombre": "Pedro Ruiz", "telefono": "5533334444", "relacion": "amigo" } ] }
```
Validaciones: CURP ficticia de 18 caracteres alfanuméricos en mayúsculas; `estadoCivil` ∈ soltero|casado|divorciado|viudo|union_libre; `tipoEmpleo` ∈ asalariado|independiente; `ingresoMensual > 0`; de 2 a 5 referencias con teléfonos distintos. Una antigüedad menor a 6 meses se acepta (el análisis la penaliza).

Cuerpo de `POST /documentos`: `{ "tipo": "identificacion", "nombreArchivoSimulado": "ine_demo.pdf" }` (extensión .pdf, .jpg, .jpeg o .png).

### 5.9 Evaluación del inmueble

| Método y ruta | Rol | Descripción | Errores |
|---|---|---|---|
| `PUT /solicitudes/{id}/inmueble` | cliente dueño | Solo hipoteca; crea o reemplaza; puede avanzar a `datos_completos` | 400 `SOLO_HIPOTECA`, `SOLICITUD_NO_EDITABLE`; 401; 403; 404; 422 |
| `GET /solicitudes/{id}/inmueble` | dueño, analista, admin, valuador asignado | Incluye `avaluo` | 400 `SOLO_HIPOTECA`, 401, 403, 404 `INMUEBLE_NO_REGISTRADO` |
| `POST /solicitudes/{id}/avaluo` | cliente dueño o analista | 201. Asigna valuador y genera el resultado → `avaluo_completado` | 400 `TRANSICION_INVALIDA`, `SOLO_HIPOTECA`, `DOCUMENTOS_RECHAZADOS`, `SIN_VALUADORES`; 401; 403; 404 |
| `GET /avaluos` | valuador (asignados), analista/admin (todos) | Paginado; query `estado` | 401, 403, 422 |
| `GET /avaluos/{id}` | valuador asignado, cliente dueño, analista, admin | | 401, 403, 404 `AVALUO_NO_ENCONTRADO` |
| `PATCH /avaluos/{id}/resultado` | valuador asignado | `{ "valorComercial": 2380000, "estadoConservacion": "bueno", "observaciones": "…" }` → `generadoAutomaticamente=false` | 400 `AVALUO_NO_EDITABLE`, 401, 403, 404, 422 |

Cuerpo de `PUT /inmueble`:
```json
{ "tipo": "casa", "direccion": "Calle Demo 45", "colonia": "Del Valle", "ciudad": "Ciudad de México",
  "estado": "Ciudad de México", "cp": "03100", "m2Terreno": 160, "m2Construccion": 140, "antiguedadAnios": 8,
  "recamaras": 3, "banos": 2, "valorEstimadoCliente": 2500000 }
```

Respuesta de `POST /avaluo`:
```json
{ "id": 5, "folio": "AVA-DEMO-2026-000005", "inmuebleId": 6, "solicitudId": 11, "valuadorId": 2, "valuadorNombre": "…",
  "estado": "completado", "fechaSolicitud": "…", "fechaVisita": "…", "valorComercial": 2351250.0,
  "estadoConservacion": "bueno", "observaciones": "Avalúo DEMO generado automáticamente…", "generadoAutomaticamente": true }
```
Regla automática: `valorComercial = valorEstimadoCliente × factor` (factor reproducible entre 0.85 y 1.05, con semilla en el id de la solicitud). Conservación según antigüedad: ≤5 años excelente, ≤15 bueno, ≤30 regular, >30 malo.

### 5.10 Cuentas (cliente; admin ve todas)

| Método y ruta | Descripción | Errores |
|---|---|---|
| `GET /cuentas` | Cuentas propias | 401, 403 |
| `GET /cuentas/{id}` | `{id, numeroEnmascarado: "****7712", tipo, saldo, moneda, estado, creadaEn}` | 401, 403 `ACCESO_DENEGADO`, 404 `CUENTA_NO_ENCONTRADA` |
| `GET /cuentas/{id}/movimientos` | Paginado, del más reciente al más antiguo; query `desde`, `hasta` (AAAA-MM-DD) y `tipo` (deposito\|retiro\|pago\|compra\|transferencia) | 400 `RANGO_FECHAS_INVALIDO`, 401, 403, 404, 422 |

Movimiento:
```json
{ "id": 10, "tipo": "compra", "concepto": "Compra en Supermercado Demo", "monto": -850.0, "saldoResultante": 14380.5,
  "referencia": "MOV-DEMO-20261101-A1B2C3D4", "fecha": "2026-11-01T18:22:00" }
```
El número de cuenta completo **nunca** aparece en las respuestas.
