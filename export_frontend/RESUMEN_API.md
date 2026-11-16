# Resumen de la API Banco Demo para Frontend

> Generado automáticamente el 2026-11-15 21:04 a partir del código fuente (`app/`), del esquema OpenAPI del servidor en ejecución y de **peticiones HTTP reales** contra la API levantada con los datos del seed. Todos los datos son ficticios.

**Cómo se obtuvo cada sección:**

- La lista de endpoints, los roles, los parámetros y las reglas de validación se leyeron por introspección de FastAPI y Pydantic (`app.routes` y `model_fields`).
- Los códigos de error y los endpoints donde ocurren salen del análisis estático (AST) de cada `ApiError` y de las llamadas entre funciones.
- Los ejemplos de respuesta son respuestas reales de `uvicorn app.main:app` en el puerto 8000. Las peticiones se hicieron sobre una **copia temporal** de la BD sembrada con `python -m seeds.seed`, así que `banco_demo.db` no se modificó.

Contenido: [a) Datos generales](#a-datos-generales) · [b) Endpoints](#b-tabla-de-endpoints) · [c) Cuerpos de petición](#c-cuerpos-de-petición) · [d) Respuestas reales](#d-respuestas-exitosas-reales) · [e) Errores](#e-catálogo-de-códigos-de-error) · [f) Enums](#f-enums) · [g) Máquina de estados](#g-máquina-de-estados) · [h) Reglas de negocio](#h-reglas-de-negocio) · [i) Datos del seed](#i-datos-del-seed) · [j) Diferencias](#j-diferencias-con-el-prompt-original)

## a) Datos generales

| Concepto | Valor (del código) |
|---|---|
| URL base | `http://localhost:8000/api/v1` |
| Prefijo | `/api/v1` (`Settings.API_PREFIX`) |
| Puerto | `8000` (comando de ejecución documentado) |
| Ejecutar | `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` |
| Seed | `python -m seeds.seed` (borra y recrea la BD) |
| Pruebas | `python -m pytest` |
| Swagger / ReDoc / OpenAPI | `/docs`, `/redoc`, `/openapi.json` (si `DOCS_ENABLED=true`) |
| Duración del token | `60` minutos (`JWT_EXPIRE_MINUTES`); algoritmo `HS256`; payload `sub` (id) y `rol`; header `Authorization: Bearer <token>` |
| Rate limit login | `5/minute` por IP (`RATE_LIMIT_LOGIN`) |
| Rate limit general | `100/minute` por IP (`RATE_LIMIT_DEFAULT`) |
| Formato JSON | salida camelCase; la entrada acepta camelCase o snake_case; los textos se recortan (strip) |
| Dinero | número con 2 decimales en JSON; `Decimal` en el servidor |
| Fechas | ISO 8601 en UTC sin zona (`2026-11-15T21:39:45`, fechas `AAAA-MM-DD`) |

Variables de `.env.example`:

| Variable | Valor en `.env.example` | Valor por defecto en código |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./banco_demo.db` | `sqlite:///<raíz>/banco_demo.db` |
| `JWT_SECRET` | `cambie-este-secreto-por-uno-largo-y-aleatorio` | `(aleatorio en cada arranque)` |
| `JWT_EXPIRE_MINUTES` | `60` | `60` |
| `CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | `http://localhost:3000,http://127.0.0.1:3000` |
| `ALLOWED_NETWORKS` | vacío | vacío |
| `DOCS_ENABLED` | `true` | `True` |
| `RATE_LIMIT_LOGIN` | `5/minute` | `5/minute` |
| `RATE_LIMIT_DEFAULT` | `100/minute` | `100/minute` |

Otras variables que también acepta `Settings` (no están en `.env.example`): `APP_NAME`, `APP_VERSION`, `API_PREFIX`, `JWT_ALGORITHM`, `BCRYPT_ROUNDS`, `RATE_LIMIT_ENABLED`, `MAX_SOLICITUDES_ACTIVAS`, `OFERTA_VIGENCIA_DIAS`, `EDAD_MINIMA`, `EDAD_MAXIMA_FIN_PLAZO`, `REFERENCIAS_MINIMAS`, `ANALISIS_MAX_RELACION_PAGO`, `ANALISIS_MAX_LTV`, `ANALISIS_BURO_MINIMO`, `ANALISIS_BURO_PREFERENTE`, `ANALISIS_DESCUENTO_PREFERENTE`, `ANALISIS_ANTIGUEDAD_MIN_MESES`, `ANALISIS_REDONDEO_MONTO_CONDICIONADO`, `AVALUO_FACTOR_MIN`, `AVALUO_FACTOR_MAX`, `CAT_COMISION_APERTURA_PCT`.

**Sobre del éxito:** `{ "ok": true, "message": "...", "data": ..., "demo": true }`, con `"meta": { "page", "limit", "total" }` solo en las listas paginadas.

**Sobre del error:** `{ "ok": false, "error": { "code", "message", "details": [] }, "demo": true }`. En un 422, `details` es una lista de `{ "campo", "mensaje" }`.

## b) Tabla de endpoints

**Total: 47 endpoints** (método + ruta) en 38 rutas distintas.

La columna «Roles» viene de la dependencia de cada endpoint: `require_roles(...)` deja pasar siempre a admin, y `get_usuario_actual` acepta cualquier rol autenticado. La columna «Verificación en servicio» indica qué pertenencia se comprueba después; si falla, el endpoint responde 403 `ACCESO_DENEGADO`.

| # | Método | Ruta | Roles (dependencia) | Verificación en servicio | Descripción | Parámetros de ruta | Query | Paginado | Status éxito |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `GET` | `/api/v1/health` | público | — | Estado de la API | — | — | no | 200 |
| 2 | `POST` | `/api/v1/auth/login` | público | — | Iniciar sesión | — | — | no | 200 |
| 3 | `GET` | `/api/v1/auth/me` | autenticado (cualquier rol) | — | Usuario autenticado | — | — | no | 200 |
| 4 | `POST` | `/api/v1/usuarios/registro` | público | — | Registro de cliente | — | — | no | 201 |
| 5 | `GET` | `/api/v1/usuarios/perfil` | autenticado (cualquier rol) | — | Consultar perfil | — | — | no | 200 |
| 6 | `PATCH` | `/api/v1/usuarios/perfil` | autenticado (cualquier rol) | — | Actualizar perfil | — | — | no | 200 |
| 7 | `PATCH` | `/api/v1/usuarios/perfil/password` | autenticado (cualquier rol) | — | Cambiar contraseña | — | — | no | 200 |
| 8 | `GET` | `/api/v1/admin/usuarios` | `admin` | — | Listar usuarios | — | `rol` (enum: `cliente` \| `valuador` \| `analista` \| `admin`)<br>`activo` (booleano)<br>`busqueda` (texto; longitud mínima 2; longitud máxima 80)<br>`page` (entero; ≥ 1; def. 1)<br>`limit` (entero; ≥ 1; ≤ 100; def. 10) | sí | 200 |
| 9 | `GET` | `/api/v1/admin/usuarios/{usuario_id}` | `admin` | — | Detalle de usuario | `usuario_id` (entero) | — | no | 200 |
| 10 | `POST` | `/api/v1/admin/usuarios` | `admin` | — | Crear personal interno | — | — | no | 201 |
| 11 | `PATCH` | `/api/v1/admin/usuarios/{usuario_id}/estado` | `admin` | — | Activar o desactivar usuario | `usuario_id` (entero) | — | no | 200 |
| 12 | `GET` | `/api/v1/admin/estadisticas` | `admin` | — | Estadísticas generales | — | — | no | 200 |
| 13 | `GET` | `/api/v1/productos` | público | — | Catálogo de productos | — | `tipo` (enum: `prestamo` \| `hipoteca`)<br>`activo` (booleano) | no | 200 |
| 14 | `GET` | `/api/v1/productos/{producto_id}` | público | — | Detalle de producto | `producto_id` (entero) | — | no | 200 |
| 15 | `GET` | `/api/v1/productos/{producto_id}/requisitos` | público | — | Requisitos del producto | `producto_id` (entero) | — | no | 200 |
| 16 | `POST` | `/api/v1/productos` | `admin` | — | Crear producto | — | — | no | 201 |
| 17 | `PUT` | `/api/v1/productos/{producto_id}` | `admin` | — | Reemplazar producto | `producto_id` (entero) | — | no | 200 |
| 18 | `DELETE` | `/api/v1/productos/{producto_id}` | `admin` | — | Desactivar producto | `producto_id` (entero) | — | no | 204 |
| 19 | `POST` | `/api/v1/simuladores/prestamo` | público | — | Simular préstamo | — | — | no | 200 |
| 20 | `POST` | `/api/v1/simuladores/hipoteca` | público | — | Simular hipoteca | — | — | no | 200 |
| 21 | `POST` | `/api/v1/simuladores/amortizacion` | público | — | Tabla de amortización | — | — | no | 200 |
| 22 | `POST` | `/api/v1/solicitudes` | `cliente` + `admin` (implícito) | — | Crear solicitud | — | — | no | 201 |
| 23 | `GET` | `/api/v1/solicitudes` | `cliente`, `analista` + `admin` (implícito) | cliente: solo las suyas; analista/admin: todas | Listar solicitudes | — | `estado` (enum: `borrador` \| `datos_completos` \| `en_avaluo` \| `avaluo_completado` \| `en_analisis` \| `aprobada` \| `condicionada` \| `rechazada` \| `oferta_aceptada` \| `oferta_rechazada` \| `formalizada` \| `cancelada`)<br>`tipo` (enum: `prestamo` \| `hipoteca`)<br>`page` (entero; ≥ 1; def. 1)<br>`limit` (entero; ≥ 1; ≤ 100; def. 10) | sí | 200 |
| 24 | `GET` | `/api/v1/solicitudes/{solicitud_id}` | autenticado (cualquier rol) | dueño, analista/admin o valuador asignado | Detalle de solicitud | `solicitud_id` (entero) | — | no | 200 |
| 25 | `POST` | `/api/v1/solicitudes/{solicitud_id}/cancelar` | `cliente` + `admin` (implícito) | dueño de la solicitud (admin pasa) | Cancelar solicitud | `solicitud_id` (entero) | — | no | 200 |
| 26 | `GET` | `/api/v1/solicitudes/{solicitud_id}/historial` | autenticado (cualquier rol) | dueño, analista/admin o valuador asignado | Historial de estados | `solicitud_id` (entero) | — | no | 200 |
| 27 | `POST` | `/api/v1/solicitudes/{solicitud_id}/analisis` | `cliente`, `analista` + `admin` (implícito) | dueño, o analista/admin | Ejecutar análisis de crédito | `solicitud_id` (entero) | — | no | 200 |
| 28 | `PATCH` | `/api/v1/solicitudes/{solicitud_id}/resolucion` | `analista` + `admin` (implícito) | — | Sobrescribir resolución | `solicitud_id` (entero) | — | no | 200 |
| 29 | `GET` | `/api/v1/solicitudes/{solicitud_id}/oferta` | `cliente` + `admin` (implícito) | dueño de la solicitud (admin pasa) | Consultar oferta | `solicitud_id` (entero) | — | no | 200 |
| 30 | `POST` | `/api/v1/solicitudes/{solicitud_id}/oferta/aceptar` | `cliente` + `admin` (implícito) | dueño de la solicitud (admin pasa) | Aceptar oferta | `solicitud_id` (entero) | — | no | 200 |
| 31 | `POST` | `/api/v1/solicitudes/{solicitud_id}/oferta/rechazar` | `cliente` + `admin` (implícito) | dueño de la solicitud (admin pasa) | Rechazar oferta | `solicitud_id` (entero) | — | no | 200 |
| 32 | `POST` | `/api/v1/solicitudes/{solicitud_id}/formalizar` | `cliente` + `admin` (implícito) | dueño de la solicitud (admin pasa) | Formalizar crédito | `solicitud_id` (entero) | — | no | 200 |
| 33 | `GET` | `/api/v1/solicitudes/{solicitud_id}/amortizacion` | `cliente` + `admin` (implícito) | dueño de la solicitud (admin pasa) | Tabla de amortización del crédito | `solicitud_id` (entero) | — | no | 200 |
| 34 | `PUT` | `/api/v1/solicitudes/{solicitud_id}/solicitante` | `cliente` + `admin` (implícito) | dueño de la solicitud (admin pasa) | Guardar datos del solicitante | `solicitud_id` (entero) | — | no | 200 |
| 35 | `GET` | `/api/v1/solicitudes/{solicitud_id}/solicitante` | autenticado (cualquier rol) | dueño, analista/admin o valuador asignado | Consultar datos del solicitante | `solicitud_id` (entero) | — | no | 200 |
| 36 | `GET` | `/api/v1/solicitudes/{solicitud_id}/documentos` | autenticado (cualquier rol) | dueño, analista/admin o valuador asignado | Documentos requeridos y su estado | `solicitud_id` (entero) | — | no | 200 |
| 37 | `POST` | `/api/v1/solicitudes/{solicitud_id}/documentos` | `cliente` + `admin` (implícito) | dueño de la solicitud (admin pasa) | Entregar documento simulado | `solicitud_id` (entero) | — | no | 201 |
| 38 | `PATCH` | `/api/v1/solicitudes/{solicitud_id}/documentos/{documento_id}` | `analista` + `admin` (implícito) | — | Validar o rechazar documento | `solicitud_id` (entero)<br>`documento_id` (entero) | — | no | 200 |
| 39 | `PUT` | `/api/v1/solicitudes/{solicitud_id}/inmueble` | `cliente` + `admin` (implícito) | dueño de la solicitud (admin pasa) | Registrar inmueble | `solicitud_id` (entero) | — | no | 200 |
| 40 | `GET` | `/api/v1/solicitudes/{solicitud_id}/inmueble` | autenticado (cualquier rol) | dueño, analista/admin o valuador asignado | Consultar inmueble | `solicitud_id` (entero) | — | no | 200 |
| 41 | `POST` | `/api/v1/solicitudes/{solicitud_id}/avaluo` | `cliente`, `analista` + `admin` (implícito) | dueño, o analista/admin | Solicitar avalúo | `solicitud_id` (entero) | — | no | 201 |
| 42 | `GET` | `/api/v1/avaluos` | `valuador`, `analista` + `admin` (implícito) | valuador: solo asignados; analista/admin: todos | Listar avalúos | — | `estado` (enum: `solicitado` \| `completado`)<br>`page` (entero; ≥ 1; def. 1)<br>`limit` (entero; ≥ 1; ≤ 100; def. 10) | sí | 200 |
| 43 | `GET` | `/api/v1/avaluos/{avaluo_id}` | autenticado (cualquier rol) | valuador asignado, cliente dueño, analista/admin | Detalle de avalúo | `avaluo_id` (entero) | — | no | 200 |
| 44 | `PATCH` | `/api/v1/avaluos/{avaluo_id}/resultado` | `valuador` + `admin` (implícito) | valuador asignado (admin pasa) | Ajustar resultado del avalúo | `avaluo_id` (entero) | — | no | 200 |
| 45 | `GET` | `/api/v1/cuentas` | `cliente` + `admin` (implícito) | solo cuentas propias (admin ve todas) | Mis cuentas | — | — | no | 200 |
| 46 | `GET` | `/api/v1/cuentas/{cuenta_id}` | `cliente` + `admin` (implícito) | dueño de la cuenta (admin pasa) | Detalle de cuenta | `cuenta_id` (entero) | — | no | 200 |
| 47 | `GET` | `/api/v1/cuentas/{cuenta_id}/movimientos` | `cliente` + `admin` (implícito) | dueño de la cuenta (admin pasa) | Movimientos de la cuenta | `cuenta_id` (entero) | `desde` (fecha `AAAA-MM-DD`)<br>`hasta` (fecha `AAAA-MM-DD`)<br>`tipo` (enum: `deposito` \| `retiro` \| `pago` \| `compra` \| `transferencia`)<br>`page` (entero; ≥ 1; def. 1)<br>`limit` (entero; ≥ 1; ≤ 100; def. 10) | sí | 200 |

## c) Cuerpos de petición

Cada ejemplo es **el cuerpo exacto que se envió** en la petición real de la sección d). Las reglas salen de los modelos Pydantic (`model_fields` y metadatos) y de los `ValueError` de sus validadores.

### `POST /api/v1/auth/login` — esquema `LoginIn`

Cuerpo obligatorio.

```json
{
  "email": "cliente11@demo-banco.test",
  "password": "Demo1234!"
}
```

| Campo | Tipo | Obligatorio | Reglas |
|---|---|---|---|
| `email` | texto | sí | longitud mínima 5; longitud máxima 160; validador: Valida el formato del correo (sin DNS) y lo normaliza a minúsculas. |
| `password` | texto | sí | longitud mínima 1; longitud máxima 72 |

### `POST /api/v1/usuarios/registro` — esquema `RegistroIn`

Cuerpo obligatorio.

```json
{
  "nombre": "Laura",
  "apellidos": "Martínez Ruiz",
  "email": "laura.frontend@demo-banco.test",
  "password": "Segura2026",
  "telefono": "5511223344"
}
```

| Campo | Tipo | Obligatorio | Reglas |
|---|---|---|---|
| `nombre` | texto | sí | longitud mínima 2; longitud máxima 80; patrón `^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ' .-]+$` |
| `apellidos` | texto | sí | longitud mínima 2; longitud máxima 120; patrón `^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ' .-]+$` |
| `email` | texto | sí | longitud mínima 5; longitud máxima 160; validador: Valida el formato del correo (sin DNS) y lo normaliza a minúsculas. |
| `password` | texto | sí | longitud máxima 72 |
| `telefono` | texto | no | patrón `^\+?[0-9]{10,15}$`; por defecto `null`; admite `null` |

Validaciones entre campos y validadores propios (responden 422 con estos mensajes):

- La contraseña debe tener al menos 8 caracteres
- La contraseña debe contener al menos una letra mayúscula
- La contraseña debe contener al menos un número

### `PATCH /api/v1/usuarios/perfil` — esquema `PerfilUpdateIn`

Cuerpo obligatorio.

```json
{
  "telefono": "5599887766"
}
```

| Campo | Tipo | Obligatorio | Reglas |
|---|---|---|---|
| `nombre` | texto | no | longitud mínima 2; longitud máxima 80; patrón `^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ' .-]+$`; por defecto `null`; admite `null` |
| `apellidos` | texto | no | longitud mínima 2; longitud máxima 120; patrón `^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ' .-]+$`; por defecto `null`; admite `null` |
| `telefono` | texto | no | patrón `^\+?[0-9]{10,15}$`; por defecto `null`; admite `null` |

### `PATCH /api/v1/usuarios/perfil/password` — esquema `PasswordUpdateIn`

Cuerpo obligatorio.

```json
{
  "passwordActual": "Segura2026",
  "passwordNueva": "NuevaClave2026"
}
```

| Campo | Tipo | Obligatorio | Reglas |
|---|---|---|---|
| `passwordActual` | texto | sí | longitud mínima 1; longitud máxima 72 |
| `passwordNueva` | texto | sí | longitud máxima 72 |

Validaciones entre campos y validadores propios (responden 422 con estos mensajes):

- La contraseña debe tener al menos 8 caracteres
- La contraseña debe contener al menos una letra mayúscula
- La contraseña debe contener al menos un número

### `POST /api/v1/admin/usuarios` — esquema `AdminUsuarioIn`

Cuerpo obligatorio.

```json
{
  "nombre": "Jorge",
  "apellidos": "Valdez Soto",
  "email": "valuador3@demo-banco.test",
  "password": "Valuador2026",
  "telefono": "5544332211",
  "rol": "valuador"
}
```

| Campo | Tipo | Obligatorio | Reglas |
|---|---|---|---|
| `nombre` | texto | sí | longitud mínima 2; longitud máxima 80; patrón `^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ' .-]+$` |
| `apellidos` | texto | sí | longitud mínima 2; longitud máxima 120; patrón `^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ' .-]+$` |
| `email` | texto | sí | longitud mínima 5; longitud máxima 160; validador: Valida el formato del correo (sin DNS) y lo normaliza a minúsculas. |
| `password` | texto | sí | longitud máxima 72 |
| `telefono` | texto | no | patrón `^\+?[0-9]{10,15}$`; por defecto `null`; admite `null` |
| `rol` | enum: `valuador` \| `analista` \| `admin` | sí | — |

Validaciones entre campos y validadores propios (responden 422 con estos mensajes):

- La contraseña debe tener al menos 8 caracteres
- La contraseña debe contener al menos una letra mayúscula
- La contraseña debe contener al menos un número

### `PATCH /api/v1/admin/usuarios/{usuario_id}/estado` — esquema `EstadoUsuarioIn`

Cuerpo obligatorio.

```json
{
  "activo": false
}
```

| Campo | Tipo | Obligatorio | Reglas |
|---|---|---|---|
| `activo` | booleano | sí | — |

### `POST /api/v1/productos` — esquema `ProductoIn`

Cuerpo obligatorio.

```json
{
  "nombre": "Préstamo Auto Demo",
  "tipo": "prestamo",
  "descripcion": "Préstamo demostrativo para auto.",
  "tasaAnual": 16.9,
  "montoMin": 30000,
  "montoMax": 400000,
  "plazosMeses": [
    12,
    24,
    36,
    48
  ],
  "engancheMinPct": null,
  "documentosRequeridos": [
    "identificacion",
    "comprobante_domicilio",
    "comprobante_ingresos"
  ],
  "requisitos": [
    "Ser mayor de edad",
    "Ingreso mínimo demostrable"
  ],
  "condiciones": "Tasa fija. Producto demostrativo sin validez comercial.",
  "activo": true
}
```

| Campo | Tipo | Obligatorio | Reglas |
|---|---|---|---|
| `nombre` | texto | sí | longitud mínima 3; longitud máxima 120 |
| `tipo` | enum: `prestamo` \| `hipoteca` | sí | — |
| `descripcion` | texto | sí | longitud mínima 5; longitud máxima 2000 |
| `tasaAnual` | número (decimal) | sí | ≥ 0; ≤ 100; máx. 6 dígitos; máx. 2 decimales |
| `montoMin` | número (decimal) | sí | > 0; máx. 12 dígitos; máx. 2 decimales |
| `montoMax` | número (decimal) | sí | > 0; máx. 12 dígitos; máx. 2 decimales |
| `plazosMeses` | lista de entero | sí | longitud mínima 1; longitud máxima 20 |
| `engancheMinPct` | número (decimal) | no | ≥ 0; ≤ 90; máx. 6 dígitos; máx. 2 decimales; por defecto `null`; admite `null` |
| `documentosRequeridos` | lista de enum: `identificacion` \| `comprobante_domicilio` \| `comprobante_ingresos` \| `estados_cuenta` \| `escrituras` \| `predial` | sí | longitud mínima 1 |
| `requisitos` | lista de texto | no | longitud máxima 30; por defecto `[]` |
| `condiciones` | texto | sí | longitud mínima 5; longitud máxima 4000 |
| `activo` | booleano | no | por defecto `true` |

Validaciones entre campos y validadores propios (responden 422 con estos mensajes):

- montoMin debe ser menor que montoMax
- Cada plazo debe estar entre 1 y 480 meses
- plazosMeses no debe tener valores repetidos
- documentosRequeridos no debe tener valores repetidos
- engancheMinPct es obligatorio para productos de hipoteca
- engancheMinPct solo aplica a productos de hipoteca
- Los documentos {invalidos} solo aplican a hipotecas

### `PUT /api/v1/productos/{producto_id}` — esquema `ProductoIn`

Cuerpo obligatorio.

```json
{
  "nombre": "Préstamo Auto Demo",
  "tipo": "prestamo",
  "descripcion": "Préstamo demostrativo para auto.",
  "tasaAnual": 15.9,
  "montoMin": 30000,
  "montoMax": 400000,
  "plazosMeses": [
    12,
    24,
    36,
    48
  ],
  "engancheMinPct": null,
  "documentosRequeridos": [
    "identificacion",
    "comprobante_domicilio",
    "comprobante_ingresos"
  ],
  "requisitos": [
    "Ser mayor de edad",
    "Ingreso mínimo demostrable"
  ],
  "condiciones": "Tasa fija. Producto demostrativo sin validez comercial.",
  "activo": true
}
```

| Campo | Tipo | Obligatorio | Reglas |
|---|---|---|---|
| `nombre` | texto | sí | longitud mínima 3; longitud máxima 120 |
| `tipo` | enum: `prestamo` \| `hipoteca` | sí | — |
| `descripcion` | texto | sí | longitud mínima 5; longitud máxima 2000 |
| `tasaAnual` | número (decimal) | sí | ≥ 0; ≤ 100; máx. 6 dígitos; máx. 2 decimales |
| `montoMin` | número (decimal) | sí | > 0; máx. 12 dígitos; máx. 2 decimales |
| `montoMax` | número (decimal) | sí | > 0; máx. 12 dígitos; máx. 2 decimales |
| `plazosMeses` | lista de entero | sí | longitud mínima 1; longitud máxima 20 |
| `engancheMinPct` | número (decimal) | no | ≥ 0; ≤ 90; máx. 6 dígitos; máx. 2 decimales; por defecto `null`; admite `null` |
| `documentosRequeridos` | lista de enum: `identificacion` \| `comprobante_domicilio` \| `comprobante_ingresos` \| `estados_cuenta` \| `escrituras` \| `predial` | sí | longitud mínima 1 |
| `requisitos` | lista de texto | no | longitud máxima 30; por defecto `[]` |
| `condiciones` | texto | sí | longitud mínima 5; longitud máxima 4000 |
| `activo` | booleano | no | por defecto `true` |

Validaciones entre campos y validadores propios (responden 422 con estos mensajes):

- montoMin debe ser menor que montoMax
- Cada plazo debe estar entre 1 y 480 meses
- plazosMeses no debe tener valores repetidos
- documentosRequeridos no debe tener valores repetidos
- engancheMinPct es obligatorio para productos de hipoteca
- engancheMinPct solo aplica a productos de hipoteca
- Los documentos {invalidos} solo aplican a hipotecas

### `POST /api/v1/simuladores/prestamo` — esquema `SimuladorPrestamoIn`

Cuerpo obligatorio.

```json
{
  "monto": 50000,
  "tasaAnual": 18.5,
  "plazoMeses": 24
}
```

| Campo | Tipo | Obligatorio | Reglas |
|---|---|---|---|
| `tasaAnual` | número (decimal) | no | ≥ 0; ≤ 100; máx. 6 dígitos; máx. 2 decimales; por defecto `null`; admite `null` |
| `productoId` | entero | no | > 0; por defecto `null`; admite `null` |
| `monto` | número (decimal) | sí | > 0; máx. 12 dígitos; máx. 2 decimales |
| `plazoMeses` | entero | sí | > 0; ≤ 480 |

Validaciones entre campos y validadores propios (responden 422 con estos mensajes):

- Debe indicar tasaAnual o productoId

### `POST /api/v1/simuladores/hipoteca` — esquema `SimuladorHipotecaIn`

Cuerpo obligatorio.

```json
{
  "valorInmueble": 2500000,
  "enganche": 700000,
  "productoId": 4,
  "plazoMeses": 240
}
```

| Campo | Tipo | Obligatorio | Reglas |
|---|---|---|---|
| `tasaAnual` | número (decimal) | no | ≥ 0; ≤ 100; máx. 6 dígitos; máx. 2 decimales; por defecto `null`; admite `null` |
| `productoId` | entero | no | > 0; por defecto `null`; admite `null` |
| `valorInmueble` | número (decimal) | sí | > 0; máx. 12 dígitos; máx. 2 decimales |
| `enganche` | número (decimal) | sí | ≥ 0; máx. 12 dígitos; máx. 2 decimales |
| `plazoMeses` | entero | sí | > 0; ≤ 480 |
| `engancheMinPct` | número (decimal) | no | ≥ 0; ≤ 90; máx. 6 dígitos; máx. 2 decimales; por defecto `null`; admite `null`; Si no se indica, se toma del producto o 10% por defecto |

Validaciones entre campos y validadores propios (responden 422 con estos mensajes):

- El enganche debe ser menor que el valor del inmueble
- Debe indicar tasaAnual o productoId

### `POST /api/v1/simuladores/amortizacion` — esquema `AmortizacionIn`

Cuerpo obligatorio.

```json
{
  "monto": 50000,
  "tasaAnual": 18.5,
  "plazoMeses": 12
}
```

| Campo | Tipo | Obligatorio | Reglas |
|---|---|---|---|
| `monto` | número (decimal) | sí | > 0; máx. 12 dígitos; máx. 2 decimales |
| `tasaAnual` | número (decimal) | sí | ≥ 0; ≤ 100; máx. 6 dígitos; máx. 2 decimales |
| `plazoMeses` | entero | sí | > 0; ≤ 480 |

### `POST /api/v1/solicitudes` — esquema `SolicitudIn`

Cuerpo obligatorio.

```json
{
  "productoId": 4,
  "montoSolicitado": 1800000,
  "plazoMeses": 240,
  "valorInmueble": 2500000
}
```

| Campo | Tipo | Obligatorio | Reglas |
|---|---|---|---|
| `productoId` | entero | sí | > 0 |
| `montoSolicitado` | número (decimal) | sí | > 0; máx. 12 dígitos; máx. 2 decimales |
| `plazoMeses` | entero | sí | > 0; ≤ 480 |
| `valorInmueble` | número (decimal) | no | > 0; máx. 12 dígitos; máx. 2 decimales; por defecto `null`; admite `null` |

### `POST /api/v1/solicitudes/{solicitud_id}/cancelar` — esquema `CancelarIn`

Cuerpo **opcional** (se puede omitir).

```json
{
  "motivo": "Ya no lo necesito"
}
```

| Campo | Tipo | Obligatorio | Reglas |
|---|---|---|---|
| `motivo` | texto | no | longitud máxima 500; por defecto `null`; admite `null` |

### `PATCH /api/v1/solicitudes/{solicitud_id}/resolucion` — esquema `ResolucionIn`

Cuerpo obligatorio.

```json
{
  "estado": "aprobada",
  "monto": 55000,
  "tasa": 22,
  "plazo": 24,
  "motivo": "Revisión manual: historial de pagos comprobado."
}
```

| Campo | Tipo | Obligatorio | Reglas |
|---|---|---|---|
| `estado` | enum: `aprobada` \| `condicionada` \| `rechazada` | sí | — |
| `monto` | número (decimal) | no | > 0; máx. 12 dígitos; máx. 2 decimales; por defecto `null`; admite `null` |
| `tasa` | número (decimal) | no | ≥ 0; ≤ 100; máx. 6 dígitos; máx. 2 decimales; por defecto `null`; admite `null` |
| `plazo` | entero | no | > 0; ≤ 480; por defecto `null`; admite `null` |
| `motivo` | texto | sí | longitud mínima 5; longitud máxima 1000 |

### `POST /api/v1/solicitudes/{solicitud_id}/oferta/rechazar` — esquema `CancelarIn`

Cuerpo **opcional** (se puede omitir).

```json
{
  "motivo": "La tasa no me conviene"
}
```

| Campo | Tipo | Obligatorio | Reglas |
|---|---|---|---|
| `motivo` | texto | no | longitud máxima 500; por defecto `null`; admite `null` |

### `PUT /api/v1/solicitudes/{solicitud_id}/solicitante` — esquema `SolicitanteIn`

Cuerpo obligatorio.

```json
{
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
    {
      "nombre": "María Gómez",
      "telefono": "5511112222",
      "relacion": "hermana"
    },
    {
      "nombre": "Pedro Ruiz",
      "telefono": "5533334444",
      "relacion": "amigo"
    }
  ]
}
```

| Campo | Tipo | Obligatorio | Reglas |
|---|---|---|---|
| `fechaNacimiento` | fecha `AAAA-MM-DD` | sí | — |
| `curpFicticia` | texto | sí | patrón `^[A-Z0-9]{18}$`; CURP FICTICIA de 18 caracteres alfanuméricos en mayúsculas |
| `estadoCivil` | enum: `soltero` \| `casado` \| `divorciado` \| `viudo` \| `union_libre` | sí | — |
| `dependientes` | entero | no | ≥ 0; ≤ 20; por defecto `0` |
| `domicilio` | texto | sí | longitud mínima 5; longitud máxima 200 |
| `ciudad` | texto | sí | longitud mínima 2; longitud máxima 80 |
| `empresa` | texto | sí | longitud mínima 2; longitud máxima 120 |
| `puesto` | texto | sí | longitud mínima 2; longitud máxima 80 |
| `tipoEmpleo` | enum: `asalariado` \| `independiente` | sí | — |
| `antiguedadMeses` | entero | sí | ≥ 0; ≤ 720 |
| `ingresoMensual` | número (decimal) | sí | > 0; máx. 12 dígitos; máx. 2 decimales |
| `otrosIngresos` | número (decimal) | no | ≥ 0; máx. 12 dígitos; máx. 2 decimales; por defecto `0.0` |
| `gastosMensuales` | número (decimal) | no | ≥ 0; máx. 12 dígitos; máx. 2 decimales; por defecto `0.0` |
| `deudasMensuales` | número (decimal) | no | ≥ 0; máx. 12 dígitos; máx. 2 decimales; por defecto `0.0` |
| `referencias` | lista de objeto | sí | longitud mínima 2; longitud máxima 5 |
| `referencias[].nombre` | texto | sí | longitud mínima 3; longitud máxima 120; patrón `^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ' .-]+$` |
| `referencias[].telefono` | texto | sí | patrón `^\+?[0-9]{10,15}$` |
| `referencias[].relacion` | texto | sí | longitud mínima 3; longitud máxima 40 |

Validaciones entre campos y validadores propios (responden 422 con estos mensajes):

- Las referencias deben tener teléfonos distintos

### `POST /api/v1/solicitudes/{solicitud_id}/documentos` — esquema `DocumentoIn`

Cuerpo obligatorio.

```json
{
  "tipo": "identificacion",
  "nombreArchivoSimulado": "identificacion_demo.pdf"
}
```

| Campo | Tipo | Obligatorio | Reglas |
|---|---|---|---|
| `tipo` | enum: `identificacion` \| `comprobante_domicilio` \| `comprobante_ingresos` \| `estados_cuenta` \| `escrituras` \| `predial` | sí | — |
| `nombreArchivoSimulado` | texto | sí | longitud mínima 5; longitud máxima 150; patrón `^[\w\-. ]+\.(pdf\|jpg\|jpeg\|png)$`; Nombre de archivo simulado con extensión .pdf, .jpg, .jpeg o .png |

### `PATCH /api/v1/solicitudes/{solicitud_id}/documentos/{documento_id}` — esquema `DocumentoRevisionIn`

Cuerpo obligatorio.

```json
{
  "estado": "validado"
}
```

| Campo | Tipo | Obligatorio | Reglas |
|---|---|---|---|
| `estado` | enum: `validado` \| `rechazado` | sí | — |
| `observaciones` | texto | no | longitud máxima 500; por defecto `null`; admite `null` |

Validaciones entre campos y validadores propios (responden 422 con estos mensajes):

- Las observaciones son obligatorias al rechazar un documento

### `PUT /api/v1/solicitudes/{solicitud_id}/inmueble` — esquema `InmuebleIn`

Cuerpo obligatorio.

```json
{
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
  "valorEstimadoCliente": 2500000
}
```

| Campo | Tipo | Obligatorio | Reglas |
|---|---|---|---|
| `tipo` | enum: `casa` \| `departamento` \| `terreno` | sí | — |
| `direccion` | texto | sí | longitud mínima 5; longitud máxima 200 |
| `colonia` | texto | sí | longitud mínima 2; longitud máxima 100 |
| `ciudad` | texto | sí | longitud mínima 2; longitud máxima 80 |
| `estado` | texto | sí | longitud mínima 2; longitud máxima 60 |
| `cp` | texto | sí | patrón `^[0-9]{5}$` |
| `m2Terreno` | número (decimal) | sí | > 0; máx. 10 dígitos; máx. 2 decimales |
| `m2Construccion` | número (decimal) | sí | ≥ 0; máx. 10 dígitos; máx. 2 decimales |
| `antiguedadAnios` | entero | sí | ≥ 0; ≤ 200 |
| `recamaras` | entero | no | ≥ 0; ≤ 30; por defecto `0` |
| `banos` | entero | no | ≥ 0; ≤ 30; por defecto `0` |
| `valorEstimadoCliente` | número (decimal) | sí | > 0; máx. 12 dígitos; máx. 2 decimales |

Validaciones entre campos y validadores propios (responden 422 con estos mensajes):

- m2Construccion debe ser mayor que 0 para casas y departamentos

### `PATCH /api/v1/avaluos/{avaluo_id}/resultado` — esquema `AvaluoResultadoIn`

Cuerpo obligatorio.

```json
{
  "valorComercial": 2400000,
  "estadoConservacion": "bueno",
  "observaciones": "Visita realizada: acabados en buen estado, requiere impermeabilización."
}
```

| Campo | Tipo | Obligatorio | Reglas |
|---|---|---|---|
| `valorComercial` | número (decimal) | sí | > 0; máx. 12 dígitos; máx. 2 decimales |
| `estadoConservacion` | enum: `excelente` \| `bueno` \| `regular` \| `malo` | sí | — |
| `observaciones` | texto | sí | longitud mínima 5; longitud máxima 1000 |

## d) Respuestas exitosas reales

Cada respuesta se copió tal cual llegó del servidor. Los únicos recortes son el token y las tablas de amortización largas, y se indican debajo de cada ejemplo. Los ids salen de la BD temporal, que se sembró igual que `banco_demo.db` porque el seed es determinista.

### `GET /api/v1/health`

Petición real: `GET /api/v1/health` sin token (endpoint público) → **HTTP 200**

```json
{
  "ok": true,
  "message": "API en línea",
  "data": {
    "estado": "ok",
    "servicio": "API Banco Demo",
    "version": "1.0.0",
    "baseDatos": "ok",
    "fecha": "2026-11-16T04:04:11"
  },
  "demo": true
}
```

### `POST /api/v1/auth/login`

Petición real: `POST /api/v1/auth/login` sin token (endpoint público) → **HTTP 200**

```json
{
  "ok": true,
  "message": "Inicio de sesión exitoso",
  "data": {
    "accessToken": "eyJhbGciOiJIUzI1NiIsInR5…",
    "tokenType": "bearer",
    "expiresIn": 3600,
    "usuario": {
      "id": 16,
      "codigo": "USR-DEMO-000016",
      "nombre": "Florencia",
      "apellidos": "Terán Castellanos",
      "email": "cliente11@demo-banco.test",
      "telefono": "5516697848",
      "rol": "cliente",
      "activo": true,
      "creadoEn": "2026-11-16T04:04:09"
    }
  },
  "demo": true
}
```

_Nota: `accessToken` recortado (el real mide 164 caracteres)._

### `GET /api/v1/auth/me`

Petición real: `GET /api/v1/auth/me` como `cliente11@demo-banco.test` (rol `cliente`) → **HTTP 200**

```json
{
  "ok": true,
  "message": "Usuario autenticado",
  "data": {
    "id": 16,
    "codigo": "USR-DEMO-000016",
    "nombre": "Florencia",
    "apellidos": "Terán Castellanos",
    "email": "cliente11@demo-banco.test",
    "telefono": "5516697848",
    "rol": "cliente",
    "activo": true,
    "creadoEn": "2026-11-16T04:04:09"
  },
  "demo": true
}
```

### `POST /api/v1/usuarios/registro`

Petición real: `POST /api/v1/usuarios/registro` sin token (endpoint público) → **HTTP 201**

```json
{
  "ok": true,
  "message": "Registro exitoso. Se creó una cuenta de débito demo.",
  "data": {
    "usuario": {
      "id": 21,
      "codigo": "USR-DEMO-000021",
      "nombre": "Laura",
      "apellidos": "Martínez Ruiz",
      "email": "laura.frontend@demo-banco.test",
      "telefono": "5511223344",
      "rol": "cliente",
      "activo": true,
      "creadoEn": "2026-11-16T04:04:11"
    },
    "cuenta": {
      "id": 23,
      "numeroEnmascarado": "****4207",
      "tipo": "debito",
      "saldo": 16006.04,
      "moneda": "MXN",
      "estado": "activa",
      "creadaEn": "2026-11-16T04:04:11"
    }
  },
  "demo": true
}
```

### `GET /api/v1/usuarios/perfil`

Petición real: `GET /api/v1/usuarios/perfil` como `cliente11@demo-banco.test` (rol `cliente`) → **HTTP 200**

```json
{
  "ok": true,
  "message": "Perfil del usuario",
  "data": {
    "id": 16,
    "codigo": "USR-DEMO-000016",
    "nombre": "Florencia",
    "apellidos": "Terán Castellanos",
    "email": "cliente11@demo-banco.test",
    "telefono": "5516697848",
    "rol": "cliente",
    "activo": true,
    "creadoEn": "2026-11-16T04:04:09"
  },
  "demo": true
}
```

### `PATCH /api/v1/usuarios/perfil`

Petición real: `PATCH /api/v1/usuarios/perfil` como `cliente11@demo-banco.test` (rol `cliente`) → **HTTP 200**

```json
{
  "ok": true,
  "message": "Perfil actualizado",
  "data": {
    "id": 16,
    "codigo": "USR-DEMO-000016",
    "nombre": "Florencia",
    "apellidos": "Terán Castellanos",
    "email": "cliente11@demo-banco.test",
    "telefono": "5599887766",
    "rol": "cliente",
    "activo": true,
    "creadoEn": "2026-11-16T04:04:09"
  },
  "demo": true
}
```

### `PATCH /api/v1/usuarios/perfil/password`

Petición real: `PATCH /api/v1/usuarios/perfil/password` como `laura.frontend@demo-banco.test` (rol `cliente`) → **HTTP 200**

```json
{
  "ok": true,
  "message": "Contraseña actualizada correctamente",
  "data": {
    "id": 21,
    "estado": null
  },
  "demo": true
}
```

### `GET /api/v1/admin/usuarios`

Petición real: `GET /api/v1/admin/usuarios?rol=cliente&page=1&limit=3` como `admin@demo-banco.test` (rol `admin`) → **HTTP 200**

```json
{
  "ok": true,
  "message": "Usuarios",
  "data": [
    {
      "id": 6,
      "codigo": "USR-DEMO-000006",
      "nombre": "Mariano",
      "apellidos": "Gonzales Santiago",
      "email": "cliente1@demo-banco.test",
      "telefono": "5559407816",
      "rol": "cliente",
      "activo": true,
      "creadoEn": "2026-11-16T04:04:09"
    },
    {
      "id": 7,
      "codigo": "USR-DEMO-000007",
      "nombre": "Olivia",
      "apellidos": "Amador Valentín",
      "email": "cliente2@demo-banco.test",
      "telefono": "5518495931",
      "rol": "cliente",
      "activo": true,
      "creadoEn": "2026-11-16T04:04:09"
    },
    {
      "id": 8,
      "codigo": "USR-DEMO-000008",
      "nombre": "Leonardo",
      "apellidos": "Trejo Perea",
      "email": "cliente3@demo-banco.test",
      "telefono": "5503413164",
      "rol": "cliente",
      "activo": true,
      "creadoEn": "2026-11-16T04:04:09"
    }
  ],
  "meta": {
    "page": 1,
    "limit": 3,
    "total": 16
  },
  "demo": true
}
```

### `GET /api/v1/admin/usuarios/{usuario_id}`

Petición real: `GET /api/v1/admin/usuarios/16` como `admin@demo-banco.test` (rol `admin`) → **HTTP 200**

```json
{
  "ok": true,
  "message": "Usuario",
  "data": {
    "id": 16,
    "codigo": "USR-DEMO-000016",
    "nombre": "Florencia",
    "apellidos": "Terán Castellanos",
    "email": "cliente11@demo-banco.test",
    "telefono": "5599887766",
    "rol": "cliente",
    "activo": true,
    "creadoEn": "2026-11-16T04:04:09"
  },
  "demo": true
}
```

### `POST /api/v1/admin/usuarios`

Petición real: `POST /api/v1/admin/usuarios` como `admin@demo-banco.test` (rol `admin`) → **HTTP 201**

```json
{
  "ok": true,
  "message": "Usuario creado",
  "data": {
    "id": 22,
    "codigo": "USR-DEMO-000022",
    "nombre": "Jorge",
    "apellidos": "Valdez Soto",
    "email": "valuador3@demo-banco.test",
    "telefono": "5544332211",
    "rol": "valuador",
    "activo": true,
    "creadoEn": "2026-11-16T04:04:12"
  },
  "demo": true
}
```

### `PATCH /api/v1/admin/usuarios/{usuario_id}/estado`

Petición real: `PATCH /api/v1/admin/usuarios/22/estado` como `admin@demo-banco.test` (rol `admin`) → **HTTP 200**

```json
{
  "ok": true,
  "message": "Usuario desactivado",
  "data": {
    "id": 22,
    "codigo": "USR-DEMO-000022",
    "nombre": "Jorge",
    "apellidos": "Valdez Soto",
    "email": "valuador3@demo-banco.test",
    "telefono": "5544332211",
    "rol": "valuador",
    "activo": false,
    "creadoEn": "2026-11-16T04:04:12"
  },
  "demo": true
}
```

### `GET /api/v1/admin/estadisticas`

Petición real: `GET /api/v1/admin/estadisticas` como `admin@demo-banco.test` (rol `admin`) → **HTTP 200**

```json
{
  "ok": true,
  "message": "Estadísticas",
  "data": {
    "totalSolicitudes": 12,
    "solicitudesPorEstado": {
      "borrador": 1,
      "datos_completos": 1,
      "en_avaluo": 1,
      "avaluo_completado": 1,
      "en_analisis": 0,
      "aprobada": 1,
      "condicionada": 1,
      "rechazada": 0,
      "oferta_aceptada": 1,
      "oferta_rechazada": 1,
      "formalizada": 2,
      "cancelada": 2
    },
    "solicitudesPorTipo": {
      "prestamo": 7,
      "hipoteca": 5
    },
    "montoTotalAprobado": 4408900.0,
    "solicitudesResueltas": 6,
    "solicitudesFavorables": 6,
    "tasaAprobacionPct": 100.0,
    "usuariosPorRol": {
      "cliente": 16,
      "valuador": 3,
      "analista": 2,
      "admin": 1
    },
    "totalCuentas": 23
  },
  "demo": true
}
```

### `GET /api/v1/productos`

Petición real: `GET /api/v1/productos` sin token (endpoint público) → **HTTP 200**

```json
{
  "ok": true,
  "message": "Catálogo de productos",
  "data": [
    {
      "id": 1,
      "nombre": "Préstamo Personal Demo Básico",
      "tipo": "prestamo",
      "descripcion": "Préstamo personal demostrativo para gastos personales, con tasa fija.",
      "tasaAnual": 24.0,
      "montoMin": 10000.0,
      "montoMax": 100000.0,
      "plazosMeses": [
        12,
        24,
        36
      ],
      "engancheMinPct": null,
      "documentosRequeridos": [
        "identificacion",
        "comprobante_domicilio",
        "comprobante_ingresos",
        "estados_cuenta"
      ],
      "requisitos": [
        "Ser mayor de 18 años",
        "Antigüedad laboral mínima de 6 meses",
        "Ingreso mensual comprobable",
        "Dos referencias personales"
      ],
      "condiciones": "Tasa fija anual de 24%. Producto demostrativo sin validez comercial.",
      "activo": true
    },
    {
      "id": 2,
      "nombre": "Préstamo Personal Demo Plus",
      "tipo": "prestamo",
      "descripcion": "Préstamo personal demostrativo de mayor monto y plazo.",
      "tasaAnual": 18.5,
      "montoMin": 50000.0,
      "montoMax": 300000.0,
      "plazosMeses": [
        12,
        24,
        36,
        48
      ],
      "engancheMinPct": null,
      "documentosRequeridos": [
        "identificacion",
        "comprobante_domicilio",
        "comprobante_ingresos",
        "estados_cuenta"
      ],
      "requisitos": [
        "Ser mayor de 18 años",
        "Antigüedad laboral mínima de 6 meses",
        "Buen historial crediticio (buró ficticio ≥ 600)",
        "Dos referencias personales"
      ],
      "condiciones": "Tasa fija anual de 18.5%. Descuento de 1 punto con buró ≥ 750. Producto demostrativo.",
      "activo": true
    },
    {
      "id": 3,
      "nombre": "Préstamo Nómina Demo",
      "tipo": "prestamo",
      "descripcion": "Préstamo demostrativo para clientes con nómina en el banco demo.",
      "tasaAnual": 15.0,
      "montoMin": 20000.0,
      "montoMax": 200000.0,
      "plazosMeses": [
        12,
        24,
        36,
        48,
        60
      ],
      "engancheMinPct": null,
      "documentosRequeridos": [
        "identificacion",
        "comprobante_domicilio",
        "comprobante_ingresos"
      ],
      "requisitos": [
        "Recibir nómina en una cuenta demo",
        "Antigüedad laboral mínima de 6 meses",
        "Dos referencias personales"
      ],
      "condiciones": "Tasa fija anual de 15%. Descuento vía nómina (simulado). Producto demostrativo.",
      "activo": true
    },
    {
      "id": 4,
      "nombre": "Hipoteca Fija Demo",
      "tipo": "hipoteca",
      "descripcion": "Crédito hipotecario demostrativo a tasa fija para compra de vivienda.",
      "tasaAnual": 10.5,
      "montoMin": 500000.0,
      "montoMax": 5000000.0,
      "plazosMeses": [
        120,
        180,
        240
      ],
      "engancheMinPct": 10.0,
      "documentosRequeridos": [
        "identificacion",
        "comprobante_domicilio",
        "comprobante_ingresos",
        "estados_cuenta",
        "escrituras",
        "predial"
      ],
      "requisitos": [
        "Ser mayor de 18 años y menor de 70 al terminar el plazo",
        "Enganche mínimo del 10% del valor del inmueble",
        "Avalúo del inmueble",
        "Financiamiento máximo del 90% del valor comercial"
      ],
      "condiciones": "Tasa fija anual de 10.5% durante todo el plazo. Producto demostrativo.",
      "activo": true
    },
    {
      "id": 5,
      "nombre": "Hipoteca Plus Demo",
      "tipo": "hipoteca",
      "descripcion": "Crédito hipotecario demostrativo para inmuebles de mayor valor.",
      "tasaAnual": 9.8,
      "montoMin": 1000000.0,
      "montoMax": 10000000.0,
      "plazosMeses": [
        180,
        240
      ],
      "engancheMinPct": 20.0,
      "documentosRequeridos": [
        "identificacion",
        "comprobante_domicilio",
        "comprobante_ingresos",
        "estados_cuenta",
        "escrituras",
        "predial"
      ],
      "requisitos": [
        "Enganche mínimo del 20% del valor del inmueble",
        "Avalúo del inmueble",
        "Ingreso comprobable suficiente (relación pago/ingreso ≤ 35%)"
      ],
      "condiciones": "Tasa fija anual de 9.8%. Producto demostrativo.",
      "activo": true
    },
    {
      "id": 6,
      "nombre": "Hipoteca Joven Demo",
      "tipo": "hipoteca",
      "descripcion": "Crédito hipotecario demostrativo para primera vivienda.",
      "tasaAnual": 11.2,
      "montoMin": 400000.0,
      "montoMax": 2500000.0,
      "plazosMeses": [
        120,
        180,
        240
      ],
      "engancheMinPct": 10.0,
      "documentosRequeridos": [
        "identificacion",
        "comprobante_domicilio",
        "comprobante_ingresos",
        "estados_cuenta",
        "escrituras",
        "predial"
      ],
      "requisitos": [
        "Primera vivienda",
        "Enganche mínimo del 10% del valor del inmueble",
        "Avalúo del inmueble"
      ],
      "condiciones": "Tasa fija anual de 11.2%. Producto demostrativo.",
      "activo": true
    }
  ],
  "demo": true
}
```

### `GET /api/v1/productos/{producto_id}`

Petición real: `GET /api/v1/productos/4` sin token (endpoint público) → **HTTP 200**

```json
{
  "ok": true,
  "message": "Producto",
  "data": {
    "id": 4,
    "nombre": "Hipoteca Fija Demo",
    "tipo": "hipoteca",
    "descripcion": "Crédito hipotecario demostrativo a tasa fija para compra de vivienda.",
    "tasaAnual": 10.5,
    "montoMin": 500000.0,
    "montoMax": 5000000.0,
    "plazosMeses": [
      120,
      180,
      240
    ],
    "engancheMinPct": 10.0,
    "documentosRequeridos": [
      "identificacion",
      "comprobante_domicilio",
      "comprobante_ingresos",
      "estados_cuenta",
      "escrituras",
      "predial"
    ],
    "requisitos": [
      "Ser mayor de 18 años y menor de 70 al terminar el plazo",
      "Enganche mínimo del 10% del valor del inmueble",
      "Avalúo del inmueble",
      "Financiamiento máximo del 90% del valor comercial"
    ],
    "condiciones": "Tasa fija anual de 10.5% durante todo el plazo. Producto demostrativo.",
    "activo": true
  },
  "demo": true
}
```

### `GET /api/v1/productos/{producto_id}/requisitos`

Petición real: `GET /api/v1/productos/4/requisitos` sin token (endpoint público) → **HTTP 200**

```json
{
  "ok": true,
  "message": "Requisitos del producto",
  "data": {
    "productoId": 4,
    "nombre": "Hipoteca Fija Demo",
    "tipo": "hipoteca",
    "requisitos": [
      "Ser mayor de 18 años y menor de 70 al terminar el plazo",
      "Enganche mínimo del 10% del valor del inmueble",
      "Avalúo del inmueble",
      "Financiamiento máximo del 90% del valor comercial"
    ],
    "documentosRequeridos": [
      {
        "tipo": "identificacion",
        "descripcion": "Identificación oficial vigente (simulada)"
      },
      {
        "tipo": "comprobante_domicilio",
        "descripcion": "Comprobante de domicilio no mayor a 3 meses (simulado)"
      },
      {
        "tipo": "comprobante_ingresos",
        "descripcion": "Comprobante de ingresos de los últimos 3 meses (simulado)"
      },
      {
        "tipo": "estados_cuenta",
        "descripcion": "Estados de cuenta bancarios de los últimos 3 meses (simulados)"
      },
      {
        "tipo": "escrituras",
        "descripcion": "Escrituras o contrato de compraventa del inmueble (simulado)"
      },
      {
        "tipo": "predial",
        "descripcion": "Boleta predial al corriente del inmueble (simulada)"
      }
    ],
    "engancheMinPct": 10.0,
    "montoMin": 500000.0,
    "montoMax": 5000000.0,
    "plazosMeses": [
      120,
      180,
      240
    ],
    "condiciones": "Tasa fija anual de 10.5% durante todo el plazo. Producto demostrativo."
  },
  "demo": true
}
```

### `POST /api/v1/productos`

Petición real: `POST /api/v1/productos` como `admin@demo-banco.test` (rol `admin`) → **HTTP 201**

```json
{
  "ok": true,
  "message": "Producto creado",
  "data": {
    "id": 7,
    "nombre": "Préstamo Auto Demo",
    "tipo": "prestamo",
    "descripcion": "Préstamo demostrativo para auto.",
    "tasaAnual": 16.9,
    "montoMin": 30000.0,
    "montoMax": 400000.0,
    "plazosMeses": [
      12,
      24,
      36,
      48
    ],
    "engancheMinPct": null,
    "documentosRequeridos": [
      "identificacion",
      "comprobante_domicilio",
      "comprobante_ingresos"
    ],
    "requisitos": [
      "Ser mayor de edad",
      "Ingreso mínimo demostrable"
    ],
    "condiciones": "Tasa fija. Producto demostrativo sin validez comercial.",
    "activo": true
  },
  "demo": true
}
```

### `PUT /api/v1/productos/{producto_id}`

Petición real: `PUT /api/v1/productos/7` como `admin@demo-banco.test` (rol `admin`) → **HTTP 200**

```json
{
  "ok": true,
  "message": "Producto actualizado",
  "data": {
    "id": 7,
    "nombre": "Préstamo Auto Demo",
    "tipo": "prestamo",
    "descripcion": "Préstamo demostrativo para auto.",
    "tasaAnual": 15.9,
    "montoMin": 30000.0,
    "montoMax": 400000.0,
    "plazosMeses": [
      12,
      24,
      36,
      48
    ],
    "engancheMinPct": null,
    "documentosRequeridos": [
      "identificacion",
      "comprobante_domicilio",
      "comprobante_ingresos"
    ],
    "requisitos": [
      "Ser mayor de edad",
      "Ingreso mínimo demostrable"
    ],
    "condiciones": "Tasa fija. Producto demostrativo sin validez comercial.",
    "activo": true
  },
  "demo": true
}
```

### `DELETE /api/v1/productos/{producto_id}`

Petición real: `DELETE /api/v1/productos/7` como `admin@demo-banco.test` (rol `admin`) → **HTTP 204**

Respuesta sin cuerpo (204 No Content).

### `POST /api/v1/simuladores/prestamo`

Petición real: `POST /api/v1/simuladores/prestamo` sin token (endpoint público) → **HTTP 200**

```json
{
  "ok": true,
  "message": "Simulación de préstamo",
  "data": {
    "monto": 50000.0,
    "tasaAnual": 18.5,
    "plazoMeses": 24,
    "mensualidad": 2508.3,
    "totalIntereses": 10199.24,
    "totalPagar": 60199.24,
    "catDemo": 20.65,
    "productoId": null,
    "productoNombre": null,
    "leyenda": "SIMULACIÓN DEMOSTRATIVA - NO ES UNA OFERTA REAL"
  },
  "demo": true
}
```

### `POST /api/v1/simuladores/hipoteca`

Petición real: `POST /api/v1/simuladores/hipoteca` sin token (endpoint público) → **HTTP 200**

```json
{
  "ok": true,
  "message": "Simulación de hipoteca",
  "data": {
    "monto": 1800000.0,
    "tasaAnual": 10.5,
    "plazoMeses": 240,
    "mensualidad": 17970.84,
    "totalIntereses": 2513000.01,
    "totalPagar": 4313000.01,
    "catDemo": 11.07,
    "productoId": 4,
    "productoNombre": "Hipoteca Fija Demo",
    "leyenda": "SIMULACIÓN DEMOSTRATIVA - NO ES UNA OFERTA REAL",
    "valorInmueble": 2500000.0,
    "enganche": 700000.0,
    "enganchePct": 28.0,
    "engancheMinPct": 10.0,
    "engancheMinimo": 250000.0,
    "cumpleEngancheMinimo": true,
    "mensajeEnganche": "El enganche cumple con el mínimo requerido"
  },
  "demo": true
}
```

### `POST /api/v1/simuladores/amortizacion`

Petición real: `POST /api/v1/simuladores/amortizacion` sin token (endpoint público) → **HTTP 200**

```json
{
  "ok": true,
  "message": "Tabla de amortización",
  "data": {
    "monto": 50000.0,
    "tasaAnual": 18.5,
    "plazoMeses": 12,
    "mensualidad": 4595.91,
    "totalIntereses": 5150.85,
    "totalPagar": 55150.85,
    "tabla": [
      {
        "numero": 1,
        "pago": 4595.91,
        "capital": 3825.08,
        "interes": 770.83,
        "saldo": 46174.92,
        "fechaPago": null
      },
      {
        "numero": 2,
        "pago": 4595.91,
        "capital": 3884.05,
        "interes": 711.86,
        "saldo": 42290.87,
        "fechaPago": null
      },
      "… 9 filas omitidas …",
      {
        "numero": 12,
        "pago": 4595.84,
        "capital": 4526.06,
        "interes": 69.78,
        "saldo": 0.0,
        "fechaPago": null
      }
    ],
    "leyenda": "SIMULACIÓN DEMOSTRATIVA - NO ES UNA OFERTA REAL"
  },
  "demo": true
}
```

_Nota: `tabla` recortada: se muestran las filas 1, 2 y 12 de 12._

### `POST /api/v1/solicitudes`

Petición real: `POST /api/v1/solicitudes` como `cliente11@demo-banco.test` (rol `cliente`) → **HTTP 201**

```json
{
  "ok": true,
  "message": "Solicitud SOL-DEMO-2026-000011 creada",
  "data": {
    "id": 11,
    "folio": "SOL-DEMO-2026-000011",
    "usuarioId": 16,
    "producto": {
      "id": 4,
      "nombre": "Hipoteca Fija Demo",
      "tipo": "hipoteca",
      "tasaAnual": 10.5
    },
    "tipo": "hipoteca",
    "montoSolicitado": 1800000.0,
    "plazoMeses": 240,
    "valorInmueble": 2500000.0,
    "enganche": 700000.0,
    "estado": "borrador",
    "montoAprobado": null,
    "tasaAprobada": null,
    "plazoAprobado": null,
    "mensualidadAprobada": null,
    "creadaEn": "2026-11-16T04:04:12",
    "actualizadaEn": "2026-11-16T04:04:12",
    "puntajeBuro": null,
    "resultadoAnalisis": null,
    "engancheRequerido": null,
    "motivoResolucion": null,
    "resueltaEn": null,
    "formalizadaEn": null,
    "solicitante": null,
    "inmueble": null,
    "documentos": [
      {
        "tipo": "identificacion",
        "descripcion": "Identificación oficial vigente (simulada)",
        "estado": "pendiente",
        "documentoId": null,
        "nombreArchivoSimulado": null,
        "observaciones": null,
        "fecha": null
      },
      {
        "tipo": "comprobante_domicilio",
        "descripcion": "Comprobante de domicilio no mayor a 3 meses (simulado)",
        "estado": "pendiente",
        "documentoId": null,
        "nombreArchivoSimulado": null,
        "observaciones": null,
        "fecha": null
      },
      {
        "tipo": "comprobante_ingresos",
        "descripcion": "Comprobante de ingresos de los últimos 3 meses (simulado)",
        "estado": "pendiente",
        "documentoId": null,
        "nombreArchivoSimulado": null,
        "observaciones": null,
        "fecha": null
      },
      {
        "tipo": "estados_cuenta",
        "descripcion": "Estados de cuenta bancarios de los últimos 3 meses (simulados)",
        "estado": "pendiente",
        "documentoId": null,
        "nombreArchivoSimulado": null,
        "observaciones": null,
        "fecha": null
      },
      {
        "tipo": "escrituras",
        "descripcion": "Escrituras o contrato de compraventa del inmueble (simulado)",
        "estado": "pendiente",
        "documentoId": null,
        "nombreArchivoSimulado": null,
        "observaciones": null,
        "fecha": null
      },
      {
        "tipo": "predial",
        "descripcion": "Boleta predial al corriente del inmueble (simulada)",
        "estado": "pendiente",
        "documentoId": null,
        "nombreArchivoSimulado": null,
        "observaciones": null,
        "fecha": null
      }
    ],
    "progreso": {
      "porcentaje": 0,
      "solicitanteCompleto": false,
      "documentosRequeridos": [
        "identificacion",
        "comprobante_domicilio",
        "comprobante_ingresos",
        "estados_cuenta",
        "escrituras",
        "predial"
      ],
      "documentosEntregados": [],
      "documentosPendientes": [
        "identificacion",
        "comprobante_domicilio",
        "comprobante_ingresos",
        "estados_cuenta",
        "escrituras",
        "predial"
      ],
      "documentosRechazados": [],
      "inmuebleRequerido": true,
      "inmuebleRegistrado": false,
      "avaluoRequerido": true,
      "avaluoEstado": null,
      "editable": true,
      "siguientePaso": "Falta capturar datos del solicitante (PUT /solicitante); entregar documentos: identificacion, comprobante_domicilio, comprobante_ingresos, estados_cuenta, escrituras, predial; registrar el inmueble (PUT /inmueble)"
    }
  },
  "demo": true
}
```

### `GET /api/v1/solicitudes`

Petición real: `GET /api/v1/solicitudes?page=1&limit=10` como `cliente11@demo-banco.test` (rol `cliente`) → **HTTP 200**

```json
{
  "ok": true,
  "message": "Solicitudes",
  "data": [
    {
      "id": 12,
      "folio": "SOL-DEMO-2026-000012",
      "usuarioId": 16,
      "producto": {
        "id": 2,
        "nombre": "Préstamo Personal Demo Plus",
        "tipo": "prestamo",
        "tasaAnual": 18.5
      },
      "tipo": "prestamo",
      "montoSolicitado": 80000.0,
      "plazoMeses": 24,
      "valorInmueble": null,
      "enganche": null,
      "estado": "cancelada",
      "montoAprobado": null,
      "tasaAprobada": null,
      "plazoAprobado": null,
      "mensualidadAprobada": null,
      "creadaEn": "2026-11-16T04:04:13",
      "actualizadaEn": "2026-11-16T04:04:13"
    },
    {
      "id": 11,
      "folio": "SOL-DEMO-2026-000011",
      "usuarioId": 16,
      "producto": {
        "id": 4,
        "nombre": "Hipoteca Fija Demo",
        "tipo": "hipoteca",
        "tasaAnual": 10.5
      },
      "tipo": "hipoteca",
      "montoSolicitado": 1800000.0,
      "plazoMeses": 240,
      "valorInmueble": 2500000.0,
      "enganche": 700000.0,
      "estado": "formalizada",
      "montoAprobado": 1800000.0,
      "tasaAprobada": 9.5,
      "plazoAprobado": 240,
      "mensualidadAprobada": 16778.36,
      "creadaEn": "2026-11-16T04:04:12",
      "actualizadaEn": "2026-11-16T04:04:13"
    }
  ],
  "meta": {
    "page": 1,
    "limit": 10,
    "total": 2
  },
  "demo": true
}
```

### `GET /api/v1/solicitudes/{solicitud_id}`

Petición real: `GET /api/v1/solicitudes/11` como `cliente11@demo-banco.test` (rol `cliente`) → **HTTP 200**

```json
{
  "ok": true,
  "message": "Detalle de la solicitud",
  "data": {
    "id": 11,
    "folio": "SOL-DEMO-2026-000011",
    "usuarioId": 16,
    "producto": {
      "id": 4,
      "nombre": "Hipoteca Fija Demo",
      "tipo": "hipoteca",
      "tasaAnual": 10.5
    },
    "tipo": "hipoteca",
    "montoSolicitado": 1800000.0,
    "plazoMeses": 240,
    "valorInmueble": 2500000.0,
    "enganche": 700000.0,
    "estado": "formalizada",
    "montoAprobado": 1800000.0,
    "tasaAprobada": 9.5,
    "plazoAprobado": 240,
    "mensualidadAprobada": 16778.36,
    "creadaEn": "2026-11-16T04:04:12",
    "actualizadaEn": "2026-11-16T04:04:13",
    "puntajeBuro": 792,
    "resultadoAnalisis": {
      "resolucion": "aprobada",
      "reglas": [
        {
          "regla": "capacidad_pago",
          "descripcion": "Mensualidad ≤ 35% del ingreso neto (ingreso + otros − deudas)",
          "valor": 25.04,
          "limite": 35.0,
          "cumple": true
        },
        {
          "regla": "ltv",
          "descripcion": "Monto ≤ 90% del valor comercial del avalúo",
          "valor": 75.0,
          "limite": 90.0,
          "cumple": true
        },
        {
          "regla": "buro",
          "descripcion": "Puntaje de buró ficticio mínimo",
          "valor": 792,
          "limite": 600,
          "cumple": true
        },
        {
          "regla": "antiguedad_laboral",
          "descripcion": "Antigüedad laboral mínima en meses",
          "valor": 48,
          "limite": 6,
          "cumple": true
        },
        {
          "regla": "edad_fin_plazo",
          "descripcion": "Edad al terminar el plazo del crédito",
          "valor": 56,
          "limite": 70,
          "cumple": true
        }
      ],
      "puntajeBuro": 792,
      "ingresoNeto": 67000.0,
      "pagoMaximo": 23450.0,
      "mensualidadSolicitada": 16778.36,
      "tasaAplicada": 9.5,
      "fechaAnalisis": "2026-11-16"
    },
    "engancheRequerido": 700000.0,
    "motivoResolucion": "Solicitud aprobada: cumple todas las reglas del análisis.",
    "resueltaEn": "2026-11-16T04:04:13",
    "formalizadaEn": "2026-11-16T04:04:13",
    "solicitante": {
      "id": 10,
      "solicitudId": 11,
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
      "ingresoMensual": 65000.0,
      "otrosIngresos": 5000.0,
      "gastosMensuales": 20000.0,
      "deudasMensuales": 3000.0,
      "referencias": [
        {
          "nombre": "María Gómez",
          "telefono": "5511112222",
          "relacion": "hermana"
        },
        {
          "nombre": "Pedro Ruiz",
          "telefono": "5533334444",
          "relacion": "amigo"
        }
      ]
    },
    "inmueble": {
      "id": 5,
      "solicitudId": 11,
      "tipo": "casa",
      "direccion": "Calle Demo 45",
      "colonia": "Del Valle",
      "ciudad": "Ciudad de México",
      "estado": "Ciudad de México",
      "cp": "03100",
      "m2Terreno": 160.0,
      "m2Construccion": 140.0,
      "antiguedadAnios": 8,
      "recamaras": 3,
      "banos": 2,
      "valorEstimadoCliente": 2500000.0,
      "avaluo": {
        "id": 5,
        "folio": "AVA-DEMO-2026-000005",
        "inmuebleId": 5,
        "solicitudId": 11,
        "valuadorId": 3,
        "valuadorNombre": "Homero Canales Trejo",
        "estado": "completado",
        "fechaSolicitud": "2026-11-16T04:04:13",
        "fechaVisita": "2026-11-16T04:04:13",
        "valorComercial": 2400000.0,
        "estadoConservacion": "bueno",
        "observaciones": "Visita realizada: acabados en buen estado, requiere impermeabilización.",
        "generadoAutomaticamente": false
      }
    },
    "documentos": [
      {
        "tipo": "identificacion",
        "descripcion": "Identificación oficial vigente (simulada)",
        "estado": "validado",
        "documentoId": 41,
        "nombreArchivoSimulado": "identificacion_demo.pdf",
        "observaciones": null,
        "fecha": "2026-11-16T04:04:13"
      },
      {
        "tipo": "comprobante_domicilio",
        "descripcion": "Comprobante de domicilio no mayor a 3 meses (simulado)",
        "estado": "entregado",
        "documentoId": 42,
        "nombreArchivoSimulado": "comprobante_domicilio_demo.pdf",
        "observaciones": null,
        "fecha": "2026-11-16T04:04:12"
      },
      {
        "tipo": "comprobante_ingresos",
        "descripcion": "Comprobante de ingresos de los últimos 3 meses (simulado)",
        "estado": "entregado",
        "documentoId": 43,
        "nombreArchivoSimulado": "comprobante_ingresos_demo.pdf",
        "observaciones": null,
        "fecha": "2026-11-16T04:04:12"
      },
      {
        "tipo": "estados_cuenta",
        "descripcion": "Estados de cuenta bancarios de los últimos 3 meses (simulados)",
        "estado": "entregado",
        "documentoId": 44,
        "nombreArchivoSimulado": "estados_cuenta_demo.pdf",
        "observaciones": null,
        "fecha": "2026-11-16T04:04:12"
      },
      {
        "tipo": "escrituras",
        "descripcion": "Escrituras o contrato de compraventa del inmueble (simulado)",
        "estado": "entregado",
        "documentoId": 45,
        "nombreArchivoSimulado": "escrituras_demo.pdf",
        "observaciones": null,
        "fecha": "2026-11-16T04:04:12"
      },
      {
        "tipo": "predial",
        "descripcion": "Boleta predial al corriente del inmueble (simulada)",
        "estado": "entregado",
        "documentoId": 46,
        "nombreArchivoSimulado": "predial_demo.pdf",
        "observaciones": null,
        "fecha": "2026-11-16T04:04:12"
      }
    ],
    "progreso": {
      "porcentaje": 100,
      "solicitanteCompleto": true,
      "documentosRequeridos": [
        "identificacion",
        "comprobante_domicilio",
        "comprobante_ingresos",
        "estados_cuenta",
        "escrituras",
        "predial"
      ],
      "documentosEntregados": [
        "identificacion",
        "comprobante_domicilio",
        "comprobante_ingresos",
        "estados_cuenta",
        "escrituras",
        "predial"
      ],
      "documentosPendientes": [],
      "documentosRechazados": [],
      "inmuebleRequerido": true,
      "inmuebleRegistrado": true,
      "avaluoRequerido": true,
      "avaluoEstado": "completado",
      "editable": false,
      "siguientePaso": "Crédito formalizado: consultar la tabla de amortización"
    }
  },
  "demo": true
}
```

### `POST /api/v1/solicitudes/{solicitud_id}/cancelar`

Petición real: `POST /api/v1/solicitudes/12/cancelar` como `cliente11@demo-banco.test` (rol `cliente`) → **HTTP 200**

```json
{
  "ok": true,
  "message": "Solicitud cancelada",
  "data": {
    "id": 12,
    "folio": "SOL-DEMO-2026-000012",
    "usuarioId": 16,
    "producto": {
      "id": 2,
      "nombre": "Préstamo Personal Demo Plus",
      "tipo": "prestamo",
      "tasaAnual": 18.5
    },
    "tipo": "prestamo",
    "montoSolicitado": 80000.0,
    "plazoMeses": 24,
    "valorInmueble": null,
    "enganche": null,
    "estado": "cancelada",
    "montoAprobado": null,
    "tasaAprobada": null,
    "plazoAprobado": null,
    "mensualidadAprobada": null,
    "creadaEn": "2026-11-16T04:04:13",
    "actualizadaEn": "2026-11-16T04:04:13",
    "puntajeBuro": null,
    "resultadoAnalisis": null,
    "engancheRequerido": null,
    "motivoResolucion": null,
    "resueltaEn": null,
    "formalizadaEn": null,
    "solicitante": null,
    "inmueble": null,
    "documentos": [
      {
        "tipo": "identificacion",
        "descripcion": "Identificación oficial vigente (simulada)",
        "estado": "pendiente",
        "documentoId": null,
        "nombreArchivoSimulado": null,
        "observaciones": null,
        "fecha": null
      },
      {
        "tipo": "comprobante_domicilio",
        "descripcion": "Comprobante de domicilio no mayor a 3 meses (simulado)",
        "estado": "pendiente",
        "documentoId": null,
        "nombreArchivoSimulado": null,
        "observaciones": null,
        "fecha": null
      },
      {
        "tipo": "comprobante_ingresos",
        "descripcion": "Comprobante de ingresos de los últimos 3 meses (simulado)",
        "estado": "pendiente",
        "documentoId": null,
        "nombreArchivoSimulado": null,
        "observaciones": null,
        "fecha": null
      },
      {
        "tipo": "estados_cuenta",
        "descripcion": "Estados de cuenta bancarios de los últimos 3 meses (simulados)",
        "estado": "pendiente",
        "documentoId": null,
        "nombreArchivoSimulado": null,
        "observaciones": null,
        "fecha": null
      }
    ],
    "progreso": {
      "porcentaje": 100,
      "solicitanteCompleto": false,
      "documentosRequeridos": [
        "identificacion",
        "comprobante_domicilio",
        "comprobante_ingresos",
        "estados_cuenta"
      ],
      "documentosEntregados": [],
      "documentosPendientes": [
        "identificacion",
        "comprobante_domicilio",
        "comprobante_ingresos",
        "estados_cuenta"
      ],
      "documentosRechazados": [],
      "inmuebleRequerido": false,
      "inmuebleRegistrado": false,
      "avaluoRequerido": false,
      "avaluoEstado": null,
      "editable": false,
      "siguientePaso": "Solicitud cancelada: proceso terminado"
    }
  },
  "demo": true
}
```

### `GET /api/v1/solicitudes/{solicitud_id}/historial`

Petición real: `GET /api/v1/solicitudes/11/historial` como `cliente11@demo-banco.test` (rol `cliente`) → **HTTP 200**

```json
{
  "ok": true,
  "message": "Historial de estados",
  "data": [
    {
      "id": 40,
      "estadoAnterior": null,
      "estadoNuevo": "borrador",
      "usuarioId": 16,
      "nota": "Solicitud creada",
      "fecha": "2026-11-16T04:04:12"
    },
    {
      "id": 41,
      "estadoAnterior": "borrador",
      "estadoNuevo": "datos_completos",
      "usuarioId": 16,
      "nota": "Expediente completo: avance automático a datos_completos",
      "fecha": "2026-11-16T04:04:13"
    },
    {
      "id": 42,
      "estadoAnterior": "datos_completos",
      "estadoNuevo": "en_avaluo",
      "usuarioId": 16,
      "nota": "Avalúo AVA-DEMO-2026-000005 asignado a USR-DEMO-000003",
      "fecha": "2026-11-16T04:04:13"
    },
    {
      "id": 43,
      "estadoAnterior": "en_avaluo",
      "estadoNuevo": "avaluo_completado",
      "usuarioId": 3,
      "nota": "Avalúo completado automáticamente: valor comercial 2351250.00",
      "fecha": "2026-11-16T04:04:13"
    },
    {
      "id": 44,
      "estadoAnterior": "avaluo_completado",
      "estadoNuevo": "en_analisis",
      "usuarioId": 16,
      "nota": "Análisis de crédito iniciado",
      "fecha": "2026-11-16T04:04:13"
    },
    {
      "id": 45,
      "estadoAnterior": "en_analisis",
      "estadoNuevo": "aprobada",
      "usuarioId": 16,
      "nota": "Solicitud aprobada: cumple todas las reglas del análisis.",
      "fecha": "2026-11-16T04:04:13"
    },
    {
      "id": 46,
      "estadoAnterior": "aprobada",
      "estadoNuevo": "oferta_aceptada",
      "usuarioId": 16,
      "nota": "Oferta aceptada por el cliente",
      "fecha": "2026-11-16T04:04:13"
    },
    {
      "id": 47,
      "estadoAnterior": "oferta_aceptada",
      "estadoNuevo": "formalizada",
      "usuarioId": 16,
      "nota": "Crédito formalizado (demo)",
      "fecha": "2026-11-16T04:04:13"
    }
  ],
  "demo": true
}
```

### `POST /api/v1/solicitudes/{solicitud_id}/analisis`

Petición real: `POST /api/v1/solicitudes/11/analisis` como `cliente11@demo-banco.test` (rol `cliente`) → **HTTP 200**

```json
{
  "ok": true,
  "message": "Análisis completado: solicitud aprobada",
  "data": {
    "id": 11,
    "folio": "SOL-DEMO-2026-000011",
    "usuarioId": 16,
    "producto": {
      "id": 4,
      "nombre": "Hipoteca Fija Demo",
      "tipo": "hipoteca",
      "tasaAnual": 10.5
    },
    "tipo": "hipoteca",
    "montoSolicitado": 1800000.0,
    "plazoMeses": 240,
    "valorInmueble": 2500000.0,
    "enganche": 700000.0,
    "estado": "aprobada",
    "montoAprobado": 1800000.0,
    "tasaAprobada": 9.5,
    "plazoAprobado": 240,
    "mensualidadAprobada": 16778.36,
    "creadaEn": "2026-11-16T04:04:12",
    "actualizadaEn": "2026-11-16T04:04:13",
    "puntajeBuro": 792,
    "resultadoAnalisis": {
      "resolucion": "aprobada",
      "reglas": [
        {
          "regla": "capacidad_pago",
          "descripcion": "Mensualidad ≤ 35% del ingreso neto (ingreso + otros − deudas)",
          "valor": 25.04,
          "limite": 35.0,
          "cumple": true
        },
        {
          "regla": "ltv",
          "descripcion": "Monto ≤ 90% del valor comercial del avalúo",
          "valor": 75.0,
          "limite": 90.0,
          "cumple": true
        },
        {
          "regla": "buro",
          "descripcion": "Puntaje de buró ficticio mínimo",
          "valor": 792,
          "limite": 600,
          "cumple": true
        },
        {
          "regla": "antiguedad_laboral",
          "descripcion": "Antigüedad laboral mínima en meses",
          "valor": 48,
          "limite": 6,
          "cumple": true
        },
        {
          "regla": "edad_fin_plazo",
          "descripcion": "Edad al terminar el plazo del crédito",
          "valor": 56,
          "limite": 70,
          "cumple": true
        }
      ],
      "puntajeBuro": 792,
      "ingresoNeto": 67000.0,
      "pagoMaximo": 23450.0,
      "mensualidadSolicitada": 16778.36,
      "tasaAplicada": 9.5,
      "fechaAnalisis": "2026-11-16"
    },
    "engancheRequerido": 700000.0,
    "motivoResolucion": "Solicitud aprobada: cumple todas las reglas del análisis.",
    "resueltaEn": "2026-11-16T04:04:13",
    "formalizadaEn": null,
    "solicitante": {
      "id": 10,
      "solicitudId": 11,
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
      "ingresoMensual": 65000.0,
      "otrosIngresos": 5000.0,
      "gastosMensuales": 20000.0,
      "deudasMensuales": 3000.0,
      "referencias": [
        {
          "nombre": "María Gómez",
          "telefono": "5511112222",
          "relacion": "hermana"
        },
        {
          "nombre": "Pedro Ruiz",
          "telefono": "5533334444",
          "relacion": "amigo"
        }
      ]
    },
    "inmueble": {
      "id": 5,
      "solicitudId": 11,
      "tipo": "casa",
      "direccion": "Calle Demo 45",
      "colonia": "Del Valle",
      "ciudad": "Ciudad de México",
      "estado": "Ciudad de México",
      "cp": "03100",
      "m2Terreno": 160.0,
      "m2Construccion": 140.0,
      "antiguedadAnios": 8,
      "recamaras": 3,
      "banos": 2,
      "valorEstimadoCliente": 2500000.0,
      "avaluo": {
        "id": 5,
        "folio": "AVA-DEMO-2026-000005",
        "inmuebleId": 5,
        "solicitudId": 11,
        "valuadorId": 3,
        "valuadorNombre": "Homero Canales Trejo",
        "estado": "completado",
        "fechaSolicitud": "2026-11-16T04:04:13",
        "fechaVisita": "2026-11-16T04:04:13",
        "valorComercial": 2400000.0,
        "estadoConservacion": "bueno",
        "observaciones": "Visita realizada: acabados en buen estado, requiere impermeabilización.",
        "generadoAutomaticamente": false
      }
    },
    "documentos": [
      {
        "tipo": "identificacion",
        "descripcion": "Identificación oficial vigente (simulada)",
        "estado": "validado",
        "documentoId": 41,
        "nombreArchivoSimulado": "identificacion_demo.pdf",
        "observaciones": null,
        "fecha": "2026-11-16T04:04:13"
      },
      {
        "tipo": "comprobante_domicilio",
        "descripcion": "Comprobante de domicilio no mayor a 3 meses (simulado)",
        "estado": "entregado",
        "documentoId": 42,
        "nombreArchivoSimulado": "comprobante_domicilio_demo.pdf",
        "observaciones": null,
        "fecha": "2026-11-16T04:04:12"
      },
      {
        "tipo": "comprobante_ingresos",
        "descripcion": "Comprobante de ingresos de los últimos 3 meses (simulado)",
        "estado": "entregado",
        "documentoId": 43,
        "nombreArchivoSimulado": "comprobante_ingresos_demo.pdf",
        "observaciones": null,
        "fecha": "2026-11-16T04:04:12"
      },
      {
        "tipo": "estados_cuenta",
        "descripcion": "Estados de cuenta bancarios de los últimos 3 meses (simulados)",
        "estado": "entregado",
        "documentoId": 44,
        "nombreArchivoSimulado": "estados_cuenta_demo.pdf",
        "observaciones": null,
        "fecha": "2026-11-16T04:04:12"
      },
      {
        "tipo": "escrituras",
        "descripcion": "Escrituras o contrato de compraventa del inmueble (simulado)",
        "estado": "entregado",
        "documentoId": 45,
        "nombreArchivoSimulado": "escrituras_demo.pdf",
        "observaciones": null,
        "fecha": "2026-11-16T04:04:12"
      },
      {
        "tipo": "predial",
        "descripcion": "Boleta predial al corriente del inmueble (simulada)",
        "estado": "entregado",
        "documentoId": 46,
        "nombreArchivoSimulado": "predial_demo.pdf",
        "observaciones": null,
        "fecha": "2026-11-16T04:04:12"
      }
    ],
    "progreso": {
      "porcentaje": 80,
      "solicitanteCompleto": true,
      "documentosRequeridos": [
        "identificacion",
        "comprobante_domicilio",
        "comprobante_ingresos",
        "estados_cuenta",
        "escrituras",
        "predial"
      ],
      "documentosEntregados": [
        "identificacion",
        "comprobante_domicilio",
        "comprobante_ingresos",
        "estados_cuenta",
        "escrituras",
        "predial"
      ],
      "documentosPendientes": [],
      "documentosRechazados": [],
      "inmuebleRequerido": true,
      "inmuebleRegistrado": true,
      "avaluoRequerido": true,
      "avaluoEstado": "completado",
      "editable": false,
      "siguientePaso": "Revisar la oferta y aceptarla o rechazarla"
    }
  },
  "demo": true
}
```

### `PATCH /api/v1/solicitudes/{solicitud_id}/resolucion`

Petición real: `PATCH /api/v1/solicitudes/7/resolucion` como `analista1@demo-banco.test` (rol `analista`) → **HTTP 200**

```json
{
  "ok": true,
  "message": "Resolución actualizada",
  "data": {
    "id": 7,
    "folio": "SOL-DEMO-2026-000007",
    "usuarioId": 12,
    "producto": {
      "id": 1,
      "nombre": "Préstamo Personal Demo Básico",
      "tipo": "prestamo",
      "tasaAnual": 24.0
    },
    "tipo": "prestamo",
    "montoSolicitado": 60000.0,
    "plazoMeses": 24,
    "valorInmueble": null,
    "enganche": null,
    "estado": "aprobada",
    "montoAprobado": 55000.0,
    "tasaAprobada": 22.0,
    "plazoAprobado": 24,
    "mensualidadAprobada": 2853.3,
    "creadaEn": "2026-11-16T04:04:09",
    "actualizadaEn": "2026-11-16T04:04:13",
    "puntajeBuro": 540,
    "resultadoAnalisis": {
      "resolucion": "rechazada",
      "reglas": [
        {
          "regla": "capacidad_pago",
          "descripcion": "Mensualidad ≤ 35% del ingreso neto (ingreso + otros − deudas)",
          "valor": 9.06,
          "limite": 35.0,
          "cumple": true
        },
        {
          "regla": "buro",
          "descripcion": "Puntaje de buró ficticio mínimo",
          "valor": 540,
          "limite": 600,
          "cumple": false
        },
        {
          "regla": "antiguedad_laboral",
          "descripcion": "Antigüedad laboral mínima en meses",
          "valor": 36,
          "limite": 6,
          "cumple": true
        },
        {
          "regla": "edad_fin_plazo",
          "descripcion": "Edad al terminar el plazo del crédito",
          "valor": 37,
          "limite": 70,
          "cumple": true
        }
      ],
      "puntajeBuro": 540,
      "ingresoNeto": 35000.0,
      "pagoMaximo": 12250.0,
      "mensualidadSolicitada": 3172.27,
      "tasaAplicada": 24.0,
      "fechaAnalisis": "2026-11-16",
      "sobrescritura": {
        "analistaId": 4,
        "estadoAnterior": "rechazada",
        "estadoNuevo": "aprobada",
        "motivo": "Revisión manual: historial de pagos comprobado.",
        "fecha": "2026-11-16T04:04:13"
      }
    },
    "engancheRequerido": null,
    "motivoResolucion": "Revisión manual: historial de pagos comprobado.",
    "resueltaEn": "2026-11-16T04:04:13",
    "formalizadaEn": null,
    "solicitante": {
      "id": 7,
      "solicitudId": 7,
      "fechaNacimiento": "1991-11-02",
      "curpFicticia": "DEMO911102HQMMHZN3",
      "estadoCivil": "soltero",
      "dependientes": 2,
      "domicilio": "Peatonal Mónaco 348 Interior 734",
      "ciudad": "San Elias los altos",
      "empresa": "Grupo Jurado, Meza y Maya (Demo)",
      "puesto": "Trabajador de cuidados personales a domicilio",
      "tipoEmpleo": "asalariado",
      "antiguedadMeses": 36,
      "ingresoMensual": 35000.0,
      "otrosIngresos": 0.0,
      "gastosMensuales": 10500.0,
      "deudasMensuales": 0.0,
      "referencias": [
        {
          "nombre": "Margarita Blanco",
          "telefono": "5516091779",
          "relacion": "familiar"
        },
        {
          "nombre": "Hernán Corona",
          "telefono": "5582708086",
          "relacion": "amistad"
        }
      ]
    },
    "inmueble": null,
    "documentos": [
      {
        "tipo": "identificacion",
        "descripcion": "Identificación oficial vigente (simulada)",
        "estado": "entregado",
        "documentoId": 27,
        "nombreArchivoSimulado": "identificacion_demo.pdf",
        "observaciones": null,
        "fecha": "2026-11-16T04:04:09"
      },
      {
        "tipo": "comprobante_domicilio",
        "descripcion": "Comprobante de domicilio no mayor a 3 meses (simulado)",
        "estado": "entregado",
        "documentoId": 28,
        "nombreArchivoSimulado": "comprobante_domicilio_demo.pdf",
        "observaciones": null,
        "fecha": "2026-11-16T04:04:09"
      },
      {
        "tipo": "comprobante_ingresos",
        "descripcion": "Comprobante de ingresos de los últimos 3 meses (simulado)",
        "estado": "entregado",
        "documentoId": 29,
        "nombreArchivoSimulado": "comprobante_ingresos_demo.pdf",
        "observaciones": null,
        "fecha": "2026-11-16T04:04:09"
      },
      {
        "tipo": "estados_cuenta",
        "descripcion": "Estados de cuenta bancarios de los últimos 3 meses (simulados)",
        "estado": "entregado",
        "documentoId": 30,
        "nombreArchivoSimulado": "estados_cuenta_demo.pdf",
        "observaciones": null,
        "fecha": "2026-11-16T04:04:09"
      }
    ],
    "progreso": {
      "porcentaje": 80,
      "solicitanteCompleto": true,
      "documentosRequeridos": [
        "identificacion",
        "comprobante_domicilio",
        "comprobante_ingresos",
        "estados_cuenta"
      ],
      "documentosEntregados": [
        "identificacion",
        "comprobante_domicilio",
        "comprobante_ingresos",
        "estados_cuenta"
      ],
      "documentosPendientes": [],
      "documentosRechazados": [],
      "inmuebleRequerido": false,
      "inmuebleRegistrado": false,
      "avaluoRequerido": false,
      "avaluoEstado": null,
      "editable": false,
      "siguientePaso": "Revisar la oferta y aceptarla o rechazarla"
    }
  },
  "demo": true
}
```

### `GET /api/v1/solicitudes/{solicitud_id}/oferta`

Petición real: `GET /api/v1/solicitudes/11/oferta` como `cliente11@demo-banco.test` (rol `cliente`) → **HTTP 200**

```json
{
  "ok": true,
  "message": "Oferta demostrativa",
  "data": {
    "solicitudId": 11,
    "folio": "SOL-DEMO-2026-000011",
    "estado": "aprobada",
    "producto": "Hipoteca Fija Demo",
    "monto": 1800000.0,
    "tasaAnual": 9.5,
    "plazoMeses": 240,
    "mensualidad": 16778.36,
    "totalPagar": 4026807.27,
    "totalIntereses": 2226807.27,
    "catDemo": 9.97,
    "engancheRequerido": 700000.0,
    "condicionada": false,
    "condiciones": "Solicitud aprobada: cumple todas las reglas del análisis.",
    "fechaEmision": "2026-11-16T04:04:13",
    "vigenteHasta": "2026-12-01T04:04:13",
    "vigente": true,
    "leyenda": "OFERTA DEMOSTRATIVA - NO ES UNA OFERTA REAL"
  },
  "demo": true
}
```

### `POST /api/v1/solicitudes/{solicitud_id}/oferta/aceptar`

Petición real: `POST /api/v1/solicitudes/11/oferta/aceptar` como `cliente11@demo-banco.test` (rol `cliente`) → **HTTP 200**

```json
{
  "ok": true,
  "message": "Oferta aceptada",
  "data": {
    "id": 11,
    "folio": "SOL-DEMO-2026-000011",
    "usuarioId": 16,
    "producto": {
      "id": 4,
      "nombre": "Hipoteca Fija Demo",
      "tipo": "hipoteca",
      "tasaAnual": 10.5
    },
    "tipo": "hipoteca",
    "montoSolicitado": 1800000.0,
    "plazoMeses": 240,
    "valorInmueble": 2500000.0,
    "enganche": 700000.0,
    "estado": "oferta_aceptada",
    "montoAprobado": 1800000.0,
    "tasaAprobada": 9.5,
    "plazoAprobado": 240,
    "mensualidadAprobada": 16778.36,
    "creadaEn": "2026-11-16T04:04:12",
    "actualizadaEn": "2026-11-16T04:04:13",
    "puntajeBuro": 792,
    "resultadoAnalisis": {
      "resolucion": "aprobada",
      "reglas": [
        {
          "regla": "capacidad_pago",
          "descripcion": "Mensualidad ≤ 35% del ingreso neto (ingreso + otros − deudas)",
          "valor": 25.04,
          "limite": 35.0,
          "cumple": true
        },
        {
          "regla": "ltv",
          "descripcion": "Monto ≤ 90% del valor comercial del avalúo",
          "valor": 75.0,
          "limite": 90.0,
          "cumple": true
        },
        {
          "regla": "buro",
          "descripcion": "Puntaje de buró ficticio mínimo",
          "valor": 792,
          "limite": 600,
          "cumple": true
        },
        {
          "regla": "antiguedad_laboral",
          "descripcion": "Antigüedad laboral mínima en meses",
          "valor": 48,
          "limite": 6,
          "cumple": true
        },
        {
          "regla": "edad_fin_plazo",
          "descripcion": "Edad al terminar el plazo del crédito",
          "valor": 56,
          "limite": 70,
          "cumple": true
        }
      ],
      "puntajeBuro": 792,
      "ingresoNeto": 67000.0,
      "pagoMaximo": 23450.0,
      "mensualidadSolicitada": 16778.36,
      "tasaAplicada": 9.5,
      "fechaAnalisis": "2026-11-16"
    },
    "engancheRequerido": 700000.0,
    "motivoResolucion": "Solicitud aprobada: cumple todas las reglas del análisis.",
    "resueltaEn": "2026-11-16T04:04:13",
    "formalizadaEn": null,
    "solicitante": {
      "id": 10,
      "solicitudId": 11,
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
      "ingresoMensual": 65000.0,
      "otrosIngresos": 5000.0,
      "gastosMensuales": 20000.0,
      "deudasMensuales": 3000.0,
      "referencias": [
        {
          "nombre": "María Gómez",
          "telefono": "5511112222",
          "relacion": "hermana"
        },
        {
          "nombre": "Pedro Ruiz",
          "telefono": "5533334444",
          "relacion": "amigo"
        }
      ]
    },
    "inmueble": {
      "id": 5,
      "solicitudId": 11,
      "tipo": "casa",
      "direccion": "Calle Demo 45",
      "colonia": "Del Valle",
      "ciudad": "Ciudad de México",
      "estado": "Ciudad de México",
      "cp": "03100",
      "m2Terreno": 160.0,
      "m2Construccion": 140.0,
      "antiguedadAnios": 8,
      "recamaras": 3,
      "banos": 2,
      "valorEstimadoCliente": 2500000.0,
      "avaluo": {
        "id": 5,
        "folio": "AVA-DEMO-2026-000005",
        "inmuebleId": 5,
        "solicitudId": 11,
        "valuadorId": 3,
        "valuadorNombre": "Homero Canales Trejo",
        "estado": "completado",
        "fechaSolicitud": "2026-11-16T04:04:13",
        "fechaVisita": "2026-11-16T04:04:13",
        "valorComercial": 2400000.0,
        "estadoConservacion": "bueno",
        "observaciones": "Visita realizada: acabados en buen estado, requiere impermeabilización.",
        "generadoAutomaticamente": false
      }
    },
    "documentos": [
      {
        "tipo": "identificacion",
        "descripcion": "Identificación oficial vigente (simulada)",
        "estado": "validado",
        "documentoId": 41,
        "nombreArchivoSimulado": "identificacion_demo.pdf",
        "observaciones": null,
        "fecha": "2026-11-16T04:04:13"
      },
      {
        "tipo": "comprobante_domicilio",
        "descripcion": "Comprobante de domicilio no mayor a 3 meses (simulado)",
        "estado": "entregado",
        "documentoId": 42,
        "nombreArchivoSimulado": "comprobante_domicilio_demo.pdf",
        "observaciones": null,
        "fecha": "2026-11-16T04:04:12"
      },
      {
        "tipo": "comprobante_ingresos",
        "descripcion": "Comprobante de ingresos de los últimos 3 meses (simulado)",
        "estado": "entregado",
        "documentoId": 43,
        "nombreArchivoSimulado": "comprobante_ingresos_demo.pdf",
        "observaciones": null,
        "fecha": "2026-11-16T04:04:12"
      },
      {
        "tipo": "estados_cuenta",
        "descripcion": "Estados de cuenta bancarios de los últimos 3 meses (simulados)",
        "estado": "entregado",
        "documentoId": 44,
        "nombreArchivoSimulado": "estados_cuenta_demo.pdf",
        "observaciones": null,
        "fecha": "2026-11-16T04:04:12"
      },
      {
        "tipo": "escrituras",
        "descripcion": "Escrituras o contrato de compraventa del inmueble (simulado)",
        "estado": "entregado",
        "documentoId": 45,
        "nombreArchivoSimulado": "escrituras_demo.pdf",
        "observaciones": null,
        "fecha": "2026-11-16T04:04:12"
      },
      {
        "tipo": "predial",
        "descripcion": "Boleta predial al corriente del inmueble (simulada)",
        "estado": "entregado",
        "documentoId": 46,
        "nombreArchivoSimulado": "predial_demo.pdf",
        "observaciones": null,
        "fecha": "2026-11-16T04:04:12"
      }
    ],
    "progreso": {
      "porcentaje": 90,
      "solicitanteCompleto": true,
      "documentosRequeridos": [
        "identificacion",
        "comprobante_domicilio",
        "comprobante_ingresos",
        "estados_cuenta",
        "escrituras",
        "predial"
      ],
      "documentosEntregados": [
        "identificacion",
        "comprobante_domicilio",
        "comprobante_ingresos",
        "estados_cuenta",
        "escrituras",
        "predial"
      ],
      "documentosPendientes": [],
      "documentosRechazados": [],
      "inmuebleRequerido": true,
      "inmuebleRegistrado": true,
      "avaluoRequerido": true,
      "avaluoEstado": "completado",
      "editable": false,
      "siguientePaso": "Formalizar el crédito (POST /formalizar)"
    }
  },
  "demo": true
}
```

### `POST /api/v1/solicitudes/{solicitud_id}/oferta/rechazar`

Petición real: `POST /api/v1/solicitudes/5/oferta/rechazar` como `cliente5@demo-banco.test` (rol `cliente`) → **HTTP 200**

```json
{
  "ok": true,
  "message": "Oferta rechazada",
  "data": {
    "id": 5,
    "folio": "SOL-DEMO-2026-000005",
    "usuarioId": 10,
    "producto": {
      "id": 3,
      "nombre": "Préstamo Nómina Demo",
      "tipo": "prestamo",
      "tasaAnual": 15.0
    },
    "tipo": "prestamo",
    "montoSolicitado": 90000.0,
    "plazoMeses": 36,
    "valorInmueble": null,
    "enganche": null,
    "estado": "oferta_rechazada",
    "montoAprobado": 90000.0,
    "tasaAprobada": 15.0,
    "plazoAprobado": 36,
    "mensualidadAprobada": 3119.88,
    "creadaEn": "2026-11-16T04:04:09",
    "actualizadaEn": "2026-11-16T04:04:13",
    "puntajeBuro": 720,
    "resultadoAnalisis": {
      "resolucion": "aprobada",
      "reglas": [
        {
          "regla": "capacidad_pago",
          "descripcion": "Mensualidad ≤ 35% del ingreso neto (ingreso + otros − deudas)",
          "valor": 7.8,
          "limite": 35.0,
          "cumple": true
        },
        {
          "regla": "buro",
          "descripcion": "Puntaje de buró ficticio mínimo",
          "valor": 720,
          "limite": 600,
          "cumple": true
        },
        {
          "regla": "antiguedad_laboral",
          "descripcion": "Antigüedad laboral mínima en meses",
          "valor": 36,
          "limite": 6,
          "cumple": true
        },
        {
          "regla": "edad_fin_plazo",
          "descripcion": "Edad al terminar el plazo del crédito",
          "valor": 38,
          "limite": 70,
          "cumple": true
        }
      ],
      "puntajeBuro": 720,
      "ingresoNeto": 40000.0,
      "pagoMaximo": 14000.0,
      "mensualidadSolicitada": 3119.88,
      "tasaAplicada": 15.0,
      "fechaAnalisis": "2026-11-16"
    },
    "engancheRequerido": null,
    "motivoResolucion": "Solicitud aprobada: cumple todas las reglas del análisis.",
    "resueltaEn": "2026-11-16T04:04:09",
    "formalizadaEn": null,
    "solicitante": {
      "id": 5,
      "solicitudId": 5,
      "fechaNacimiento": "1991-11-02",
      "curpFicticia": "DEMO911102HPF322F5",
      "estadoCivil": "casado",
      "dependientes": 2,
      "domicilio": "Diagonal Aguascalientes 436 Interior 995",
      "ciudad": "San Esparta los bajos",
      "empresa": "Industrias Rojas y de la O (Demo)",
      "puesto": "Peón de jardinería y horticultura",
      "tipoEmpleo": "asalariado",
      "antiguedadMeses": 36,
      "ingresoMensual": 40000.0,
      "otrosIngresos": 0.0,
      "gastosMensuales": 12000.0,
      "deudasMensuales": 0.0,
      "referencias": [
        {
          "nombre": "Enrique Limón",
          "telefono": "5517016608",
          "relacion": "familiar"
        },
        {
          "nombre": "Laura Meza",
          "telefono": "5580199488",
          "relacion": "amistad"
        }
      ]
    },
    "inmueble": null,
    "documentos": [
      {
        "tipo": "identificacion",
        "descripcion": "Identificación oficial vigente (simulada)",
        "estado": "entregado",
        "documentoId": 18,
        "nombreArchivoSimulado": "identificacion_demo.pdf",
        "observaciones": null,
        "fecha": "2026-11-16T04:04:09"
      },
      {
        "tipo": "comprobante_domicilio",
        "descripcion": "Comprobante de domicilio no mayor a 3 meses (simulado)",
        "estado": "entregado",
        "documentoId": 19,
        "nombreArchivoSimulado": "comprobante_domicilio_demo.pdf",
        "observaciones": null,
        "fecha": "2026-11-16T04:04:09"
      },
      {
        "tipo": "comprobante_ingresos",
        "descripcion": "Comprobante de ingresos de los últimos 3 meses (simulado)",
        "estado": "entregado",
        "documentoId": 20,
        "nombreArchivoSimulado": "comprobante_ingresos_demo.pdf",
        "observaciones": null,
        "fecha": "2026-11-16T04:04:09"
      }
    ],
    "progreso": {
      "porcentaje": 100,
      "solicitanteCompleto": true,
      "documentosRequeridos": [
        "identificacion",
        "comprobante_domicilio",
        "comprobante_ingresos"
      ],
      "documentosEntregados": [
        "identificacion",
        "comprobante_domicilio",
        "comprobante_ingresos"
      ],
      "documentosPendientes": [],
      "documentosRechazados": [],
      "inmuebleRequerido": false,
      "inmuebleRegistrado": false,
      "avaluoRequerido": false,
      "avaluoEstado": null,
      "editable": false,
      "siguientePaso": "Oferta rechazada: proceso terminado"
    }
  },
  "demo": true
}
```

### `POST /api/v1/solicitudes/{solicitud_id}/formalizar`

Petición real: `POST /api/v1/solicitudes/11/formalizar` como `cliente11@demo-banco.test` (rol `cliente`) → **HTTP 200**

```json
{
  "ok": true,
  "message": "Crédito formalizado",
  "data": {
    "id": 11,
    "folio": "SOL-DEMO-2026-000011",
    "usuarioId": 16,
    "producto": {
      "id": 4,
      "nombre": "Hipoteca Fija Demo",
      "tipo": "hipoteca",
      "tasaAnual": 10.5
    },
    "tipo": "hipoteca",
    "montoSolicitado": 1800000.0,
    "plazoMeses": 240,
    "valorInmueble": 2500000.0,
    "enganche": 700000.0,
    "estado": "formalizada",
    "montoAprobado": 1800000.0,
    "tasaAprobada": 9.5,
    "plazoAprobado": 240,
    "mensualidadAprobada": 16778.36,
    "creadaEn": "2026-11-16T04:04:12",
    "actualizadaEn": "2026-11-16T04:04:13",
    "puntajeBuro": 792,
    "resultadoAnalisis": {
      "resolucion": "aprobada",
      "reglas": [
        {
          "regla": "capacidad_pago",
          "descripcion": "Mensualidad ≤ 35% del ingreso neto (ingreso + otros − deudas)",
          "valor": 25.04,
          "limite": 35.0,
          "cumple": true
        },
        {
          "regla": "ltv",
          "descripcion": "Monto ≤ 90% del valor comercial del avalúo",
          "valor": 75.0,
          "limite": 90.0,
          "cumple": true
        },
        {
          "regla": "buro",
          "descripcion": "Puntaje de buró ficticio mínimo",
          "valor": 792,
          "limite": 600,
          "cumple": true
        },
        {
          "regla": "antiguedad_laboral",
          "descripcion": "Antigüedad laboral mínima en meses",
          "valor": 48,
          "limite": 6,
          "cumple": true
        },
        {
          "regla": "edad_fin_plazo",
          "descripcion": "Edad al terminar el plazo del crédito",
          "valor": 56,
          "limite": 70,
          "cumple": true
        }
      ],
      "puntajeBuro": 792,
      "ingresoNeto": 67000.0,
      "pagoMaximo": 23450.0,
      "mensualidadSolicitada": 16778.36,
      "tasaAplicada": 9.5,
      "fechaAnalisis": "2026-11-16"
    },
    "engancheRequerido": 700000.0,
    "motivoResolucion": "Solicitud aprobada: cumple todas las reglas del análisis.",
    "resueltaEn": "2026-11-16T04:04:13",
    "formalizadaEn": "2026-11-16T04:04:13",
    "solicitante": {
      "id": 10,
      "solicitudId": 11,
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
      "ingresoMensual": 65000.0,
      "otrosIngresos": 5000.0,
      "gastosMensuales": 20000.0,
      "deudasMensuales": 3000.0,
      "referencias": [
        {
          "nombre": "María Gómez",
          "telefono": "5511112222",
          "relacion": "hermana"
        },
        {
          "nombre": "Pedro Ruiz",
          "telefono": "5533334444",
          "relacion": "amigo"
        }
      ]
    },
    "inmueble": {
      "id": 5,
      "solicitudId": 11,
      "tipo": "casa",
      "direccion": "Calle Demo 45",
      "colonia": "Del Valle",
      "ciudad": "Ciudad de México",
      "estado": "Ciudad de México",
      "cp": "03100",
      "m2Terreno": 160.0,
      "m2Construccion": 140.0,
      "antiguedadAnios": 8,
      "recamaras": 3,
      "banos": 2,
      "valorEstimadoCliente": 2500000.0,
      "avaluo": {
        "id": 5,
        "folio": "AVA-DEMO-2026-000005",
        "inmuebleId": 5,
        "solicitudId": 11,
        "valuadorId": 3,
        "valuadorNombre": "Homero Canales Trejo",
        "estado": "completado",
        "fechaSolicitud": "2026-11-16T04:04:13",
        "fechaVisita": "2026-11-16T04:04:13",
        "valorComercial": 2400000.0,
        "estadoConservacion": "bueno",
        "observaciones": "Visita realizada: acabados en buen estado, requiere impermeabilización.",
        "generadoAutomaticamente": false
      }
    },
    "documentos": [
      {
        "tipo": "identificacion",
        "descripcion": "Identificación oficial vigente (simulada)",
        "estado": "validado",
        "documentoId": 41,
        "nombreArchivoSimulado": "identificacion_demo.pdf",
        "observaciones": null,
        "fecha": "2026-11-16T04:04:13"
      },
      {
        "tipo": "comprobante_domicilio",
        "descripcion": "Comprobante de domicilio no mayor a 3 meses (simulado)",
        "estado": "entregado",
        "documentoId": 42,
        "nombreArchivoSimulado": "comprobante_domicilio_demo.pdf",
        "observaciones": null,
        "fecha": "2026-11-16T04:04:12"
      },
      {
        "tipo": "comprobante_ingresos",
        "descripcion": "Comprobante de ingresos de los últimos 3 meses (simulado)",
        "estado": "entregado",
        "documentoId": 43,
        "nombreArchivoSimulado": "comprobante_ingresos_demo.pdf",
        "observaciones": null,
        "fecha": "2026-11-16T04:04:12"
      },
      {
        "tipo": "estados_cuenta",
        "descripcion": "Estados de cuenta bancarios de los últimos 3 meses (simulados)",
        "estado": "entregado",
        "documentoId": 44,
        "nombreArchivoSimulado": "estados_cuenta_demo.pdf",
        "observaciones": null,
        "fecha": "2026-11-16T04:04:12"
      },
      {
        "tipo": "escrituras",
        "descripcion": "Escrituras o contrato de compraventa del inmueble (simulado)",
        "estado": "entregado",
        "documentoId": 45,
        "nombreArchivoSimulado": "escrituras_demo.pdf",
        "observaciones": null,
        "fecha": "2026-11-16T04:04:12"
      },
      {
        "tipo": "predial",
        "descripcion": "Boleta predial al corriente del inmueble (simulada)",
        "estado": "entregado",
        "documentoId": 46,
        "nombreArchivoSimulado": "predial_demo.pdf",
        "observaciones": null,
        "fecha": "2026-11-16T04:04:12"
      }
    ],
    "progreso": {
      "porcentaje": 100,
      "solicitanteCompleto": true,
      "documentosRequeridos": [
        "identificacion",
        "comprobante_domicilio",
        "comprobante_ingresos",
        "estados_cuenta",
        "escrituras",
        "predial"
      ],
      "documentosEntregados": [
        "identificacion",
        "comprobante_domicilio",
        "comprobante_ingresos",
        "estados_cuenta",
        "escrituras",
        "predial"
      ],
      "documentosPendientes": [],
      "documentosRechazados": [],
      "inmuebleRequerido": true,
      "inmuebleRegistrado": true,
      "avaluoRequerido": true,
      "avaluoEstado": "completado",
      "editable": false,
      "siguientePaso": "Crédito formalizado: consultar la tabla de amortización"
    }
  },
  "demo": true
}
```

### `GET /api/v1/solicitudes/{solicitud_id}/amortizacion`

Petición real: `GET /api/v1/solicitudes/11/amortizacion` como `cliente11@demo-banco.test` (rol `cliente`) → **HTTP 200**

```json
{
  "ok": true,
  "message": "Tabla de amortización del crédito",
  "data": {
    "monto": 1800000.0,
    "tasaAnual": 9.5,
    "plazoMeses": 240,
    "mensualidad": 16778.36,
    "totalIntereses": 2226807.27,
    "totalPagar": 4026807.27,
    "tabla": [
      {
        "numero": 1,
        "pago": 16778.36,
        "capital": 2528.36,
        "interes": 14250.0,
        "saldo": 1797471.64,
        "fechaPago": "2026-12-16"
      },
      {
        "numero": 2,
        "pago": 16778.36,
        "capital": 2548.38,
        "interes": 14229.98,
        "saldo": 1794923.26,
        "fechaPago": "2027-01-16"
      },
      "… 237 filas omitidas …",
      {
        "numero": 240,
        "pago": 16779.23,
        "capital": 16647.44,
        "interes": 131.79,
        "saldo": 0.0,
        "fechaPago": "2046-11-16"
      }
    ],
    "leyenda": "CRÉDITO DEMOSTRATIVO SOL-DEMO-2026-000011 - SIN VALIDEZ REAL"
  },
  "demo": true
}
```

_Nota: `tabla` recortada: se muestran las filas 1, 2 y 240 de 240._

### `PUT /api/v1/solicitudes/{solicitud_id}/solicitante`

Petición real: `PUT /api/v1/solicitudes/11/solicitante` como `cliente11@demo-banco.test` (rol `cliente`) → **HTTP 200**

```json
{
  "ok": true,
  "message": "Datos del solicitante guardados",
  "data": {
    "id": 10,
    "solicitudId": 11,
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
    "ingresoMensual": 65000.0,
    "otrosIngresos": 5000.0,
    "gastosMensuales": 20000.0,
    "deudasMensuales": 3000.0,
    "referencias": [
      {
        "nombre": "María Gómez",
        "telefono": "5511112222",
        "relacion": "hermana"
      },
      {
        "nombre": "Pedro Ruiz",
        "telefono": "5533334444",
        "relacion": "amigo"
      }
    ]
  },
  "demo": true
}
```

### `GET /api/v1/solicitudes/{solicitud_id}/solicitante`

Petición real: `GET /api/v1/solicitudes/11/solicitante` como `cliente11@demo-banco.test` (rol `cliente`) → **HTTP 200**

```json
{
  "ok": true,
  "message": "Datos del solicitante",
  "data": {
    "id": 10,
    "solicitudId": 11,
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
    "ingresoMensual": 65000.0,
    "otrosIngresos": 5000.0,
    "gastosMensuales": 20000.0,
    "deudasMensuales": 3000.0,
    "referencias": [
      {
        "nombre": "María Gómez",
        "telefono": "5511112222",
        "relacion": "hermana"
      },
      {
        "nombre": "Pedro Ruiz",
        "telefono": "5533334444",
        "relacion": "amigo"
      }
    ]
  },
  "demo": true
}
```

### `GET /api/v1/solicitudes/{solicitud_id}/documentos`

Petición real: `GET /api/v1/solicitudes/11/documentos` como `cliente11@demo-banco.test` (rol `cliente`) → **HTTP 200**

```json
{
  "ok": true,
  "message": "Documentos de la solicitud",
  "data": [
    {
      "tipo": "identificacion",
      "descripcion": "Identificación oficial vigente (simulada)",
      "estado": "pendiente",
      "documentoId": null,
      "nombreArchivoSimulado": null,
      "observaciones": null,
      "fecha": null
    },
    {
      "tipo": "comprobante_domicilio",
      "descripcion": "Comprobante de domicilio no mayor a 3 meses (simulado)",
      "estado": "pendiente",
      "documentoId": null,
      "nombreArchivoSimulado": null,
      "observaciones": null,
      "fecha": null
    },
    {
      "tipo": "comprobante_ingresos",
      "descripcion": "Comprobante de ingresos de los últimos 3 meses (simulado)",
      "estado": "pendiente",
      "documentoId": null,
      "nombreArchivoSimulado": null,
      "observaciones": null,
      "fecha": null
    },
    {
      "tipo": "estados_cuenta",
      "descripcion": "Estados de cuenta bancarios de los últimos 3 meses (simulados)",
      "estado": "pendiente",
      "documentoId": null,
      "nombreArchivoSimulado": null,
      "observaciones": null,
      "fecha": null
    },
    {
      "tipo": "escrituras",
      "descripcion": "Escrituras o contrato de compraventa del inmueble (simulado)",
      "estado": "pendiente",
      "documentoId": null,
      "nombreArchivoSimulado": null,
      "observaciones": null,
      "fecha": null
    },
    {
      "tipo": "predial",
      "descripcion": "Boleta predial al corriente del inmueble (simulada)",
      "estado": "pendiente",
      "documentoId": null,
      "nombreArchivoSimulado": null,
      "observaciones": null,
      "fecha": null
    }
  ],
  "demo": true
}
```

### `POST /api/v1/solicitudes/{solicitud_id}/documentos`

Petición real: `POST /api/v1/solicitudes/11/documentos` como `cliente11@demo-banco.test` (rol `cliente`) → **HTTP 201**

```json
{
  "ok": true,
  "message": "Documento entregado",
  "data": {
    "id": 41,
    "solicitudId": 11,
    "tipo": "identificacion",
    "nombreArchivoSimulado": "identificacion_demo.pdf",
    "estado": "entregado",
    "observaciones": null,
    "fecha": "2026-11-16T04:04:12"
  },
  "demo": true
}
```

### `PATCH /api/v1/solicitudes/{solicitud_id}/documentos/{documento_id}`

Petición real: `PATCH /api/v1/solicitudes/11/documentos/41` como `analista1@demo-banco.test` (rol `analista`) → **HTTP 200**

```json
{
  "ok": true,
  "message": "Documento validado",
  "data": {
    "id": 41,
    "solicitudId": 11,
    "tipo": "identificacion",
    "nombreArchivoSimulado": "identificacion_demo.pdf",
    "estado": "validado",
    "observaciones": null,
    "fecha": "2026-11-16T04:04:13"
  },
  "demo": true
}
```

### `PUT /api/v1/solicitudes/{solicitud_id}/inmueble`

Petición real: `PUT /api/v1/solicitudes/11/inmueble` como `cliente11@demo-banco.test` (rol `cliente`) → **HTTP 200**

```json
{
  "ok": true,
  "message": "Inmueble registrado. La solicitud avanzó a datos_completos",
  "data": {
    "id": 5,
    "solicitudId": 11,
    "tipo": "casa",
    "direccion": "Calle Demo 45",
    "colonia": "Del Valle",
    "ciudad": "Ciudad de México",
    "estado": "Ciudad de México",
    "cp": "03100",
    "m2Terreno": 160.0,
    "m2Construccion": 140.0,
    "antiguedadAnios": 8,
    "recamaras": 3,
    "banos": 2,
    "valorEstimadoCliente": 2500000.0,
    "avaluo": null
  },
  "demo": true
}
```

### `GET /api/v1/solicitudes/{solicitud_id}/inmueble`

Petición real: `GET /api/v1/solicitudes/11/inmueble` como `cliente11@demo-banco.test` (rol `cliente`) → **HTTP 200**

```json
{
  "ok": true,
  "message": "Inmueble",
  "data": {
    "id": 5,
    "solicitudId": 11,
    "tipo": "casa",
    "direccion": "Calle Demo 45",
    "colonia": "Del Valle",
    "ciudad": "Ciudad de México",
    "estado": "Ciudad de México",
    "cp": "03100",
    "m2Terreno": 160.0,
    "m2Construccion": 140.0,
    "antiguedadAnios": 8,
    "recamaras": 3,
    "banos": 2,
    "valorEstimadoCliente": 2500000.0,
    "avaluo": {
      "id": 5,
      "folio": "AVA-DEMO-2026-000005",
      "inmuebleId": 5,
      "solicitudId": 11,
      "valuadorId": 3,
      "valuadorNombre": "Homero Canales Trejo",
      "estado": "completado",
      "fechaSolicitud": "2026-11-16T04:04:13",
      "fechaVisita": "2026-11-16T04:04:13",
      "valorComercial": 2400000.0,
      "estadoConservacion": "bueno",
      "observaciones": "Visita realizada: acabados en buen estado, requiere impermeabilización.",
      "generadoAutomaticamente": false
    }
  },
  "demo": true
}
```

### `POST /api/v1/solicitudes/{solicitud_id}/avaluo`

Petición real: `POST /api/v1/solicitudes/11/avaluo` como `cliente11@demo-banco.test` (rol `cliente`) → **HTTP 201**

```json
{
  "ok": true,
  "message": "Avalúo AVA-DEMO-2026-000005 completado",
  "data": {
    "id": 5,
    "folio": "AVA-DEMO-2026-000005",
    "inmuebleId": 5,
    "solicitudId": 11,
    "valuadorId": 3,
    "valuadorNombre": "Homero Canales Trejo",
    "estado": "completado",
    "fechaSolicitud": "2026-11-16T04:04:13",
    "fechaVisita": "2026-11-16T04:04:13",
    "valorComercial": 2351250.0,
    "estadoConservacion": "bueno",
    "observaciones": "Avalúo DEMO generado automáticamente. Inmueble tipo casa de 8 años en Del Valle, Ciudad de México; estado de conservación bueno. Valor comercial 5.95% por debajo del valor estimado por el cliente.",
    "generadoAutomaticamente": true
  },
  "demo": true
}
```

### `GET /api/v1/avaluos`

Petición real: `GET /api/v1/avaluos?page=1&limit=10` como `valuador2@demo-banco.test` (rol `valuador`) → **HTTP 200**

```json
{
  "ok": true,
  "message": "Avalúos",
  "data": [
    {
      "id": 5,
      "folio": "AVA-DEMO-2026-000005",
      "inmuebleId": 5,
      "solicitudId": 11,
      "valuadorId": 3,
      "valuadorNombre": "Homero Canales Trejo",
      "estado": "completado",
      "fechaSolicitud": "2026-11-16T04:04:13",
      "fechaVisita": "2026-11-16T04:04:13",
      "valorComercial": 2351250.0,
      "estadoConservacion": "bueno",
      "observaciones": "Avalúo DEMO generado automáticamente. Inmueble tipo casa de 8 años en Del Valle, Ciudad de México; estado de conservación bueno. Valor comercial 5.95% por debajo del valor estimado por el cliente.",
      "generadoAutomaticamente": true
    },
    {
      "id": 4,
      "folio": "AVA-DEMO-2026-000004",
      "inmuebleId": 4,
      "solicitudId": 8,
      "valuadorId": 3,
      "valuadorNombre": "Homero Canales Trejo",
      "estado": "completado",
      "fechaSolicitud": "2026-11-16T04:04:09",
      "fechaVisita": "2026-11-16T04:04:09",
      "valorComercial": 1790600.0,
      "estadoConservacion": "excelente",
      "observaciones": "Avalúo DEMO generado automáticamente. Inmueble tipo departamento de 4 años en Col. de Jesús, San Gonzalo los altos; estado de conservación excelente. Valor comercial 10.47% por debajo del valor estimado por el cliente.",
      "generadoAutomaticamente": true
    },
    {
      "id": 2,
      "folio": "AVA-DEMO-2026-000002",
      "inmuebleId": 2,
      "solicitudId": 4,
      "valuadorId": 3,
      "valuadorNombre": "Homero Canales Trejo",
      "estado": "completado",
      "fechaSolicitud": "2026-11-16T04:04:09",
      "fechaVisita": "2026-11-16T04:04:09",
      "valorComercial": 4037400.0,
      "estadoConservacion": "excelente",
      "observaciones": "Avalúo DEMO generado automáticamente. Inmueble tipo casa de 3 años en Col. Cavazos, Vieja Suiza; estado de conservación excelente. Valor comercial 10.28% por debajo del valor estimado por el cliente.",
      "generadoAutomaticamente": true
    }
  ],
  "meta": {
    "page": 1,
    "limit": 10,
    "total": 3
  },
  "demo": true
}
```

### `GET /api/v1/avaluos/{avaluo_id}`

Petición real: `GET /api/v1/avaluos/5` como `valuador2@demo-banco.test` (rol `valuador`) → **HTTP 200**

```json
{
  "ok": true,
  "message": "Avalúo",
  "data": {
    "id": 5,
    "folio": "AVA-DEMO-2026-000005",
    "inmuebleId": 5,
    "solicitudId": 11,
    "valuadorId": 3,
    "valuadorNombre": "Homero Canales Trejo",
    "estado": "completado",
    "fechaSolicitud": "2026-11-16T04:04:13",
    "fechaVisita": "2026-11-16T04:04:13",
    "valorComercial": 2351250.0,
    "estadoConservacion": "bueno",
    "observaciones": "Avalúo DEMO generado automáticamente. Inmueble tipo casa de 8 años en Del Valle, Ciudad de México; estado de conservación bueno. Valor comercial 5.95% por debajo del valor estimado por el cliente.",
    "generadoAutomaticamente": true
  },
  "demo": true
}
```

### `PATCH /api/v1/avaluos/{avaluo_id}/resultado`

Petición real: `PATCH /api/v1/avaluos/5/resultado` como `valuador2@demo-banco.test` (rol `valuador`) → **HTTP 200**

```json
{
  "ok": true,
  "message": "Resultado del avalúo actualizado",
  "data": {
    "id": 5,
    "folio": "AVA-DEMO-2026-000005",
    "inmuebleId": 5,
    "solicitudId": 11,
    "valuadorId": 3,
    "valuadorNombre": "Homero Canales Trejo",
    "estado": "completado",
    "fechaSolicitud": "2026-11-16T04:04:13",
    "fechaVisita": "2026-11-16T04:04:13",
    "valorComercial": 2400000.0,
    "estadoConservacion": "bueno",
    "observaciones": "Visita realizada: acabados en buen estado, requiere impermeabilización.",
    "generadoAutomaticamente": false
  },
  "demo": true
}
```

### `GET /api/v1/cuentas`

Petición real: `GET /api/v1/cuentas` como `cliente11@demo-banco.test` (rol `cliente`) → **HTTP 200**

```json
{
  "ok": true,
  "message": "Cuentas",
  "data": [
    {
      "id": 15,
      "numeroEnmascarado": "****6296",
      "tipo": "debito",
      "saldo": 39318.82,
      "moneda": "MXN",
      "estado": "activa",
      "creadaEn": "2026-05-19T04:04:09"
    },
    {
      "id": 16,
      "numeroEnmascarado": "****0589",
      "tipo": "ahorro",
      "saldo": 108773.05,
      "moneda": "MXN",
      "estado": "activa",
      "creadaEn": "2026-05-19T04:04:09"
    }
  ],
  "demo": true
}
```

### `GET /api/v1/cuentas/{cuenta_id}`

Petición real: `GET /api/v1/cuentas/15` como `cliente11@demo-banco.test` (rol `cliente`) → **HTTP 200**

```json
{
  "ok": true,
  "message": "Cuenta",
  "data": {
    "id": 15,
    "numeroEnmascarado": "****6296",
    "tipo": "debito",
    "saldo": 39318.82,
    "moneda": "MXN",
    "estado": "activa",
    "creadaEn": "2026-05-19T04:04:09"
  },
  "demo": true
}
```

### `GET /api/v1/cuentas/{cuenta_id}/movimientos`

Petición real: `GET /api/v1/cuentas/15/movimientos?page=1&limit=3` como `cliente11@demo-banco.test` (rol `cliente`) → **HTTP 200**

```json
{
  "ok": true,
  "message": "Movimientos",
  "data": [
    {
      "id": 639,
      "tipo": "pago",
      "concepto": "Pago de servicio Luz (CFE Demo)",
      "monto": -1794.0,
      "saldoResultante": 39318.82,
      "referencia": "MOV-DEMO-20261022-72F60958",
      "fecha": "2026-10-22T04:16:33"
    },
    {
      "id": 638,
      "tipo": "retiro",
      "concepto": "Retiro en cajero Demo",
      "monto": -500.0,
      "saldoResultante": 41112.82,
      "referencia": "MOV-DEMO-20261019-B719BB68",
      "fecha": "2026-10-19T10:15:45"
    },
    {
      "id": 637,
      "tipo": "compra",
      "concepto": "Compra en Restaurante Demo",
      "monto": -414.84,
      "saldoResultante": 41612.82,
      "referencia": "MOV-DEMO-20261015-4D8670BD",
      "fecha": "2026-10-15T01:12:03"
    }
  ],
  "meta": {
    "page": 1,
    "limit": 3,
    "total": 32
  },
  "demo": true
}
```

## e) Catálogo de códigos de error

Se encontraron 69 lugares donde se lanza un error: los `ApiError(...)`, las llamadas a `obtener_o_404(...)` (404 con código propio) y las llamadas a `respuesta_error(...)` en los manejadores y el middleware. Para cada error se listan los endpoints cuyo código llega a la función que lo lanza, incluidas las dependencias de autenticación. Los textos entre `{}` se rellenan en tiempo de ejecución.

> La lista de endpoints es un **análisis estático**: indica dónde *puede* producirse cada error según el código, no dónde se produce siempre. En `TRANSICION_INVALIDA` se excluyen las funciones que comprueban el estado antes de cambiarlo (`intentar_completar`, `ajustar_avaluo`, `sobrescribir_resolucion`), porque nunca lo lanzan.

| Código | HTTP | Mensaje | Origen en código | Endpoint(s) donde puede ocurrir |
|---|---|---|---|---|
| `AVALUO_NO_EDITABLE` | 400 | El avalúo ya no puede ajustarse: la solicitud está en '{solicitud.estado}' | services.evaluacion.ajustar_avaluo | `PATCH /api/v1/avaluos/{avaluo_id}/resultado` |
| `AVALUO_PENDIENTE` | 400 | La hipoteca requiere un avalúo completado | services.evaluacion.ejecutar_analisis | `POST /api/v1/solicitudes/{solicitud_id}/analisis` |
| `CAMPO_OBLIGATORIO` | 400 | El campo '{campo}' no puede quedar vacío | services.usuarios.actualizar_perfil | `PATCH /api/v1/usuarios/perfil` |
| `CREDITO_NO_FORMALIZADO` | 400 | La tabla de amortización solo está disponible para créditos formalizados | services.solicitudes.amortizacion | `GET /api/v1/solicitudes/{solicitud_id}/amortizacion` |
| `DOCUMENTOS_RECHAZADOS` | 400 | Hay documentos rechazados; vuelva a entregarlos antes de continuar | services.evaluacion.ejecutar_analisis, services.evaluacion.solicitar_avaluo | `POST /api/v1/solicitudes/{solicitud_id}/analisis`<br>`POST /api/v1/solicitudes/{solicitud_id}/avaluo` |
| `DOCUMENTO_NO_REQUERIDO` | 400 | El documento '{tipo}' no es requerido por este producto | services.expediente.entregar_documento | `POST /api/v1/solicitudes/{solicitud_id}/documentos` |
| `EDAD_EXCEDE_PLAZO` | 400 | El solicitante debe tener menos de {settings.EDAD_MAXIMA_FIN_PLAZO} años al terminar el plazo (tendría {edad_fin}) | services.expediente._validar_edad | `PUT /api/v1/solicitudes/{solicitud_id}/solicitante` |
| `EDAD_INSUFICIENTE` | 400 | El solicitante debe ser mayor de {settings.EDAD_MINIMA} años | services.expediente._validar_edad | `PUT /api/v1/solicitudes/{solicitud_id}/solicitante` |
| `ENGANCHE_INSUFICIENTE` | 400 | El enganche ({enganche}) es menor al mínimo requerido ({minimo}, {producto.enganche_min_pct}% del valor del inmueble) | services.solicitudes.crear | `POST /api/v1/solicitudes` |
| `FECHA_NACIMIENTO_INVALIDA` | 400 | La fecha de nacimiento debe ser anterior a hoy | services.expediente._validar_edad | `PUT /api/v1/solicitudes/{solicitud_id}/solicitante` |
| `INMUEBLE_NO_REGISTRADO` | 400 | La solicitud no tiene inmueble registrado | services.evaluacion.solicitar_avaluo | `POST /api/v1/solicitudes/{solicitud_id}/avaluo` |
| `LIMITE_SOLICITUDES` | 400 | No puede tener más de {settings.MAX_SOLICITUDES_ACTIVAS} solicitudes activas | services.solicitudes.crear | `POST /api/v1/solicitudes` |
| `MONTO_EXCEDE_VALOR` | 400 | El monto debe ser menor al valor del inmueble / El monto solicitado debe ser menor al valor del inmueble | services.evaluacion.sobrescribir_resolucion, services.solicitudes.crear | `PATCH /api/v1/solicitudes/{solicitud_id}/resolucion`<br>`POST /api/v1/solicitudes` |
| `MONTO_FUERA_DE_RANGO` | 400 | El monto debe estar entre {producto.monto_min} y {producto.monto_max} | services.simuladores.validar_monto_plazo | `PATCH /api/v1/solicitudes/{solicitud_id}/resolucion`<br>`POST /api/v1/simuladores/hipoteca`<br>`POST /api/v1/simuladores/prestamo`<br>`POST /api/v1/solicitudes` |
| `OFERTA_NO_DISPONIBLE` | 400 | La solicitud en estado '{solicitud.estado}' no tiene una oferta disponible | services.solicitudes.construir_oferta | `GET /api/v1/solicitudes/{solicitud_id}/oferta` |
| `OFERTA_VENCIDA` | 400 | La oferta venció el {vence.isoformat()} | services.solicitudes.aceptar_oferta | `POST /api/v1/solicitudes/{solicitud_id}/oferta/aceptar` |
| `OPERACION_NO_PERMITIDA` | 400 | No puede desactivar su propio usuario | services.admin.cambiar_estado_usuario | `PATCH /api/v1/admin/usuarios/{usuario_id}/estado` |
| `PASSWORD_INCORRECTA` | 400 | La contraseña actual no es correcta | services.usuarios.cambiar_password | `PATCH /api/v1/usuarios/perfil/password` |
| `PASSWORD_REPETIDA` | 400 | La nueva contraseña debe ser distinta de la actual | services.usuarios.cambiar_password | `PATCH /api/v1/usuarios/perfil/password` |
| `PLAZO_NO_PERMITIDO` | 400 | El plazo debe ser uno de {producto.plazos_meses} meses | services.simuladores.validar_monto_plazo | `PATCH /api/v1/solicitudes/{solicitud_id}/resolucion`<br>`POST /api/v1/simuladores/hipoteca`<br>`POST /api/v1/simuladores/prestamo`<br>`POST /api/v1/solicitudes` |
| `PRODUCTO_INACTIVO` | 400 | El producto no está disponible / El producto no está disponible para nuevas solicitudes | services.simuladores._producto_para, services.solicitudes.crear | `POST /api/v1/simuladores/hipoteca`<br>`POST /api/v1/simuladores/prestamo`<br>`POST /api/v1/solicitudes` |
| `RANGO_FECHAS_INVALIDO` | 400 | La fecha 'desde' debe ser menor o igual a 'hasta' | services.cuentas.movimientos | `GET /api/v1/cuentas/{cuenta_id}/movimientos` |
| `RESOLUCION_NO_EDITABLE` | 400 | Solo se puede sobrescribir la resolución en estados {sorted(E.ESTADOS_RESUELTOS)} (estado actual: '{solicitud.estado}') | services.evaluacion.sobrescribir_resolucion | `PATCH /api/v1/solicitudes/{solicitud_id}/resolucion` |
| `SIN_CAMBIOS` | 400 | No se indicó ningún campo para actualizar | services.usuarios.actualizar_perfil | `PATCH /api/v1/usuarios/perfil` |
| `SIN_VALUADORES` | 400 | No hay valuadores activos disponibles | services.evaluacion.solicitar_avaluo | `POST /api/v1/solicitudes/{solicitud_id}/avaluo` |
| `SOLICITANTE_NO_REGISTRADO` | 400 | La solicitud no tiene datos del solicitante | services.evaluacion.ejecutar_analisis | `POST /api/v1/solicitudes/{solicitud_id}/analisis` |
| `SOLICITUD_FINALIZADA` | 400 | La solicitud está en un estado final | services.expediente.revisar_documento | `PATCH /api/v1/solicitudes/{solicitud_id}/documentos/{documento_id}` |
| `SOLICITUD_NO_EDITABLE` | 400 | La solicitud está en estado '{solicitud.estado}' y ya no puede modificarse | services.comun.validar_editable | `POST /api/v1/solicitudes/{solicitud_id}/documentos`<br>`PUT /api/v1/solicitudes/{solicitud_id}/inmueble`<br>`PUT /api/v1/solicitudes/{solicitud_id}/solicitante` |
| `SOLO_HIPOTECA` | 400 | Esta operación solo aplica a solicitudes de hipoteca | services.evaluacion._solo_hipoteca | `GET /api/v1/solicitudes/{solicitud_id}/inmueble`<br>`POST /api/v1/solicitudes/{solicitud_id}/avaluo`<br>`PUT /api/v1/solicitudes/{solicitud_id}/inmueble` |
| `TIPO_PRODUCTO_INVALIDO` | 400 | El producto indicado no es de tipo {tipo} | services.simuladores._producto_para | `POST /api/v1/simuladores/hipoteca`<br>`POST /api/v1/simuladores/prestamo` |
| `TRANSICION_INVALIDA` | 400 | Estado actual desconocido: '{actual}' / La transición de '{actual}' a '{nuevo}' solo aplica a solicitudes de tipo {requerido} \| No se puede pasar de '{actual}' a '{nuevo}' | utils.estados.validar_transicion | `POST /api/v1/solicitudes/{solicitud_id}/analisis`<br>`POST /api/v1/solicitudes/{solicitud_id}/avaluo`<br>`POST /api/v1/solicitudes/{solicitud_id}/cancelar`<br>`POST /api/v1/solicitudes/{solicitud_id}/formalizar`<br>`POST /api/v1/solicitudes/{solicitud_id}/oferta/aceptar`<br>`POST /api/v1/solicitudes/{solicitud_id}/oferta/rechazar` |
| `VALOR_INMUEBLE_REQUERIDO` | 400 | El valor del inmueble es obligatorio en hipotecas | services.solicitudes.crear | `POST /api/v1/solicitudes` |
| `CREDENCIALES_INVALIDAS` | 401 | Correo o contraseña incorrectos | services.auth.login | `POST /api/v1/auth/login` |
| `NO_AUTENTICADO` | 401 | Se requiere autenticación (Authorization: Bearer <token>) | dependencies.auth.get_usuario_actual | `DELETE /api/v1/productos/{producto_id}`<br>`GET /api/v1/admin/estadisticas`<br>`GET /api/v1/admin/usuarios`<br>`GET /api/v1/admin/usuarios/{usuario_id}`<br>`GET /api/v1/auth/me`<br>`GET /api/v1/avaluos`<br>`GET /api/v1/avaluos/{avaluo_id}`<br>`GET /api/v1/cuentas`<br>`GET /api/v1/cuentas/{cuenta_id}`<br>`GET /api/v1/cuentas/{cuenta_id}/movimientos`<br>`GET /api/v1/solicitudes`<br>`GET /api/v1/solicitudes/{solicitud_id}`<br>`GET /api/v1/solicitudes/{solicitud_id}/amortizacion`<br>`GET /api/v1/solicitudes/{solicitud_id}/documentos`<br>`GET /api/v1/solicitudes/{solicitud_id}/historial`<br>`GET /api/v1/solicitudes/{solicitud_id}/inmueble`<br>`GET /api/v1/solicitudes/{solicitud_id}/oferta`<br>`GET /api/v1/solicitudes/{solicitud_id}/solicitante`<br>`GET /api/v1/usuarios/perfil`<br>`PATCH /api/v1/admin/usuarios/{usuario_id}/estado`<br>`PATCH /api/v1/avaluos/{avaluo_id}/resultado`<br>`PATCH /api/v1/solicitudes/{solicitud_id}/documentos/{documento_id}`<br>`PATCH /api/v1/solicitudes/{solicitud_id}/resolucion`<br>`PATCH /api/v1/usuarios/perfil`<br>`PATCH /api/v1/usuarios/perfil/password`<br>`POST /api/v1/admin/usuarios`<br>`POST /api/v1/productos`<br>`POST /api/v1/solicitudes`<br>`POST /api/v1/solicitudes/{solicitud_id}/analisis`<br>`POST /api/v1/solicitudes/{solicitud_id}/avaluo`<br>`POST /api/v1/solicitudes/{solicitud_id}/cancelar`<br>`POST /api/v1/solicitudes/{solicitud_id}/documentos`<br>`POST /api/v1/solicitudes/{solicitud_id}/formalizar`<br>`POST /api/v1/solicitudes/{solicitud_id}/oferta/aceptar`<br>`POST /api/v1/solicitudes/{solicitud_id}/oferta/rechazar`<br>`PUT /api/v1/productos/{producto_id}`<br>`PUT /api/v1/solicitudes/{solicitud_id}/inmueble`<br>`PUT /api/v1/solicitudes/{solicitud_id}/solicitante` |
| `TOKEN_EXPIRADO` | 401 | El token ha expirado, inicie sesión de nuevo | core.security.decodificar_token | `DELETE /api/v1/productos/{producto_id}`<br>`GET /api/v1/admin/estadisticas`<br>`GET /api/v1/admin/usuarios`<br>`GET /api/v1/admin/usuarios/{usuario_id}`<br>`GET /api/v1/auth/me`<br>`GET /api/v1/avaluos`<br>`GET /api/v1/avaluos/{avaluo_id}`<br>`GET /api/v1/cuentas`<br>`GET /api/v1/cuentas/{cuenta_id}`<br>`GET /api/v1/cuentas/{cuenta_id}/movimientos`<br>`GET /api/v1/solicitudes`<br>`GET /api/v1/solicitudes/{solicitud_id}`<br>`GET /api/v1/solicitudes/{solicitud_id}/amortizacion`<br>`GET /api/v1/solicitudes/{solicitud_id}/documentos`<br>`GET /api/v1/solicitudes/{solicitud_id}/historial`<br>`GET /api/v1/solicitudes/{solicitud_id}/inmueble`<br>`GET /api/v1/solicitudes/{solicitud_id}/oferta`<br>`GET /api/v1/solicitudes/{solicitud_id}/solicitante`<br>`GET /api/v1/usuarios/perfil`<br>`PATCH /api/v1/admin/usuarios/{usuario_id}/estado`<br>`PATCH /api/v1/avaluos/{avaluo_id}/resultado`<br>`PATCH /api/v1/solicitudes/{solicitud_id}/documentos/{documento_id}`<br>`PATCH /api/v1/solicitudes/{solicitud_id}/resolucion`<br>`PATCH /api/v1/usuarios/perfil`<br>`PATCH /api/v1/usuarios/perfil/password`<br>`POST /api/v1/admin/usuarios`<br>`POST /api/v1/productos`<br>`POST /api/v1/solicitudes`<br>`POST /api/v1/solicitudes/{solicitud_id}/analisis`<br>`POST /api/v1/solicitudes/{solicitud_id}/avaluo`<br>`POST /api/v1/solicitudes/{solicitud_id}/cancelar`<br>`POST /api/v1/solicitudes/{solicitud_id}/documentos`<br>`POST /api/v1/solicitudes/{solicitud_id}/formalizar`<br>`POST /api/v1/solicitudes/{solicitud_id}/oferta/aceptar`<br>`POST /api/v1/solicitudes/{solicitud_id}/oferta/rechazar`<br>`PUT /api/v1/productos/{producto_id}`<br>`PUT /api/v1/solicitudes/{solicitud_id}/inmueble`<br>`PUT /api/v1/solicitudes/{solicitud_id}/solicitante` |
| `TOKEN_INVALIDO` | 401 | El token no es válido / El token no contiene la información requerida / El usuario del token no existe | core.security.decodificar_token, dependencies.auth.get_usuario_actual | `DELETE /api/v1/productos/{producto_id}`<br>`GET /api/v1/admin/estadisticas`<br>`GET /api/v1/admin/usuarios`<br>`GET /api/v1/admin/usuarios/{usuario_id}`<br>`GET /api/v1/auth/me`<br>`GET /api/v1/avaluos`<br>`GET /api/v1/avaluos/{avaluo_id}`<br>`GET /api/v1/cuentas`<br>`GET /api/v1/cuentas/{cuenta_id}`<br>`GET /api/v1/cuentas/{cuenta_id}/movimientos`<br>`GET /api/v1/solicitudes`<br>`GET /api/v1/solicitudes/{solicitud_id}`<br>`GET /api/v1/solicitudes/{solicitud_id}/amortizacion`<br>`GET /api/v1/solicitudes/{solicitud_id}/documentos`<br>`GET /api/v1/solicitudes/{solicitud_id}/historial`<br>`GET /api/v1/solicitudes/{solicitud_id}/inmueble`<br>`GET /api/v1/solicitudes/{solicitud_id}/oferta`<br>`GET /api/v1/solicitudes/{solicitud_id}/solicitante`<br>`GET /api/v1/usuarios/perfil`<br>`PATCH /api/v1/admin/usuarios/{usuario_id}/estado`<br>`PATCH /api/v1/avaluos/{avaluo_id}/resultado`<br>`PATCH /api/v1/solicitudes/{solicitud_id}/documentos/{documento_id}`<br>`PATCH /api/v1/solicitudes/{solicitud_id}/resolucion`<br>`PATCH /api/v1/usuarios/perfil`<br>`PATCH /api/v1/usuarios/perfil/password`<br>`POST /api/v1/admin/usuarios`<br>`POST /api/v1/productos`<br>`POST /api/v1/solicitudes`<br>`POST /api/v1/solicitudes/{solicitud_id}/analisis`<br>`POST /api/v1/solicitudes/{solicitud_id}/avaluo`<br>`POST /api/v1/solicitudes/{solicitud_id}/cancelar`<br>`POST /api/v1/solicitudes/{solicitud_id}/documentos`<br>`POST /api/v1/solicitudes/{solicitud_id}/formalizar`<br>`POST /api/v1/solicitudes/{solicitud_id}/oferta/aceptar`<br>`POST /api/v1/solicitudes/{solicitud_id}/oferta/rechazar`<br>`PUT /api/v1/productos/{producto_id}`<br>`PUT /api/v1/solicitudes/{solicitud_id}/inmueble`<br>`PUT /api/v1/solicitudes/{solicitud_id}/solicitante` |
| `ACCESO_DENEGADO` | 403 | No tiene permiso para acceder a esta solicitud / La solicitud no le pertenece / La cuenta no le pertenece / No tiene permiso para ver este avalúo / El avalúo no está asignado a este valuador | services.comun.solicitud_con_acceso, services.comun.solicitud_propia, services.comun.solicitud_propia_o_personal, services.cuentas.obtener, services.evaluacion.ajustar_avaluo, services.evaluacion.obtener_avaluo | `GET /api/v1/avaluos/{avaluo_id}`<br>`GET /api/v1/cuentas/{cuenta_id}`<br>`GET /api/v1/cuentas/{cuenta_id}/movimientos`<br>`GET /api/v1/solicitudes/{solicitud_id}`<br>`GET /api/v1/solicitudes/{solicitud_id}/amortizacion`<br>`GET /api/v1/solicitudes/{solicitud_id}/documentos`<br>`GET /api/v1/solicitudes/{solicitud_id}/historial`<br>`GET /api/v1/solicitudes/{solicitud_id}/inmueble`<br>`GET /api/v1/solicitudes/{solicitud_id}/oferta`<br>`GET /api/v1/solicitudes/{solicitud_id}/solicitante`<br>`PATCH /api/v1/avaluos/{avaluo_id}/resultado`<br>`POST /api/v1/solicitudes/{solicitud_id}/analisis`<br>`POST /api/v1/solicitudes/{solicitud_id}/avaluo`<br>`POST /api/v1/solicitudes/{solicitud_id}/cancelar`<br>`POST /api/v1/solicitudes/{solicitud_id}/documentos`<br>`POST /api/v1/solicitudes/{solicitud_id}/formalizar`<br>`POST /api/v1/solicitudes/{solicitud_id}/oferta/aceptar`<br>`POST /api/v1/solicitudes/{solicitud_id}/oferta/rechazar`<br>`PUT /api/v1/solicitudes/{solicitud_id}/inmueble`<br>`PUT /api/v1/solicitudes/{solicitud_id}/solicitante` |
| `PERMISO_INSUFICIENTE` | 403 | Su rol no tiene permiso para esta operación | dependencies.auth._dependencia | `DELETE /api/v1/productos/{producto_id}`<br>`GET /api/v1/admin/estadisticas`<br>`GET /api/v1/admin/usuarios`<br>`GET /api/v1/admin/usuarios/{usuario_id}`<br>`GET /api/v1/avaluos`<br>`GET /api/v1/cuentas`<br>`GET /api/v1/cuentas/{cuenta_id}`<br>`GET /api/v1/cuentas/{cuenta_id}/movimientos`<br>`GET /api/v1/solicitudes`<br>`GET /api/v1/solicitudes/{solicitud_id}/amortizacion`<br>`GET /api/v1/solicitudes/{solicitud_id}/oferta`<br>`PATCH /api/v1/admin/usuarios/{usuario_id}/estado`<br>`PATCH /api/v1/avaluos/{avaluo_id}/resultado`<br>`PATCH /api/v1/solicitudes/{solicitud_id}/documentos/{documento_id}`<br>`PATCH /api/v1/solicitudes/{solicitud_id}/resolucion`<br>`POST /api/v1/admin/usuarios`<br>`POST /api/v1/productos`<br>`POST /api/v1/solicitudes`<br>`POST /api/v1/solicitudes/{solicitud_id}/analisis`<br>`POST /api/v1/solicitudes/{solicitud_id}/avaluo`<br>`POST /api/v1/solicitudes/{solicitud_id}/cancelar`<br>`POST /api/v1/solicitudes/{solicitud_id}/documentos`<br>`POST /api/v1/solicitudes/{solicitud_id}/formalizar`<br>`POST /api/v1/solicitudes/{solicitud_id}/oferta/aceptar`<br>`POST /api/v1/solicitudes/{solicitud_id}/oferta/rechazar`<br>`PUT /api/v1/productos/{producto_id}`<br>`PUT /api/v1/solicitudes/{solicitud_id}/inmueble`<br>`PUT /api/v1/solicitudes/{solicitud_id}/solicitante` |
| `RED_NO_PERMITIDA` | 403 | La petición proviene de una red no autorizada | core.middlewares.dispatch | todos, si `ALLOWED_NETWORKS` está configurado y la IP no pertenece |
| `USUARIO_INACTIVO` | 403 | El usuario está desactivado / El usuario está desactivado; contacte al administrador | dependencies.auth.get_usuario_actual, services.auth.login | `DELETE /api/v1/productos/{producto_id}`<br>`GET /api/v1/admin/estadisticas`<br>`GET /api/v1/admin/usuarios`<br>`GET /api/v1/admin/usuarios/{usuario_id}`<br>`GET /api/v1/auth/me`<br>`GET /api/v1/avaluos`<br>`GET /api/v1/avaluos/{avaluo_id}`<br>`GET /api/v1/cuentas`<br>`GET /api/v1/cuentas/{cuenta_id}`<br>`GET /api/v1/cuentas/{cuenta_id}/movimientos`<br>`GET /api/v1/solicitudes`<br>`GET /api/v1/solicitudes/{solicitud_id}`<br>`GET /api/v1/solicitudes/{solicitud_id}/amortizacion`<br>`GET /api/v1/solicitudes/{solicitud_id}/documentos`<br>`GET /api/v1/solicitudes/{solicitud_id}/historial`<br>`GET /api/v1/solicitudes/{solicitud_id}/inmueble`<br>`GET /api/v1/solicitudes/{solicitud_id}/oferta`<br>`GET /api/v1/solicitudes/{solicitud_id}/solicitante`<br>`GET /api/v1/usuarios/perfil`<br>`PATCH /api/v1/admin/usuarios/{usuario_id}/estado`<br>`PATCH /api/v1/avaluos/{avaluo_id}/resultado`<br>`PATCH /api/v1/solicitudes/{solicitud_id}/documentos/{documento_id}`<br>`PATCH /api/v1/solicitudes/{solicitud_id}/resolucion`<br>`PATCH /api/v1/usuarios/perfil`<br>`PATCH /api/v1/usuarios/perfil/password`<br>`POST /api/v1/admin/usuarios`<br>`POST /api/v1/auth/login`<br>`POST /api/v1/productos`<br>`POST /api/v1/solicitudes`<br>`POST /api/v1/solicitudes/{solicitud_id}/analisis`<br>`POST /api/v1/solicitudes/{solicitud_id}/avaluo`<br>`POST /api/v1/solicitudes/{solicitud_id}/cancelar`<br>`POST /api/v1/solicitudes/{solicitud_id}/documentos`<br>`POST /api/v1/solicitudes/{solicitud_id}/formalizar`<br>`POST /api/v1/solicitudes/{solicitud_id}/oferta/aceptar`<br>`POST /api/v1/solicitudes/{solicitud_id}/oferta/rechazar`<br>`PUT /api/v1/productos/{producto_id}`<br>`PUT /api/v1/solicitudes/{solicitud_id}/inmueble`<br>`PUT /api/v1/solicitudes/{solicitud_id}/solicitante` |
| `AVALUO_NO_ENCONTRADO` | 404 | El avalúo con id {id} no existe | services.evaluacion.ajustar_avaluo, services.evaluacion.obtener_avaluo | `GET /api/v1/avaluos/{avaluo_id}`<br>`PATCH /api/v1/avaluos/{avaluo_id}/resultado` |
| `CUENTA_NO_ENCONTRADA` | 404 | La cuenta con id {id} no existe | services.cuentas.obtener | `GET /api/v1/cuentas/{cuenta_id}`<br>`GET /api/v1/cuentas/{cuenta_id}/movimientos` |
| `DOCUMENTO_NO_ENCONTRADO` | 404 | El documento con id {id} no existe / El documento no pertenece a esta solicitud | services.expediente.revisar_documento | `PATCH /api/v1/solicitudes/{solicitud_id}/documentos/{documento_id}` |
| `INMUEBLE_NO_REGISTRADO` | 404 | La solicitud aún no tiene inmueble registrado | services.evaluacion.obtener_inmueble | `GET /api/v1/solicitudes/{solicitud_id}/inmueble` |
| `PRODUCTO_NO_ENCONTRADO` | 404 | El producto con id {id} no existe | services.productos.obtener | `DELETE /api/v1/productos/{producto_id}`<br>`GET /api/v1/productos/{producto_id}`<br>`GET /api/v1/productos/{producto_id}/requisitos`<br>`POST /api/v1/simuladores/hipoteca`<br>`POST /api/v1/simuladores/prestamo`<br>`POST /api/v1/solicitudes`<br>`PUT /api/v1/productos/{producto_id}` |
| `RUTA_NO_ENCONTRADA` | 404 | La ruta solicitada no existe | core.exceptions._manejar_http | cualquier ruta inexistente |
| `SOLICITANTE_NO_REGISTRADO` | 404 | La solicitud aún no tiene datos del solicitante | services.expediente.obtener_solicitante | `GET /api/v1/solicitudes/{solicitud_id}/solicitante` |
| `SOLICITUD_NO_ENCONTRADA` | 404 | La solicitud con id {id} no existe | services.comun.obtener_solicitud | `GET /api/v1/solicitudes/{solicitud_id}`<br>`GET /api/v1/solicitudes/{solicitud_id}/amortizacion`<br>`GET /api/v1/solicitudes/{solicitud_id}/documentos`<br>`GET /api/v1/solicitudes/{solicitud_id}/historial`<br>`GET /api/v1/solicitudes/{solicitud_id}/inmueble`<br>`GET /api/v1/solicitudes/{solicitud_id}/oferta`<br>`GET /api/v1/solicitudes/{solicitud_id}/solicitante`<br>`PATCH /api/v1/solicitudes/{solicitud_id}/documentos/{documento_id}`<br>`PATCH /api/v1/solicitudes/{solicitud_id}/resolucion`<br>`POST /api/v1/solicitudes/{solicitud_id}/analisis`<br>`POST /api/v1/solicitudes/{solicitud_id}/avaluo`<br>`POST /api/v1/solicitudes/{solicitud_id}/cancelar`<br>`POST /api/v1/solicitudes/{solicitud_id}/documentos`<br>`POST /api/v1/solicitudes/{solicitud_id}/formalizar`<br>`POST /api/v1/solicitudes/{solicitud_id}/oferta/aceptar`<br>`POST /api/v1/solicitudes/{solicitud_id}/oferta/rechazar`<br>`PUT /api/v1/solicitudes/{solicitud_id}/inmueble`<br>`PUT /api/v1/solicitudes/{solicitud_id}/solicitante` |
| `USUARIO_NO_ENCONTRADO` | 404 | El usuario con id {id} no existe | services.admin.obtener_usuario | `GET /api/v1/admin/usuarios/{usuario_id}`<br>`PATCH /api/v1/admin/usuarios/{usuario_id}/estado` |
| `METODO_NO_PERMITIDO` | 405 | Método HTTP no permitido para esta ruta | core.exceptions._manejar_http | cualquier ruta existente llamada con un método no soportado |
| `DOCUMENTO_YA_ENTREGADO` | 409 | El documento '{tipo}' ya fue entregado (estado: {documento.estado}) | services.expediente.entregar_documento | `POST /api/v1/solicitudes/{solicitud_id}/documentos` |
| `EMAIL_REGISTRADO` | 409 | El correo electrónico ya está registrado | services.usuarios.crear_usuario | `POST /api/v1/admin/usuarios`<br>`POST /api/v1/usuarios/registro` |
| `PRODUCTO_DUPLICADO` | 409 | Ya existe un producto con el nombre '{nombre}' | services.productos._validar_nombre_unico | `POST /api/v1/productos`<br>`PUT /api/v1/productos/{producto_id}` |
| `ERROR_VALIDACION` | 422 | Los datos enviados no son válidos | core.exceptions._manejar_validacion | cualquier endpoint con parámetros de ruta/query o cuerpo (incluye JSON mal formado) |
| `LIMITE_PETICIONES_EXCEDIDO` | 429 | Demasiadas peticiones. Intente de nuevo en un momento. | core.exceptions.manejar_rate_limit | todos (login: 5/min; resto: 100/min) |
| `ERROR_INTERNO` | 500 | Ocurrió un error interno en el servidor | core.exceptions._manejar_error_interno | todos (error no controlado; no expone trazas) |

Total: **56 códigos distintos**.

## f) Enums

Valores exactos de las constantes del código. Donde un esquema usa `Literal`, se comprueba que coincida con la constante.

| Enum | Fuente | Valores | Coincide con el `Literal` del esquema |
|---|---|---|---|
| Roles | app/models/usuario.py · ROLES | `cliente`, `valuador`, `analista`, `admin` | — |
| Roles creables por admin | AdminUsuarioIn.rol | `valuador`, `analista`, `admin` | — |
| Estados de solicitud | app/utils/estados.py · ESTADOS | `borrador`, `datos_completos`, `en_avaluo`, `avaluo_completado`, `en_analisis`, `aprobada`, `condicionada`, `rechazada`, `oferta_aceptada`, `oferta_rechazada`, `formalizada`, `cancelada` | — |
| Tipos de producto / solicitud | app/models/producto.py · TIPOS_PRODUCTO | `prestamo`, `hipoteca` | sí |
| Tipos de documento | app/models/producto.py · TIPOS_DOCUMENTO | `identificacion`, `comprobante_domicilio`, `comprobante_ingresos`, `estados_cuenta`, `escrituras`, `predial` | sí |
| Documentos solo de hipoteca | DOCUMENTOS_SOLO_HIPOTECA | `escrituras`, `predial` | — |
| Estados de documento (BD) | app/models/documento.py · ESTADOS_DOCUMENTO | `entregado`, `validado`, `rechazado` | — |
| Estados de documento (en listados) | services/progreso.documentos_estado | `pendiente`, `entregado`, `validado`, `rechazado` | — |
| Revisión de documento (analista) | DocumentoRevisionIn.estado | `validado`, `rechazado` | — |
| Estado civil | app/models/solicitante.py · ESTADOS_CIVILES | `soltero`, `casado`, `divorciado`, `viudo`, `union_libre` | sí |
| Tipo de empleo | app/models/solicitante.py · TIPOS_EMPLEO | `asalariado`, `independiente` | sí |
| Tipo de inmueble | app/models/inmueble.py · TIPOS_INMUEBLE | `casa`, `departamento`, `terreno` | sí |
| Estado de conservación | app/models/avaluo.py · ESTADOS_CONSERVACION | `excelente`, `bueno`, `regular`, `malo` | sí |
| Estados de avalúo | app/models/avaluo.py · ESTADOS_AVALUO | `solicitado`, `completado` | — |
| Resolución (sobrescritura) | ResolucionIn.estado | `aprobada`, `condicionada`, `rechazada` | — |
| Tipos de movimiento | app/models/movimiento.py · TIPOS_MOVIMIENTO | `deposito`, `retiro`, `pago`, `compra`, `transferencia` | — |
| Tipos de cuenta | app/models/cuenta.py · TIPOS_CUENTA | `debito`, `ahorro` | — |
| Estados de cuenta | app/models/cuenta.py · ESTADOS_CUENTA | `activa`, `bloqueada` | — |

El filtro `tipo` de movimientos acepta: `deposito`, `retiro`, `pago`, `compra`, `transferencia`.

## g) Máquina de estados

Las transiciones se copian de `app/utils/estados.py` (`TRANSICIONES` y `RESTRICCIONES_TIPO`). El endpoint de cada una sale de buscar qué funciones de servicio llaman a `cambiar_estado(..., E.<DESTINO>)` y qué endpoints llegan a esas funciones.

| Desde | Hacia | Restricción de tipo | Endpoint(s) que la provocan |
|---|---|---|---|
| (inicio) | `borrador` | — | `POST /api/v1/solicitudes` |
| `borrador` | `datos_completos` | — | `POST /api/v1/solicitudes/{solicitud_id}/documentos`<br>`PUT /api/v1/solicitudes/{solicitud_id}/inmueble`<br>`PUT /api/v1/solicitudes/{solicitud_id}/solicitante` |
| `borrador` | `cancelada` | — | `POST /api/v1/solicitudes/{solicitud_id}/cancelar` |
| `datos_completos` | `en_avaluo` | hipoteca | `POST /api/v1/solicitudes/{solicitud_id}/avaluo` |
| `datos_completos` | `en_analisis` | prestamo | `POST /api/v1/solicitudes/{solicitud_id}/analisis` |
| `datos_completos` | `cancelada` | — | `POST /api/v1/solicitudes/{solicitud_id}/cancelar` |
| `en_avaluo` | `avaluo_completado` | — | `PATCH /api/v1/avaluos/{avaluo_id}/resultado`<br>`POST /api/v1/solicitudes/{solicitud_id}/avaluo` |
| `en_avaluo` | `cancelada` | — | `POST /api/v1/solicitudes/{solicitud_id}/cancelar` |
| `avaluo_completado` | `en_analisis` | — | `POST /api/v1/solicitudes/{solicitud_id}/analisis` |
| `avaluo_completado` | `cancelada` | — | `POST /api/v1/solicitudes/{solicitud_id}/cancelar` |
| `en_analisis` | `aprobada` | — | `POST /api/v1/solicitudes/{solicitud_id}/analisis` |
| `en_analisis` | `condicionada` | — | `POST /api/v1/solicitudes/{solicitud_id}/analisis` |
| `en_analisis` | `rechazada` | — | `POST /api/v1/solicitudes/{solicitud_id}/analisis` |
| `aprobada` | `oferta_aceptada` | — | `POST /api/v1/solicitudes/{solicitud_id}/oferta/aceptar` |
| `aprobada` | `oferta_rechazada` | — | `POST /api/v1/solicitudes/{solicitud_id}/oferta/rechazar` |
| `aprobada` | `cancelada` | — | `POST /api/v1/solicitudes/{solicitud_id}/cancelar` |
| `condicionada` | `oferta_aceptada` | — | `POST /api/v1/solicitudes/{solicitud_id}/oferta/aceptar` |
| `condicionada` | `oferta_rechazada` | — | `POST /api/v1/solicitudes/{solicitud_id}/oferta/rechazar` |
| `condicionada` | `cancelada` | — | `POST /api/v1/solicitudes/{solicitud_id}/cancelar` |
| `oferta_aceptada` | `formalizada` | — | `POST /api/v1/solicitudes/{solicitud_id}/formalizar` |

Estados finales (sin salida): `rechazada`, `oferta_rechazada`, `formalizada`, `cancelada`.

Estados en los que se puede editar el expediente: `borrador`, `datos_completos`.

**Sobrescritura manual (no pasa por `TRANSICIONES`):** `PATCH /api/v1/solicitudes/{solicitud_id}/resolucion` puede llevar la solicitud entre `aprobada`, `condicionada`, `rechazada` en cualquier dirección, siempre que esté en uno de esos estados. También deja registro en el historial.

**Notas sobre el flujo:**

- `POST /solicitudes/{id}/avaluo` encadena `datos_completos → en_avaluo → avaluo_completado` en una sola llamada, porque el resultado del avalúo se genera automáticamente.
- `POST /solicitudes/{id}/analisis` encadena `→ en_analisis → aprobada|condicionada|rechazada` en una sola llamada.
- `PATCH /avaluos/{id}/resultado` solo cambia el estado si la solicitud sigue en `en_avaluo`. Eso ocurre con avalúos que no se completaron automáticamente, como la solicitud 3 del seed.
- Una transición inválida responde `400 TRANSICION_INVALIDA` con `details: [{estadoActual, estadoSolicitado, permitidos}]`.

## h) Reglas de negocio

Los valores se leen de `Settings`; las fórmulas, de los docstrings y del código.

### Solicitudes

- Máximo **3 solicitudes activas** por cliente, es decir, en un estado no final (cancelada, formalizada, oferta_rechazada, rechazada son finales). Al superarlo responde `400 LIMITE_SOLICITUDES`.
- El producto debe existir (404) y estar activo (`400 PRODUCTO_INACTIVO`). El monto debe estar en `[montoMin, montoMax]` y el plazo debe estar en `plazosMeses`.
- **Enganche (hipoteca):** `enganche = valorInmueble − montoSolicitado`. Debe cumplir `enganche ≥ valorInmueble × engancheMinPct / 100`; si no, responde `400 ENGANCHE_INSUFICIENTE`. Además, `montoSolicitado < valorInmueble` y `valorInmueble` es obligatorio. En préstamos `valorInmueble` se ignora.
- El expediente (solicitante, documentos, inmueble) solo se edita en `borrador` y `datos_completos`; en otro estado responde `400 SOLICITUD_NO_EDITABLE`.
- **Paso automático a `datos_completos`:** ocurre al tener los datos del solicitante, todos los documentos requeridos en estado `entregado` o `validado` y, si es hipoteca, el inmueble. Se revisa después de cada `PUT /solicitante`, `POST /documentos` y `PUT /inmueble`, y el `message` de esa respuesta lo indica.
- Si hay documentos `rechazado`, el avalúo y el análisis responden `400 DOCUMENTOS_RECHAZADOS`. Volver a entregar un documento rechazado lo reemplaza (mismo `id`).

### Datos del solicitante

- Edad ≥ 18 años hoy (`EDAD_INSUFICIENTE`). Edad al terminar el plazo < 70 (`EDAD_EXCEDE_PLAZO`). `ingresoMensual > 0`. Mínimo 2 referencias (máximo 5) con teléfonos distintos.
- Una antigüedad laboral menor a 6 meses se acepta al capturar, pero el análisis la rechaza.

### Análisis de crédito (`app/utils/analisis.py`)

| Regla (`regla`) | Valor (`valor`) | Límite (`limite`) | Si falla |
|---|---|---|---|
| `capacidad_pago` | mensualidad / (ingreso + otros − deudas) × 100 | ≤ 35% | condicionada (corregible) |
| `ltv` (solo hipoteca) | monto / valor comercial del avalúo × 100 | ≤ 90% | condicionada (corregible) |
| `buro` | puntaje ficticio 400–850 | ≥ 600 | rechazada |
| `antiguedad_laboral` | meses | ≥ 6 | rechazada |
| `edad_fin_plazo` | edad al terminar el plazo | ≤ 70 | rechazada |

- **Resolución:** si se cumplen todas, queda `aprobada` con el monto, la tasa y el plazo solicitados. Si falla buró, antigüedad o edad, queda `rechazada`. Si solo fallan capacidad de pago y/o LTV, se calcula el monto máximo que sí cumple: `min(solicitado, monto_maximo_por_pago(35% ingreso neto), 90% valor comercial)`, truncado a múltiplos de 100. Si ese monto es menor que `montoMin` del producto, queda `rechazada`; si no, queda `condicionada` con ese monto, su mensualidad y, en hipoteca, `engancheRequerido = valorInmueble − monto`.
- **Tasa aprobada:** la tasa del producto, con 1.00 punto(s) menos si el buró es ≥ 750. La capacidad de pago se calcula con la tasa ya descontada.
- **Buró:** Puntaje de buró FICTICIO entre 400 y 850, reproducible a partir del folio. Usa SHA-256 del folio, así que la misma solicitud siempre obtiene el mismo puntaje.
- `resultadoAnalisis` guarda `{resolucion, reglas:[{regla, descripcion, valor, limite, cumple}], puntajeBuro, ingresoNeto, pagoMaximo, mensualidadSolicitada, tasaAplicada, fechaAnalisis, montoMaximo?, sobrescritura?}`. Hay un ejemplo real en la sección d).

### Avalúo automático

- Solo aplica a hipotecas en `datos_completos`. Asigna un valuador activo al azar (`random.Random(id * 7919)`).
- `valorComercial = valorEstimadoCliente × factor`, con un factor entre 0.85 y 1.05 (4 decimales) generado con `random.Random(id_solicitud)`, por lo que se repite para la misma solicitud.
- Estado de conservación según la antigüedad del inmueble: 0–5 años → `excelente`; 6–15 años → `bueno`; 16–30 años → `regular`; ≥ 31 años → `malo`.
- Las observaciones se generan automáticamente y `generadoAutomaticamente` queda en `true`. El valuador asignado puede ajustar el resultado mientras la solicitud esté en `en_avaluo` o `avaluo_completado`; al hacerlo, `generadoAutomaticamente` pasa a `false`.

### Oferta, formalización y cálculos

- Vigencia de la oferta: 15 días desde `resueltaEn`. Fuera de plazo, `vigente: false` y aceptar responde `400 OFERTA_VENCIDA`.
- Formalizar un **préstamo** deposita el monto en la primera cuenta activa del cliente, con un movimiento «Disposición de préstamo …».
- Mensualidad: Cuota fija mensual (método francés). Si la tasa es 0 devuelve monto/plazo.
- Amortización: El último pago ajusta el redondeo para que el saldo final sea exactamente 0.00.
- CAT demo: CAT DEMOSTRATIVO (aproximación simple, NO es el cálculo oficial de Banxico). ``CAT ≈ ((1 + tasa_mensual)^12 - 1) * 100 + comision_apertura_pct * 12 / plazo`` Es decir, la tasa efectiva anual más la comisión de apertura prorrateada por año del plazo. Resultado en porcentaje con 2 decimales. Comisión de apertura usada: 1.00%.

### Bloque `progreso` (en `GET /solicitudes/{id}` y en las acciones que devuelven el detalle)

| Campo | Tipo | Significado |
|---|---|---|
| `porcentaje` | entero | 0–100. En borrador: (solicitante + documentos entregados + inmueble) / total × 40. En otros estados: valor fijo por estado (ver tabla siguiente) |
| `solicitanteCompleto` | booleano | ya se capturaron los datos del solicitante |
| `documentosRequeridos` | lista | tipos que exige el producto |
| `documentosEntregados` | lista | requeridos en estado entregado o validado |
| `documentosPendientes` | lista | requeridos que aún no se entregan |
| `documentosRechazados` | lista | requeridos en estado rechazado (hay que volver a entregarlos) |
| `inmuebleRequerido` | booleano | true en hipotecas |
| `inmuebleRegistrado` | booleano | ya existe el inmueble |
| `avaluoRequerido` | booleano | true en hipotecas |
| `avaluoEstado` | texto | null, `solicitado` o `completado` |
| `editable` | booleano | el estado permite editar el expediente |
| `siguientePaso` | texto | texto con la siguiente acción sugerida |

Porcentaje fijo por estado (`services/progreso._PORCENTAJE_ESTADO`): `datos_completos`=40, `en_avaluo`=50, `avaluo_completado`=60, `en_analisis`=70, `aprobada`=80, `condicionada`=80, `oferta_aceptada`=90, `formalizada`=100, `rechazada`=100, `oferta_rechazada`=100, `cancelada`=100.

Ejemplo real recién creada (hipoteca en `borrador`):

```json
{
  "porcentaje": 0,
  "solicitanteCompleto": false,
  "documentosRequeridos": [
    "identificacion",
    "comprobante_domicilio",
    "comprobante_ingresos",
    "estados_cuenta",
    "escrituras",
    "predial"
  ],
  "documentosEntregados": [],
  "documentosPendientes": [
    "identificacion",
    "comprobante_domicilio",
    "comprobante_ingresos",
    "estados_cuenta",
    "escrituras",
    "predial"
  ],
  "documentosRechazados": [],
  "inmuebleRequerido": true,
  "inmuebleRegistrado": false,
  "avaluoRequerido": true,
  "avaluoEstado": null,
  "editable": true,
  "siguientePaso": "Falta capturar datos del solicitante (PUT /solicitante); entregar documentos: identificacion, comprobante_domicilio, comprobante_ingresos, estados_cuenta, escrituras, predial; registrar el inmueble (PUT /inmueble)"
}
```

## i) Datos del seed

Comando: `python -m seeds.seed`. Es determinista (`Faker.seed(42)`, `random.seed(42)`), así que estos ids coinciden con `banco_demo.db` recién sembrada. Contraseña de **todos** los usuarios: `Demo1234!`.

Registros creados: usuarios: 20, cuentas: 22, movimientos: 966, productos_credito: 6, solicitudes: 10, solicitantes: 9, inmuebles: 4, avaluos: 4, documentos_solicitud: 40, historial_estados: 39.

### Usuarios

| id | Código | Correo | Rol | Activo |
|---|---|---|---|---|
| 1 | `USR-DEMO-000001` | `admin@demo-banco.test` | `admin` | sí |
| 2 | `USR-DEMO-000002` | `valuador1@demo-banco.test` | `valuador` | sí |
| 3 | `USR-DEMO-000003` | `valuador2@demo-banco.test` | `valuador` | sí |
| 4 | `USR-DEMO-000004` | `analista1@demo-banco.test` | `analista` | sí |
| 5 | `USR-DEMO-000005` | `analista2@demo-banco.test` | `analista` | sí |
| 6 | `USR-DEMO-000006` | `cliente1@demo-banco.test` | `cliente` | sí |
| 7 | `USR-DEMO-000007` | `cliente2@demo-banco.test` | `cliente` | sí |
| 8 | `USR-DEMO-000008` | `cliente3@demo-banco.test` | `cliente` | sí |
| 9 | `USR-DEMO-000009` | `cliente4@demo-banco.test` | `cliente` | sí |
| 10 | `USR-DEMO-000010` | `cliente5@demo-banco.test` | `cliente` | sí |
| 11 | `USR-DEMO-000011` | `cliente6@demo-banco.test` | `cliente` | sí |
| 12 | `USR-DEMO-000012` | `cliente7@demo-banco.test` | `cliente` | sí |
| 13 | `USR-DEMO-000013` | `cliente8@demo-banco.test` | `cliente` | sí |
| 14 | `USR-DEMO-000014` | `cliente9@demo-banco.test` | `cliente` | sí |
| 15 | `USR-DEMO-000015` | `cliente10@demo-banco.test` | `cliente` | sí |
| 16 | `USR-DEMO-000016` | `cliente11@demo-banco.test` | `cliente` | sí |
| 17 | `USR-DEMO-000017` | `cliente12@demo-banco.test` | `cliente` | sí |
| 18 | `USR-DEMO-000018` | `cliente13@demo-banco.test` | `cliente` | sí |
| 19 | `USR-DEMO-000019` | `cliente14@demo-banco.test` | `cliente` | sí |
| 20 | `USR-DEMO-000020` | `cliente15@demo-banco.test` | `cliente` | sí |

### Productos

| id | Nombre | Tipo | Tasa anual | Monto mín. | Monto máx. | Plazos (meses) | Enganche mín. | Documentos |
|---|---|---|---|---|---|---|---|---|
| 1 | Préstamo Personal Demo Básico | `prestamo` | 24% | 10,000.00 | 100,000.00 | 12, 24, 36 | — | identificacion, comprobante_domicilio, comprobante_ingresos, estados_cuenta |
| 2 | Préstamo Personal Demo Plus | `prestamo` | 18.5% | 50,000.00 | 300,000.00 | 12, 24, 36, 48 | — | identificacion, comprobante_domicilio, comprobante_ingresos, estados_cuenta |
| 3 | Préstamo Nómina Demo | `prestamo` | 15% | 20,000.00 | 200,000.00 | 12, 24, 36, 48, 60 | — | identificacion, comprobante_domicilio, comprobante_ingresos |
| 4 | Hipoteca Fija Demo | `hipoteca` | 10.5% | 500,000.00 | 5,000,000.00 | 120, 180, 240 | 10% | identificacion, comprobante_domicilio, comprobante_ingresos, estados_cuenta, escrituras, predial |
| 5 | Hipoteca Plus Demo | `hipoteca` | 9.8% | 1,000,000.00 | 10,000,000.00 | 180, 240 | 20% | identificacion, comprobante_domicilio, comprobante_ingresos, estados_cuenta, escrituras, predial |
| 6 | Hipoteca Joven Demo | `hipoteca` | 11.2% | 400,000.00 | 2,500,000.00 | 120, 180, 240 | 10% | identificacion, comprobante_domicilio, comprobante_ingresos, estados_cuenta, escrituras, predial |

### Solicitudes de ejemplo (10)

| id | Folio | Tipo | Producto | Monto | Plazo | Estado | Cliente |
|---|---|---|---|---|---|---|---|
| 1 | `SOL-DEMO-2026-000001` | `prestamo` | Préstamo Personal Demo Básico | 50,000.00 | 24 | `borrador` | `cliente1@demo-banco.test` |
| 2 | `SOL-DEMO-2026-000002` | `prestamo` | Préstamo Personal Demo Plus | 120,000.00 | 36 | `datos_completos` | `cliente2@demo-banco.test` |
| 3 | `SOL-DEMO-2026-000003` | `hipoteca` | Hipoteca Fija Demo | 1,800,000.00 | 240 | `en_avaluo` | `cliente3@demo-banco.test` |
| 4 | `SOL-DEMO-2026-000004` | `hipoteca` | Hipoteca Plus Demo | 3,200,000.00 | 240 | `avaluo_completado` | `cliente4@demo-banco.test` |
| 5 | `SOL-DEMO-2026-000005` | `prestamo` | Préstamo Nómina Demo | 90,000.00 | 36 | `aprobada` | `cliente5@demo-banco.test` |
| 6 | `SOL-DEMO-2026-000006` | `hipoteca` | Hipoteca Joven Demo | 1,300,000.00 | 240 | `condicionada` | `cliente6@demo-banco.test` |
| 7 | `SOL-DEMO-2026-000007` | `prestamo` | Préstamo Personal Demo Básico | 60,000.00 | 24 | `rechazada` | `cliente7@demo-banco.test` |
| 8 | `SOL-DEMO-2026-000008` | `hipoteca` | Hipoteca Fija Demo | 1,400,000.00 | 240 | `oferta_aceptada` | `cliente8@demo-banco.test` |
| 9 | `SOL-DEMO-2026-000009` | `prestamo` | Préstamo Personal Demo Plus | 150,000.00 | 48 | `formalizada` | `cliente9@demo-banco.test` |
| 10 | `SOL-DEMO-2026-000010` | `prestamo` | Préstamo Nómina Demo | 40,000.00 | 24 | `cancelada` | `cliente10@demo-banco.test` |

Clientes sin solicitudes (útiles para probar el flujo desde cero): `cliente11@demo-banco.test`, `cliente12@demo-banco.test`, `cliente13@demo-banco.test`, `cliente14@demo-banco.test`, `cliente15@demo-banco.test`.

> El folio incluye el año de creación (`SOL-DEMO-<año>-<id>`), así que cambia si el seed se ejecuta otro año.

## j) Diferencias con el prompt original

> El archivo `PROMPT_API_BANCO.md` **no existe en el proyecto**. La comparación se hizo contra el texto del prompt «API REST COMPLETA DE BANCO SIMULADO» con el que se construyó la API. Las secciones de endpoints, campos de modelos y archivos se compararon automáticamente; el resto viene de revisar el código.

### Endpoints

- El prompt pide **47** endpoints y la API tiene **47**.
- Faltantes: ninguno.
- Extra: ninguno.
- Rutas renombradas: ninguna. Las rutas coinciden; solo cambian los nombres de los parámetros de ruta, que en el código son descriptivos (`{solicitud_id}`, `{documento_id}`, `{avaluo_id}`, `{cuenta_id}`, `{producto_id}`, `{usuario_id}`) en lugar de `{id}`/`{doc_id}`. Esto no afecta a la URL que llama el frontend.
- `/health` también lleva el prefijo: `GET /api/v1/health`.

### Campos de los modelos (BD)

| Tabla | Campos extra respecto al prompt | Campos del prompt que faltan |
|---|---|---|
| `usuarios` | — | — |
| `cuentas` | — | — |
| `movimientos` | — | — |
| `productos_credito` | — | — |
| `solicitudes` | `enganche_requerido`, `resuelta_en` | — |
| `solicitantes` | `id` (clave técnica de la relación 1:1), `solicitud_id` (clave técnica de la relación 1:1) | — |
| `inmuebles` | `id` (clave técnica de la relación 1:1), `solicitud_id` (clave técnica de la relación 1:1) | — |
| `avaluos` | `id` (clave técnica de la relación 1:1), `inmueble_id` (clave técnica de la relación 1:1) | — |
| `documentos_solicitud` | — | — |
| `historial_estados` | — | — |

### Archivos

- `app/core/`: extra ninguno; faltantes ninguno.
- `app/dependencies/`: extra ninguno; faltantes ninguno.
- `app/models/`: extra ninguno; faltantes ninguno.
- `app/routers/`: extra ninguno; faltantes ninguno.
- `app/utils/`: extra `fechas.py`; faltantes ninguno.
- `tests/`: extra `helpers.py`; faltantes ninguno.
- `app/services/` (el prompt pide uno por módulo): `admin.py`, `auth.py`, `comun.py`, `cuentas.py`, `evaluacion.py`, `expediente.py`, `productos.py`, `progreso.py`, `simuladores.py`, `solicitudes.py`, `usuarios.py`. `comun.py` y `progreso.py` son auxiliares compartidos.
- Raíz: extra `pytest.ini`. `app/schemas/admin.py` contiene el esquema de estadísticas.

### Comportamiento distinto o añadido (revisado en el código)

| Tema | Diferencia |
|---|---|
| Mensualidad de referencia | El prompt pone como ejemplo 50,000 a 18.5% en 24 meses ≈ 2,520.37. El método francés implementado (`utils/finanzas.calcular_mensualidad`) da **2,508.30**, y las pruebas usan ese valor. |
| Antigüedad laboral < 6 meses | El prompt dice que se acepta pero «el análisis lo penaliza». En el código (`utils/analisis.evaluar`) lleva a **`rechazada`**, porque la condicionada solo aplica a capacidad de pago y LTV. |
| Regla de edad | Al capturar datos se exige edad final **< 70** (`EDAD_EXCEDE_PLAZO`), como pide el prompt; el análisis acepta **≤ 70**. En la práctica el análisis solo falla si el tiempo pasa entre la captura y el análisis. |
| Monto condicionado | Se trunca a múltiplos de 100 (`ANALISIS_REDONDEO_MONTO_CONDICIONADO`). El prompt no lo especificaba. |
| Códigos 403 | Se distinguen `PERMISO_INSUFICIENTE` (el rol no puede usar el endpoint) y `ACCESO_DENEGADO` (el recurso es de otro usuario). El prompt solo mencionaba `ACCESO_DENEGADO`. |
| Campos extra en Solicitud | `resuelta_en` (base de la vigencia de 15 días) y `enganche_requerido` (enganche necesario en ofertas condicionadas). |
| Formalizar préstamo | Deposita el monto en la cuenta demo del cliente y registra un movimiento. No estaba en el prompt. |
| Respuesta de login | `data = {accessToken, tokenType: "bearer", expiresIn, usuario}`. El prompt solo pedía token y usuario. |
| Respuesta de registro | `data = {usuario, cuenta}`: incluye la cuenta de débito creada, con el número enmascarado. |
| Paginación | `meta` lleva solo `page`, `limit` y `total` (no incluye el total de páginas). |
| `GET /productos` | Sin el filtro `activo` devuelve **solo los activos**; `?activo=false` muestra los inactivos. |
| Simuladores | Aceptan `tasaAnual` **o** `productoId`. Con `productoId` se validan el tipo, el monto y el plazo del producto. La hipoteca usa 10% de enganche mínimo por defecto o el valor de `engancheMinPct` del cuerpo. |
| `cancelar` y `oferta/rechazar` | Aceptan un cuerpo opcional `{motivo}`, que se guarda como nota en el historial. |
| Acceso del valuador | El valuador asignado también puede ver la solicitud, el solicitante, los documentos, el inmueble y el historial. El cliente dueño puede ver `GET /avaluos/{id}`. |
| Cuentas con admin | `GET /cuentas` con el rol admin devuelve todas las cuentas; analistas y valuadores reciben 403. |
| Documentos rechazados | Bloquean el avalúo y el análisis (`DOCUMENTOS_RECHAZADOS`). La solicitud no vuelve a `borrador`; el cliente los reentrega estando en `datos_completos`. |
| Revisión de documentos | Se permite en cualquier estado que no sea final (`SOLICITUD_FINALIZADA` en estados finales). |
| Correos | Se valida el formato sin consultar DNS y se admiten dominios `.test` (`email-validator` los rechazaba). |
| Nombres de archivo simulados | Deben terminar en `.pdf`, `.jpg`, `.jpeg` o `.png`. |
| Errores adicionales | Hay códigos que el prompt no listaba, como `SIN_CAMBIOS`, `PASSWORD_REPETIDA`, `OPERACION_NO_PERMITIDA`, `MONTO_EXCEDE_VALOR`, `VALOR_INMUEBLE_REQUERIDO`, `RED_NO_PERMITIDA` y `OFERTA_VENCIDA`. El catálogo completo está en la sección e). |
| Estado civil | El prompt no definía los valores; el código usa `soltero`, `casado`, `divorciado`, `viudo` y `union_libre`. |
| Cabeceras | Todas las respuestas llevan `X-Demo: true`, `X-Content-Type-Options`, `X-Frame-Options` y `Referrer-Policy`. |
| Versiones | Python 3.14, FastAPI 0.163.1, SQLAlchemy 2.0.57 y Pydantic 2.14.3 (ver `requirements.txt`). |

