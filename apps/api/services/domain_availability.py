"""Explicit 'not_available' responses for regulatory domains not yet ingested.

Multiple regulatory frameworks (MiCA, DORA, MiFID, PSD2, MAR, PRIIPs, CSRD,
PBC, SFDR, fraud) have routers exposed but their backing tables are empty.
Returning `[]` would let legal/compliance consumers mistakenly conclude
"there is no regulation here" — a liability in the Spanish tax/compliance
domain. Audit policy requires an explicit signal.

Use `check_domain(db, table, domain_label)` at the top of listing endpoints
whose table has zero rows globally. When the table is empty, returns a
JSONResponse that bypasses the router's response_model and carries the
not-available envelope; otherwise returns None so the endpoint continues.

Response shape (status HTTP 200 so clients treat as a normal response):

    {
      "status": "not_available",
      "reason": "source_not_yet_ingested",
      "domain": "MiCA",
      "table": "casp",
      "message": "Datos de MiCA no disponibles. Fuente pendiente de ingesta.",
      "items": [],
      "total": 0
    }

Downstream clients (LLM/UI) MUST check `status == "not_available"` and
surface it as "no hay cobertura todavía en nuestra base", NOT as "no hay
regulación aplicable".
"""

from __future__ import annotations

from fastapi.responses import JSONResponse
from sqlalchemy import text


def _table_is_empty(db, table_name: str) -> bool:
    """Return True iff the table exists and has zero rows.

    If the table does not exist (OperationalError / UndefinedTable), treat as
    empty — the router-level OperationalError handler would return the same
    envelope downstream.
    """
    try:
        total = db.execute(
            text(f"SELECT COUNT(*) FROM {table_name}")
        ).scalar_one()
        return total == 0
    except Exception:
        return True


def _envelope(table: str, domain_label: str, message_es: str | None) -> dict:
    return {
        "status": "not_available",
        "reason": "source_not_yet_ingested",
        "domain": domain_label,
        "table": table,
        "message": message_es
        or f"Datos de {domain_label} no disponibles. Fuente pendiente de ingesta.",
        "items": [],
        "total": 0,
    }


def check_domain(
    db,
    table: str,
    domain_label: str,
    *,
    message_es: str | None = None,
) -> JSONResponse | None:
    """Return a not-available JSONResponse if the domain table is empty.

    Usage at top of a listing endpoint (including endpoints with response_model):

        with db_session() as db:
            unavailable = check_domain(db, "casp", "MiCA")
            if unavailable is not None:
                return unavailable
            ...existing query...

    Returns JSONResponse (status 200) to bypass FastAPI response_model coercion.
    """
    if _table_is_empty(db, table):
        return JSONResponse(
            status_code=200,
            content=_envelope(table, domain_label, message_es),
        )
    return None

