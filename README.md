# API Banco Demo — Hipotecas y préstamos personales

> **Proyecto académico.** Todos los datos son ficticios. No hay conexión con bancos reales
> ni se realizan operaciones financieras auténticas. Los números de cuenta, folios y CURP
> llevan el prefijo `DEMO`.

API REST construida con **FastAPI + SQLAlchemy 2.0 + SQLite** que simula el ciclo completo
de una solicitud de crédito: alta, expediente, documentos simulados, inmueble, avalúo,
análisis de crédito automático, oferta, aceptación y formalización.

## Requisitos

- Python 3.11 o superior (probado con 3.14)
- pip
- (Opcional) Postman para la colección de `docs/postman/`

## Instalación

### Windows (PowerShell)

```powershell
cd api-banco-demo
python -m venv venv
.\venv\Scripts\Activate.ps1          # en cmd: venv\Scripts\activate.bat
pip install -r requirements.txt
Copy-Item .env.example .env
```

### Linux / macOS

```bash
cd api-banco-demo
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Configuración (`.env`)

| Variable | Descripción | Valor por defecto |
|---|---|---|
| `DATABASE_URL` | URL de SQLAlchemy. Para PostgreSQL: `postgresql+psycopg://user:pass@host/db` | `sqlite:///./banco_demo.db` |
| `JWT_SECRET` | Secreto para firmar los JWT | aleatorio por proceso |
| `JWT_EXPIRE_MINUTES` | Vigencia del token | `60` |
| `CORS_ORIGINS` | Orígenes permitidos, separados por coma | `http://localhost:3000,...` |
| `ALLOWED_NETWORKS` | Redes CIDR permitidas (vacío = todas) | vacío |
| `DOCS_ENABLED` | Habilita `/docs`, `/redoc` y `/openapi.json` | `true` |
| `RATE_LIMIT_LOGIN` | Límite de `/auth/login` | `5/minute` |
| `RATE_LIMIT_DEFAULT` | Límite general | `100/minute` |

Si no existe `.env`, la API arranca con valores de desarrollo y muestra un aviso en consola.
Con un `JWT_SECRET` aleatorio los tokens dejan de valer al reiniciar el servidor.

## Cargar datos demo

```bash
python -m seeds.seed
```

Borra y recrea la base con datos reproducibles (`Faker.seed(42)`): 20 usuarios, 22 cuentas
con ~1,000 movimientos, 6 productos y 10 solicitudes, una en cada estado del ciclo.

## Ejecutar

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Swagger UI: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>
- Salud: <http://localhost:8000/api/v1/health>

## Pruebas

```bash
python -m pytest
```

263 pruebas: unitarias (finanzas, estados, análisis) y de integración por endpoint (éxito,
sin auth/permiso, validación, inexistente) más flujos completos. Usan una BD temporal; no
tocan `banco_demo.db`.

## Usuarios demo

Contraseña de todos: **`Demo1234!`**

| Correo | Rol |
|---|---|
| `admin@demo-banco.test` | admin |
| `valuador1@demo-banco.test`, `valuador2@demo-banco.test` | valuador |
| `analista1@demo-banco.test`, `analista2@demo-banco.test` | analista |
| `cliente1@demo-banco.test` … `cliente15@demo-banco.test` | cliente |

`cliente11` a `cliente15` no tienen solicitudes: úsalos para probar el flujo desde cero.

## Recorrido rápido: flujo de hipoteca

Base: `http://localhost:8000/api/v1`. Desde el paso 2, todas las peticiones llevan `Authorization: Bearer <token>`.

1. **Login** — `POST /auth/login` `{"email":"cliente11@demo-banco.test","password":"Demo1234!"}` → `data.accessToken`
2. **Simular (opcional)** — `POST /simuladores/hipoteca` `{"valorInmueble":2500000,"enganche":700000,"productoId":4,"plazoMeses":240}`
3. **Crear solicitud** — `POST /solicitudes` `{"productoId":4,"montoSolicitado":1800000,"plazoMeses":240,"valorInmueble":2500000}` → estado `borrador`
4. **Datos del solicitante** — `PUT /solicitudes/{id}/solicitante` (ver ejemplo en Swagger)
5. **Documentos** — `POST /solicitudes/{id}/documentos` para cada tipo: `identificacion`, `comprobante_domicilio`, `comprobante_ingresos`, `estados_cuenta`, `escrituras`, `predial`
6. **Inmueble** — `PUT /solicitudes/{id}/inmueble` → la solicitud avanza sola a `datos_completos`
7. **Avalúo** — `POST /solicitudes/{id}/avaluo` → `avaluo_completado` (resultado automático)
8. **Análisis** — `POST /solicitudes/{id}/analisis` → `aprobada`, `condicionada` o `rechazada`
9. **Oferta** — `GET /solicitudes/{id}/oferta`
10. **Aceptar** — `POST /solicitudes/{id}/oferta/aceptar` → `oferta_aceptada`
11. **Formalizar** — `POST /solicitudes/{id}/formalizar` → `formalizada`
12. **Amortización** — `GET /solicitudes/{id}/amortizacion`

En cualquier momento, `GET /solicitudes/{id}` devuelve `progreso.siguientePaso` con lo que falta para avanzar.

## Documentación adicional

- [`docs/CONTRATO_API.md`](docs/CONTRATO_API.md): contrato de cada endpoint y catálogo de errores
- [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md): capas, decisiones técnicas, diagramas
- [`docs/postman/banco-demo.postman_collection.json`](docs/postman/banco-demo.postman_collection.json): colección Postman
