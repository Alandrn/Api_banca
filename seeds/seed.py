"""Carga de datos ficticios reproducibles para el banco demo.

Ejecutar desde la raíz del proyecto::

    python -m seeds.seed

Borra y recrea la base de datos indicada en DATABASE_URL.
"""

from __future__ import annotations

import random
import string
import sys
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from faker import Faker

import app.models  # noqa: F401  (registra modelos)
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models.avaluo import Avaluo
from app.models.cuenta import Cuenta
from app.models.movimiento import Movimiento
from app.models.producto import ProductoCredito
from app.models.usuario import Usuario
from app.services import evaluacion as evaluacion_service
from app.services import expediente as expediente_service
from app.services import solicitudes as solicitudes_service
from app.services.comun import cambiar_estado
from app.services.usuarios import crear_usuario, numero_cuenta_unico
from app.utils import estados as E
from app.utils.fechas import ahora
from app.utils.finanzas import redondear
from app.utils.identificadores import folio_avaluo, referencia_movimiento

PASSWORD_DEMO = "Demo1234!"

DOCS_PRESTAMO = ["identificacion", "comprobante_domicilio", "comprobante_ingresos", "estados_cuenta"]
DOCS_HIPOTECA = DOCS_PRESTAMO + ["escrituras", "predial"]

PRODUCTOS: list[dict[str, Any]] = [
    {
        "nombre": "Préstamo Personal Demo Básico",
        "tipo": "prestamo",
        "descripcion": "Préstamo personal demostrativo para gastos personales, con tasa fija.",
        "tasa_anual": Decimal("24.00"),
        "monto_min": Decimal("10000.00"),
        "monto_max": Decimal("100000.00"),
        "plazos_meses": [12, 24, 36],
        "enganche_min_pct": None,
        "documentos_requeridos": DOCS_PRESTAMO,
        "requisitos": [
            "Ser mayor de 18 años",
            "Antigüedad laboral mínima de 6 meses",
            "Ingreso mensual comprobable",
            "Dos referencias personales",
        ],
        "condiciones": "Tasa fija anual de 24%. Producto demostrativo sin validez comercial.",
    },
    {
        "nombre": "Préstamo Personal Demo Plus",
        "tipo": "prestamo",
        "descripcion": "Préstamo personal demostrativo de mayor monto y plazo.",
        "tasa_anual": Decimal("18.50"),
        "monto_min": Decimal("50000.00"),
        "monto_max": Decimal("300000.00"),
        "plazos_meses": [12, 24, 36, 48],
        "enganche_min_pct": None,
        "documentos_requeridos": DOCS_PRESTAMO,
        "requisitos": [
            "Ser mayor de 18 años",
            "Antigüedad laboral mínima de 6 meses",
            "Buen historial crediticio (buró ficticio ≥ 600)",
            "Dos referencias personales",
        ],
        "condiciones": "Tasa fija anual de 18.5%. Descuento de 1 punto con buró ≥ 750. Producto demostrativo.",
    },
    {
        "nombre": "Préstamo Nómina Demo",
        "tipo": "prestamo",
        "descripcion": "Préstamo demostrativo para clientes con nómina en el banco demo.",
        "tasa_anual": Decimal("15.00"),
        "monto_min": Decimal("20000.00"),
        "monto_max": Decimal("200000.00"),
        "plazos_meses": [12, 24, 36, 48, 60],
        "enganche_min_pct": None,
        "documentos_requeridos": ["identificacion", "comprobante_domicilio", "comprobante_ingresos"],
        "requisitos": [
            "Recibir nómina en una cuenta demo",
            "Antigüedad laboral mínima de 6 meses",
            "Dos referencias personales",
        ],
        "condiciones": "Tasa fija anual de 15%. Descuento vía nómina (simulado). Producto demostrativo.",
    },
    {
        "nombre": "Hipoteca Fija Demo",
        "tipo": "hipoteca",
        "descripcion": "Crédito hipotecario demostrativo a tasa fija para compra de vivienda.",
        "tasa_anual": Decimal("10.50"),
        "monto_min": Decimal("500000.00"),
        "monto_max": Decimal("5000000.00"),
        "plazos_meses": [120, 180, 240],
        "enganche_min_pct": Decimal("10.00"),
        "documentos_requeridos": DOCS_HIPOTECA,
        "requisitos": [
            "Ser mayor de 18 años y menor de 70 al terminar el plazo",
            "Enganche mínimo del 10% del valor del inmueble",
            "Avalúo del inmueble",
            "Financiamiento máximo del 90% del valor comercial",
        ],
        "condiciones": "Tasa fija anual de 10.5% durante todo el plazo. Producto demostrativo.",
    },
    {
        "nombre": "Hipoteca Plus Demo",
        "tipo": "hipoteca",
        "descripcion": "Crédito hipotecario demostrativo para inmuebles de mayor valor.",
        "tasa_anual": Decimal("9.80"),
        "monto_min": Decimal("1000000.00"),
        "monto_max": Decimal("10000000.00"),
        "plazos_meses": [180, 240],
        "enganche_min_pct": Decimal("20.00"),
        "documentos_requeridos": DOCS_HIPOTECA,
        "requisitos": [
            "Enganche mínimo del 20% del valor del inmueble",
            "Avalúo del inmueble",
            "Ingreso comprobable suficiente (relación pago/ingreso ≤ 35%)",
        ],
        "condiciones": "Tasa fija anual de 9.8%. Producto demostrativo.",
    },
    {
        "nombre": "Hipoteca Joven Demo",
        "tipo": "hipoteca",
        "descripcion": "Crédito hipotecario demostrativo para primera vivienda.",
        "tasa_anual": Decimal("11.20"),
        "monto_min": Decimal("400000.00"),
        "monto_max": Decimal("2500000.00"),
        "plazos_meses": [120, 180, 240],
        "enganche_min_pct": Decimal("10.00"),
        "documentos_requeridos": DOCS_HIPOTECA,
        "requisitos": [
            "Primera vivienda",
            "Enganche mínimo del 10% del valor del inmueble",
            "Avalúo del inmueble",
        ],
        "condiciones": "Tasa fija anual de 11.2%. Producto demostrativo.",
    },
]


# ---------------------------------------------------------------------------
# Generadores
# ---------------------------------------------------------------------------

def curp_ficticia(fecha_nac: date, rng: random.Random) -> str:
    """CURP FICTICIA de 18 caracteres: DEMO + AAMMDD + H + 7 alfanuméricos."""
    resto = "".join(rng.choice(string.ascii_uppercase + string.digits) for _ in range(7))
    return f"DEMO{fecha_nac:%y%m%d}H{resto}"


def telefono(rng: random.Random) -> str:
    """Teléfono ficticio de 10 dígitos que empieza con 55."""
    return "55" + "".join(str(rng.randint(0, 9)) for _ in range(8))


def generar_movimientos(db, cuenta: Cuenta, rng: random.Random, fake: Faker) -> int:
    """Genera 30–60 movimientos en los últimos 6 meses con saldos coherentes."""
    total = rng.randint(30, 60)
    fin = ahora()
    inicio = fin - timedelta(days=180)
    saldo = redondear(Decimal(rng.randint(3000, 25000)))
    db.add(
        Movimiento(
            cuenta_id=cuenta.id, tipo="deposito", concepto="Depósito de apertura (demo)", monto=saldo,
            saldo_resultante=saldo, referencia=referencia_movimiento(inicio, rng), fecha=inicio,
        )
    )
    fechas = sorted(inicio + timedelta(seconds=rng.randint(3600, 180 * 86400 - 3600)) for _ in range(total - 1))
    comercios = ["Supermercado Demo", "Farmacia Demo", "Gasolinera Demo", "Cafetería Demo", "Tienda en línea Demo",
                 "Restaurante Demo", "Librería Demo"]
    servicios = ["Luz (CFE Demo)", "Agua Demo", "Internet Demo", "Telefonía Demo", "Tarjeta de crédito Demo"]
    for fecha in fechas:
        tipo = rng.choices(["deposito", "retiro", "pago", "compra", "transferencia"], weights=[22, 13, 18, 35, 12])[0]
        if tipo == "deposito":
            monto = Decimal(rng.randint(3000, 18000))
            concepto = rng.choice(["Depósito de nómina (demo)", "Depósito en ventanilla (demo)",
                                   f"Transferencia recibida de {fake.first_name()} (demo)"])
        elif tipo == "retiro":
            monto = Decimal(rng.choice([300, 500, 1000, 1500, 2000]))
            concepto = "Retiro en cajero Demo"
        elif tipo == "pago":
            monto = Decimal(rng.randint(250, 2500))
            concepto = f"Pago de servicio {rng.choice(servicios)}"
        elif tipo == "compra":
            monto = Decimal(rng.randint(5000, 250000)) / 100
            concepto = f"Compra en {rng.choice(comercios)}"
        else:
            monto = Decimal(rng.randint(500, 6000))
            concepto = f"Transferencia enviada a {fake.first_name()} (demo)"
        monto = redondear(monto)
        if tipo != "deposito":
            if monto > saldo:
                tipo, concepto = "deposito", "Depósito de nómina (demo)"
                monto = redondear(Decimal(rng.randint(5000, 15000)))
            else:
                monto = -monto
        saldo = redondear(saldo + monto)
        db.add(
            Movimiento(
                cuenta_id=cuenta.id, tipo=tipo, concepto=concepto, monto=monto, saldo_resultante=saldo,
                referencia=referencia_movimiento(fecha, rng), fecha=fecha,
            )
        )
    cuenta.saldo = saldo
    return total


def datos_solicitante(fake: Faker, rng: random.Random, ingreso: int, antiguedad: int = 36,
                      deudas: int = 0, edad: int = 35) -> dict[str, Any]:
    """Datos completos y válidos de un solicitante ficticio."""
    nacimiento = date.today().replace(day=1) - timedelta(days=int(edad * 365.25))
    return {
        "fecha_nacimiento": nacimiento,
        "curp_ficticia": curp_ficticia(nacimiento, rng),
        "estado_civil": rng.choice(["soltero", "casado", "union_libre"]),
        "dependientes": rng.randint(0, 3),
        "domicilio": fake.street_address()[:200],
        "ciudad": fake.city()[:80],
        "empresa": f"{fake.company()[:100]} (Demo)",
        "puesto": fake.job()[:80],
        "tipo_empleo": "asalariado",
        "antiguedad_meses": antiguedad,
        "ingreso_mensual": Decimal(ingreso),
        "otros_ingresos": Decimal("0"),
        "gastos_mensuales": Decimal(int(ingreso * 0.3)),
        "deudas_mensuales": Decimal(deudas),
        "referencias": [
            {"nombre": f"{fake.first_name()} {fake.last_name()}", "telefono": telefono(rng), "relacion": "familiar"},
            {"nombre": f"{fake.first_name()} {fake.last_name()}", "telefono": telefono(rng), "relacion": "amistad"},
        ],
    }


def datos_inmueble(fake: Faker, rng: random.Random, valor: Decimal, antiguedad: int) -> dict[str, Any]:
    """Datos de un inmueble ficticio."""
    return {
        "tipo": rng.choice(["casa", "departamento"]),
        "direccion": fake.street_address()[:200],
        "colonia": f"Col. {fake.last_name()}",
        "ciudad": fake.city()[:80],
        "estado": fake.state()[:60],
        "cp": f"{rng.randint(1000, 99999):05d}",
        "m2_terreno": Decimal(rng.randint(90, 300)),
        "m2_construccion": Decimal(rng.randint(60, 250)),
        "antiguedad_anios": antiguedad,
        "recamaras": rng.randint(1, 4),
        "banos": rng.randint(1, 3),
        "valor_estimado_cliente": valor,
    }


def entregar_documentos(db, solicitud_id: int, cliente: Usuario, tipos: list[str]) -> None:
    """Entrega simulada de documentos."""
    for tipo in tipos:
        expediente_service.entregar_documento(db, solicitud_id, cliente, tipo, f"{tipo}_demo.pdf")


# ---------------------------------------------------------------------------
# Seed principal
# ---------------------------------------------------------------------------

def crear_productos(db) -> list[ProductoCredito]:
    """Inserta los 6 productos demo."""
    productos = [ProductoCredito(**p, activo=True) for p in PRODUCTOS]
    db.add_all(productos)
    db.commit()
    return productos


def ejecutar() -> dict[str, Any]:
    """Borra y recrea la BD con datos ficticios reproducibles."""
    Faker.seed(42)
    random.seed(42)
    fake = Faker("es_MX")
    rng = random.Random(42)

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    password_hash = hash_password(PASSWORD_DEMO)
    resumen: dict[str, Any] = {"usuarios": 0, "cuentas": 0, "movimientos": 0, "productos": 0, "solicitudes": []}

    try:
        # --- Usuarios ---
        def nuevo(email: str, rol: str) -> Usuario:
            return crear_usuario(
                db, nombre=fake.first_name(), apellidos=f"{fake.last_name()} {fake.last_name()}", email=email,
                telefono=telefono(rng), rol=rol, password_hash=password_hash,
            )

        nuevo("admin@demo-banco.test", "admin")
        valuadores = [nuevo(f"valuador{i}@demo-banco.test", "valuador") for i in (1, 2)]
        analistas = [nuevo(f"analista{i}@demo-banco.test", "analista") for i in (1, 2)]
        clientes = [nuevo(f"cliente{i}@demo-banco.test", "cliente") for i in range(1, 16)]
        db.commit()
        resumen["usuarios"] = 5 + len(clientes)

        # --- Cuentas y movimientos ---
        for cliente in clientes:
            tipos = ["debito"] if rng.random() < 0.5 else ["debito", "ahorro"]
            for tipo in tipos:
                cuenta = Cuenta(
                    usuario_id=cliente.id, numero=numero_cuenta_unico(db, rng), tipo=tipo, saldo=Decimal("0"),
                    moneda="MXN", estado="activa", creada_en=ahora() - timedelta(days=181),
                )
                db.add(cuenta)
                db.flush()
                resumen["movimientos"] += generar_movimientos(db, cuenta, rng, fake)
                resumen["cuentas"] += 1
        db.commit()

        # --- Productos ---
        productos = crear_productos(db)
        resumen["productos"] = len(productos)
        p_basico, p_plus, p_nomina, h_fija, h_plus, h_joven = productos
        analista = analistas[0]

        def solicitud(cliente: Usuario, producto: ProductoCredito, monto: int, plazo: int, valor: int | None = None):
            datos = {"producto_id": producto.id, "monto_solicitado": Decimal(monto), "plazo_meses": plazo,
                     "valor_inmueble": Decimal(valor) if valor else None}
            return solicitudes_service.crear(db, cliente, datos)

        def expediente(s, cliente: Usuario, ingreso: int, **kw):
            expediente_service.guardar_solicitante(db, s.id, cliente, datos_solicitante(fake, rng, ingreso, **kw))
            entregar_documentos(db, s.id, cliente, s.producto.documentos_requeridos)

        def hipoteca_lista(cliente, producto, monto, plazo, valor, ingreso, antiguedad_inmueble=8):
            s = solicitud(cliente, producto, monto, plazo, valor)
            expediente(s, cliente, ingreso)
            evaluacion_service.guardar_inmueble(
                db, s.id, cliente, datos_inmueble(fake, rng, Decimal(valor), antiguedad_inmueble)
            )
            return s

        # 1. borrador: solo datos del solicitante y un documento
        s1 = solicitud(clientes[0], p_basico, 50000, 24)
        expediente_service.guardar_solicitante(db, s1.id, clientes[0], datos_solicitante(fake, rng, 28000))
        entregar_documentos(db, s1.id, clientes[0], ["identificacion"])

        # 2. datos_completos (préstamo)
        s2 = solicitud(clientes[1], p_plus, 120000, 36)
        expediente(s2, clientes[1], 45000)

        # 3. en_avaluo (hipoteca con avalúo solicitado, aún sin resultado)
        s3 = hipoteca_lista(clientes[2], h_fija, 1800000, 240, 2400000, 85000)
        db.refresh(s3)
        avaluo = Avaluo(
            inmueble_id=s3.inmueble.id, valuador_id=valuadores[0].id, estado="solicitado",
            fecha_solicitud=ahora(), generado_automaticamente=False,
        )
        db.add(avaluo)
        db.flush()
        avaluo.folio = folio_avaluo(avaluo.id, ahora().year)
        cambiar_estado(db, s3, E.EN_AVALUO, clientes[2].id, f"Avalúo {avaluo.folio} asignado; visita pendiente")
        db.commit()

        # 4. avaluo_completado
        s4 = hipoteca_lista(clientes[3], h_plus, 3200000, 240, 4500000, 160000, 3)
        evaluacion_service.solicitar_avaluo(db, s4.id, clientes[3])

        # 5. aprobada (préstamo nómina, buró bueno)
        s5 = solicitud(clientes[4], p_nomina, 90000, 36)
        expediente(s5, clientes[4], 40000)
        evaluacion_service.ejecutar_analisis(db, s5.id, analista, puntaje_buro=720)

        # 6. condicionada (hipoteca joven, capacidad de pago insuficiente)
        s6 = hipoteca_lista(clientes[5], h_joven, 1300000, 240, 1500000, 30000, 12)
        evaluacion_service.solicitar_avaluo(db, s6.id, clientes[5])
        evaluacion_service.ejecutar_analisis(db, s6.id, analista, puntaje_buro=680)

        # 7. rechazada (buró bajo)
        s7 = solicitud(clientes[6], p_basico, 60000, 24)
        expediente(s7, clientes[6], 35000)
        evaluacion_service.ejecutar_analisis(db, s7.id, analista, puntaje_buro=540)

        # 8. oferta_aceptada (hipoteca fija aprobada)
        s8 = hipoteca_lista(clientes[7], h_fija, 1400000, 240, 2000000, 95000, 4)
        evaluacion_service.solicitar_avaluo(db, s8.id, clientes[7])
        evaluacion_service.ejecutar_analisis(db, s8.id, analista, puntaje_buro=780)
        solicitudes_service.aceptar_oferta(db, s8.id, clientes[7])

        # 9. formalizada (préstamo plus)
        s9 = solicitud(clientes[8], p_plus, 150000, 48)
        expediente(s9, clientes[8], 60000)
        evaluacion_service.ejecutar_analisis(db, s9.id, analista, puntaje_buro=760)
        solicitudes_service.aceptar_oferta(db, s9.id, clientes[8])
        solicitudes_service.formalizar(db, s9.id, clientes[8])

        # 10. cancelada
        s10 = solicitud(clientes[9], p_nomina, 40000, 24)
        solicitudes_service.cancelar(db, s10.id, clientes[9], "El cliente ya no requiere el crédito")

        for s in (s1, s2, s3, s4, s5, s6, s7, s8, s9, s10):
            db.refresh(s)
            resumen["solicitudes"].append((s.folio, s.tipo, s.estado, s.usuario.email))
        return resumen
    finally:
        db.close()


def imprimir_resumen(resumen: dict[str, Any]) -> None:
    """Muestra en consola lo creado y las credenciales demo."""
    print("=" * 72)
    print(" SEED COMPLETADO - BANCO DEMO (todos los datos son ficticios)")
    print("=" * 72)
    print(f" Base de datos : {settings.DATABASE_URL}")
    print(f" Usuarios      : {resumen['usuarios']}")
    print(f" Cuentas       : {resumen['cuentas']}")
    print(f" Movimientos   : {resumen['movimientos']}")
    print(f" Productos     : {resumen['productos']}")
    print(f" Solicitudes   : {len(resumen['solicitudes'])}")
    for folio, tipo, estado, email in resumen["solicitudes"]:
        print(f"   - {folio}  {tipo:<9} {estado:<18} {email}")
    print("-" * 72)
    print(f" Credenciales (contraseña de todos: {PASSWORD_DEMO})")
    print("   admin@demo-banco.test                      (admin)")
    print("   valuador1@ / valuador2@demo-banco.test     (valuador)")
    print("   analista1@ / analista2@demo-banco.test     (analista)")
    print("   cliente1@ … cliente15@demo-banco.test      (cliente)")
    print("   cliente11 … cliente15 no tienen solicitudes (ideales para probar el flujo)")
    print("=" * 72)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    imprimir_resumen(ejecutar())
