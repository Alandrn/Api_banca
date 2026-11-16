# CLAUDE.md — API Banco Demo

API REST académica que simula un banco para **solicitudes de hipotecas y préstamos personales**.
Todos los datos son ficticios. Solo backend (FastAPI), sin frontend.

## Cómo ejecutar

```bash
python -m venv venv
venv\Scripts\activate            # Windows  (Linux/macOS: source venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env           # Linux: cp .env.example .env  (opcional; sin .env usa valores de desarrollo)
python -m seeds.seed             # borra y recrea banco_demo.db con datos demo
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
python -m pytest                 # 263 pruebas, BD temporal (no toca banco_demo.db)
```

Swagger: http://localhost:8000/docs · ReDoc: /redoc · Prefijo de rutas: `/api/v1`.
Usuarios demo: `admin@`, `valuador1@`, `analista1@`, `cliente1@`…`cliente15@demo-banco.test`, contraseña `Demo1234!`.

## Arquitectura (capas)

```
routers/ → dependencies/ → schemas/ → services/ → models/ → SQLite (SQLAlchemy 2.0)
                      utils/ (lógica pura: finanzas, estados, análisis, identificadores, fechas)
                      core/  (config, database, security, exceptions, responses, middlewares)
```

- **Router**: solo HTTP (dependencias de auth, validación con schemas, sobre de respuesta `ok()`/`paginado()`). Sin lógica de negocio.
- **Service**: reglas de negocio; no conoce HTTP; lanza `ApiError(status, CODE, mensaje, details)`. Hace `commit`.
- **utils/**: funciones puras y testeables sin BD (`finanzas.py`, `analisis.py`, `estados.py`).
- `services/comun.py`: `solicitud_con_acceso`, `solicitud_propia`, `cambiar_estado` (valida transición + registra `HistorialEstado`).
- `services/progreso.py`: progreso del expediente y avance automático `borrador → datos_completos`.

## Convenciones

- Dinero: `Decimal` / `Numeric(12,2)`, redondeo `ROUND_HALF_UP` (`utils.finanzas.redondear`). En JSON se serializa como número.
- Schemas heredan de `SchemaBase` (alias camelCase, `populate_by_name=True`): salida camelCase, entrada camel o snake.
- Respuesta éxito `{ok, message, data, meta?, demo}`; error `{ok:false, error:{code, message, details}, demo}`. Los handlers centrales están en `core/exceptions.py` (ApiError, 422 traducido al español, 404/405, 429, 500 sin traza).
- Códigos de error en `MAYUSCULAS_CON_GUION_BAJO`. Rutas en español, plural, minúsculas.
- Fechas UTC sin zona (`utils.fechas.ahora()`), ISO 8601.
- Docstrings y comentarios en español.
- Toda transición de estado pasa por `services.comun.cambiar_estado` (nunca asignar `solicitud.estado` directo).
- Umbrales del análisis y reglas en `core/config.py` (configurables por entorno).
- Roles: `require_roles(...)`; admin siempre pasa. Pertenencia → 403 `ACCESO_DENEGADO`; rol → 403 `PERMISO_INSUFICIENTE`.

## Pruebas

- `tests/conftest.py` fija variables de entorno ANTES de importar la app (BD temporal, `BCRYPT_ROUNDS=4`), recrea la BD por prueba y reinicia el rate limit.
- El buró ficticio se fija en 700 por defecto (fixture autouse); usar `fijar_buro(valor)` para otros casos.
- `tests/helpers.py`: escenarios (`prestamo_listo`, `hipoteca_lista`, `hipoteca_avaluada`) y asserts de sobre (`ok_data`, `error_code`).
- Tokens por rol: fixtures `h_admin`, `h_analista`, `h_valuador`, `h_valuador2`, `h_cliente`, `h_cliente2`.

## Documentación

- `docs/CONTRATO_API.md`: contrato completo por endpoint y catálogo de errores.
- `docs/ARQUITECTURA.md`: decisiones, diagrama ER y de estados, reglas de análisis.
- `docs/postman/banco-demo.postman_collection.json`: colección con flujo de hipoteca.
