"""Folios de factura INV-YYYY-NNNNNNNNNNNN, únicos en toda la tabla."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.locks import advisory_xact_lock
from app.models.invoice import Invoice

# 12 dígitos: un billón de folios por año, global. El UNIQUE es el string
# completo; el relleno no recorta (10000 sigue siendo 10000 si alguien
# llegara a emitir con menos dígitos).
SEQ_DIGITS = 12


def format_invoice_number(year: int, seq: int) -> str:
    return f"INV-{int(year)}-{int(seq):0{SEQ_DIGITS}d}"


def next_invoice_number(db: Session) -> str:
    """
    Siguiente folio global INV-YYYY- + 12 dígitos.

    `invoice_number` es UNIQUE en toda la tabla, no por cuenta. El lock
    serializa a quienes asignan folio del mismo año. Folios viejos de 4
    dígitos (INV-2026-0001) cuentan igual: el siguiente es …000000000002.
    """
    year = datetime.now(timezone.utc).year
    prefix = f"INV-{year}-"
    advisory_xact_lock(db, "invoice_number", str(year))
    rows = (
        db.query(Invoice.invoice_number)
        .filter(Invoice.invoice_number.like(f"{prefix}%"))
        .all()
    )
    max_seq = 0
    for (number,) in rows:
        try:
            max_seq = max(max_seq, int(str(number).removeprefix(prefix)))
        except ValueError:
            continue
    return format_invoice_number(year, max_seq + 1)
