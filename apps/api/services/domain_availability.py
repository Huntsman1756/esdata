"""Domain availability contract for empty regulatory tables.

The Ralph table registry is the source of truth for whether an empty table is
acceptable workflow state, an allowed healthy empty table, or a configured
domain whose source ingestion is not available yet. API/MCP clients must see
that explicitly instead of receiving a bare `[]` that could be interpreted as a
legal or fiscal conclusion.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi.responses import JSONResponse
from sqlalchemy import text

EMPTY_STATUSES = {
    "workflow_empty",
    "allowed_empty",
    "configured_but_unavailable",
}

CONFIGURED_UNAVAILABLE_MARKERS = (
    "official",
    "fuente oficial",
    "source ingestion",
    "ingestion is configured",
    "ingestion exists",
    "ingestion target",
    "parser",
    "registry ingestion",
    "report ingestion",
    "filing ingestion",
    "public report",
    "source urls",
    "cnmv",
    "esma",
    "eba",
    "boe",
    "borme",
    "irs",
    "gleif",
    "dgsfp",
)

WORKFLOW_MARKERS = (
    "user",
    "workflow",
    "entity-specific",
    "proprietary",
    "internal",
    "incident",
    "eval",
    "review",
    "alert",
    "no fake",
    "no synthetic",
    "healthy",
    "runtime",
)


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _find_registry() -> Path:
    env_path = os.getenv("ESDATA_TABLE_REGISTRY_PATH")
    if env_path:
        return Path(env_path)

    current = Path(__file__).resolve().parent
    relative_registry = Path("scripts") / "ralph" / "table-remediation-registry.json"
    for root in [current, *current.parents]:
        candidate = root / relative_registry
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        "table-remediation-registry.json no encontrado. Define ESDATA_TABLE_REGISTRY_PATH o monta scripts/ralph en el runtime."
    )


@lru_cache(maxsize=1)
def _load_registry() -> dict[str, Any]:
    with _find_registry().open("r", encoding="utf-8") as handle:
        return json.load(handle)


def clear_registry_cache() -> None:
    _load_registry.cache_clear()


def _table_count(db, table_name: str) -> int | None:
    statement = text(f"SELECT COUNT(*) FROM {_quote_identifier(table_name)}")
    try:
        if hasattr(db, "connect") and not hasattr(db, "execute"):
            with db.connect() as conn:
                return int(conn.execute(statement).scalar_one())
        return int(db.execute(statement).scalar_one())
    except Exception:
        return None


def _table_is_empty(db, table_name: str) -> bool:
    total = _table_count(db, table_name)
    return total is None or total == 0


def _registry_items() -> list[dict[str, Any]]:
    payload = _load_registry()
    return list(payload.get("tables") or [])


def get_registry_item(table: str) -> dict[str, Any] | None:
    for item in _registry_items():
        if item.get("table") == table:
            return item
    return None


def _availability_status(item: dict[str, Any], row_count: int | None) -> str:
    if row_count and row_count > 0:
        return "populated"

    classification = str(item.get("classification") or "configured_but_unavailable")
    if classification == "populated":
        return "configured_but_unavailable"
    if classification == "allowed_empty":
        return "allowed_empty"
    if classification == "configured_but_unavailable":
        return "configured_but_unavailable"
    if classification in {"blocker", "derived_blocker", "unclassified"}:
        return "configured_but_unavailable"
    if classification != "workflow_empty":
        return classification

    action = str(item.get("action") or "").lower()
    configured = any(marker in action for marker in CONFIGURED_UNAVAILABLE_MARKERS)
    workflow = any(marker in action for marker in WORKFLOW_MARKERS)
    if configured and not workflow:
        return "configured_but_unavailable"
    return "workflow_empty"


def _reason_for_status(status: str) -> str:
    return {
        "workflow_empty": "workflow_has_no_real_rows",
        "allowed_empty": "empty_is_valid_operational_state",
        "configured_but_unavailable": "source_or_ingestion_not_available",
        "populated": "table_has_real_rows",
    }.get(status, "availability_status_from_registry")


def _message(item: dict[str, Any], status: str, row_count: int | None) -> str:
    table = item.get("table")
    domain = item.get("domain") or "Dominio no clasificado"
    if status == "populated":
        return f"Tabla {table} disponible para {domain}: {row_count} filas reales en la base consultada."
    if status == "allowed_empty":
        return (
            f"Tabla {table} vacia de forma permitida para {domain}. "
            "No implica ausencia de obligacion; solo que no hay eventos/configuracion que registrar ahora."
        )
    if status == "workflow_empty":
        return (
            f"Tabla {table} vacia por flujo de trabajo para {domain}. "
            "No se deben inventar filas; la respuesta debe indicar que no hay datos reales del workflow."
        )
    return (
        f"Tabla {table} configurada pero sin datos disponibles para {domain}. "
        "La ingesta/fuente oficial aun no aporta filas verificadas; no se debe responder como si hubiera cobertura."
    )


def availability_record(db, item: dict[str, Any]) -> dict[str, Any]:
    row_count = _table_count(db, str(item["table"]))
    status = _availability_status(item, row_count)
    reason = _reason_for_status(status)
    if item.get("table") == "suspicious_activity_report" and status == "workflow_empty":
        reason = "proprietary_to_obligated_entity"
    return {
        "table": item.get("table"),
        "domain": item.get("domain"),
        "row_count": row_count,
        "status": status,
        "availability_status": status,
        "reason": reason,
        "registry_classification": item.get("classification"),
        "official_source_family": item.get("official_source_family"),
        "target_path": item.get("target_path"),
        "action": item.get("action"),
        "safe_to_answer": status == "populated",
        "message": _message(item, status, row_count),
    }


def list_domain_availability(
    db,
    *,
    only_empty: bool = False,
    status: str | None = None,
    domain: str | None = None,
) -> list[dict[str, Any]]:
    records = [availability_record(db, item) for item in _registry_items()]
    if only_empty:
        records = [record for record in records if not record["safe_to_answer"]]
    if status:
        records = [record for record in records if record["availability_status"] == status]
    if domain:
        needle = domain.lower()
        records = [record for record in records if needle in str(record.get("domain") or "").lower()]
    return sorted(records, key=lambda record: (str(record.get("domain")), str(record.get("table"))))


def summarize_availability(records: list[dict[str, Any]]) -> dict[str, int]:
    summary: dict[str, int] = {
        "total": len(records),
        "populated": 0,
        "workflow_empty": 0,
        "allowed_empty": 0,
        "configured_but_unavailable": 0,
        "unknown": 0,
    }
    for record in records:
        key = record.get("availability_status")
        if key in summary:
            summary[key] += 1
        else:
            summary["unknown"] += 1
    return summary


def get_domain_availability(db, table: str) -> dict[str, Any] | None:
    item = get_registry_item(table)
    if item is None:
        return None
    return availability_record(db, item)


def availability_envelope(db, table: str, domain_label: str | None = None) -> dict:
    item = get_registry_item(table) or {
        "table": table,
        "classification": "configured_but_unavailable",
        "domain": domain_label or "Dominio no registrado",
        "official_source_family": "unknown",
        "target_path": "unknown",
        "action": "Table is exposed by API but not classified in Ralph registry.",
    }
    if domain_label and not item.get("domain"):
        item = {**item, "domain": domain_label}
    return {
        **availability_record(db, item),
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
    """Return an explicit availability JSONResponse if the domain table is empty."""

    del message_es
    if _table_is_empty(db, table):
        return JSONResponse(
            status_code=200,
            content=availability_envelope(db, table, domain_label),
        )
    return None
