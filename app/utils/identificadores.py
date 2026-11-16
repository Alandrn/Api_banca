"""Generación de identificadores demostrativos (todos con prefijo DEMO)."""

from __future__ import annotations

import random
import secrets
from datetime import datetime


def codigo_usuario(usuario_id: int) -> str:
    """Código de usuario: USR-DEMO-000001."""
    return f"USR-DEMO-{usuario_id:06d}"


def folio_solicitud(solicitud_id: int, anio: int) -> str:
    """Folio de solicitud: SOL-DEMO-2026-000001."""
    return f"SOL-DEMO-{anio}-{solicitud_id:06d}"


def folio_avaluo(avaluo_id: int, anio: int) -> str:
    """Folio de avalúo: AVA-DEMO-2026-000001."""
    return f"AVA-DEMO-{anio}-{avaluo_id:06d}"


def numero_cuenta(rng: random.Random | None = None) -> str:
    """Número de cuenta ficticio: DEMO-XXXX-XXXX-XXXX (no es CLABE ni tarjeta)."""
    generador = rng or random.SystemRandom()
    bloques = ["".join(str(generador.randint(0, 9)) for _ in range(4)) for _ in range(3)]
    return "DEMO-" + "-".join(bloques)


def referencia_movimiento(fecha: datetime, rng: random.Random | None = None) -> str:
    """Referencia de movimiento: MOV-DEMO-AAAAMMDD-XXXXXXXX."""
    if rng is None:
        sufijo = secrets.token_hex(4).upper()
    else:
        sufijo = f"{rng.getrandbits(32):08X}"
    return f"MOV-DEMO-{fecha:%Y%m%d}-{sufijo}"


def enmascarar_cuenta(numero: str) -> str:
    """Enmascara un número de cuenta dejando visibles los últimos 4 dígitos: ****7712."""
    digitos = [c for c in numero if c.isdigit()]
    return "****" + "".join(digitos[-4:])
