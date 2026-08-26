"""
Locks de aplicación en Postgres.

Se usan para serializar operaciones de cobro que no se pueden proteger con un
`SELECT ... FOR UPDATE` porque la fila todavía no existe (por ejemplo, dos
checkouts simultáneos de la misma cuenta creando el primer pago).
"""

import hashlib

from sqlalchemy import text
from sqlalchemy.orm import Session


def advisory_xact_lock(db: Session, *parts: str) -> None:
    """
    Toma un lock de transacción derivado de `parts`.

    Se libera al terminar la transacción, así que no hay que soltarlo a mano ni
    puede quedarse colgado si el proceso muere. En SQLite (tests) no hace nada:
    las pruebas corren en serie sobre una sola conexión.
    """
    bind = db.get_bind()
    if bind.dialect.name != "postgresql":
        return
    raw = "|".join(str(p) for p in parts)
    lock_id = int.from_bytes(
        hashlib.sha256(raw.encode()).digest()[:8], "big", signed=True
    )
    db.execute(text("SELECT pg_advisory_xact_lock(:lock_id)"), {"lock_id": lock_id})
