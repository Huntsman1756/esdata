import re
from datetime import UTC, datetime

from db import SessionLocal
from fastapi import APIRouter
from middleware.metrics import (
    record_worker_last_errors,
    record_worker_metrics,
    record_worker_sync_summary,
)
from sqlalchemy import text


def _build_modelos_status(db) -> dict:
    row = db.execute(
        text(
            """
            SELECT COUNT(*) AS total, MAX(updated_at) AS actualizado_en
            FROM aeat_modelo
            """
        )
    ).mappings().first()

    total = int((row or {}).get("total") or 0)
    actualizado_en = (row or {}).get("actualizado_en")
    return {
        "status": "ok",
        "total": total,
        "updated_at": _serialize_datetime(actualizado_en),
    }

router = APIRouter()

WORKER_CANONICAL_NAMES = {
    "modelos": "worker-modelos",
    "worker-aeat-modelos": "worker-modelos",
    "worker-aeat-current-designs": "cron-aeat-current-daily",
}

WORKER_THRESHOLDS_HOURS = {
    "worker-boe": 25,
    "cron-boe-daily": 25,
    "worker-dgt": 24 * 8,
    "cron-dgt-weekly": 24 * 8,
    "worker-teac": 24 * 8,
    "cron-teac-weekly": 24 * 8,
    "worker-modelos": 26,
    "cron-modelos-daily": 26,
    "cron-aeat-current-daily": 26,
    "worker-boe-modelos": 26,
    "worker-bdns": 24 * 8,
    "cron-bdns-weekly": 24 * 8,
    "worker-borme": 24 * 8,
    "cron-borme-weekly": 24 * 8,
    "worker-cnmv": 24 * 8,
    "cron-cnmv-weekly": 24 * 8,
    "worker-sepblac": 24 * 8,
    "cron-sepblac-weekly": 24 * 8,
    "worker-cendoj": 24 * 8,
    "cron-cendoj-weekly": 24 * 8,
    "worker-eurlex": 24 * 8,
    "cron-eurlex-weekly": 24 * 8,
    "worker-bde": 24 * 8,
    "cron-bde-weekly": 24 * 8,
    "worker-aepd": 24 * 8,
    "cron-aepd-weekly": 24 * 8,
}


def _serialize_datetime(value):
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _coerce_datetime(value):
    if value is None:
        return None
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    return value


def _is_stale(worker: str, finished_at) -> bool:
    finished_at_dt = _coerce_datetime(finished_at)
    if not finished_at_dt:
        return True

    now = datetime.now(UTC)
    age_hours = (now - finished_at_dt).total_seconds() / 3600
    return age_hours > WORKER_THRESHOLDS_HOURS.get(worker, 25)


def _canonical_worker_name(worker: str) -> str:
    return WORKER_CANONICAL_NAMES.get(worker, worker)


def _parse_sync_summary(error_msg: str | None) -> dict[str, int] | None:
    if not error_msg:
        return None
    match = re.fullmatch(
        r"summary:\s*unchanged=(\d+);\s*no_index=(\d+);\s*fetch_errors=(\d+)",
        error_msg.strip(),
    )
    if not match:
        return None
    unchanged, no_index, fetch_errors = match.groups()
    return {
        "unchanged": int(unchanged),
        "no_index": int(no_index),
        "fetch_errors": int(fetch_errors),
    }


@router.get("/status")
async def status():
    """Estado agregado de la API y de los workers presentes en sync_log."""
    return _build_status_payload()


def _build_status_payload():
    with SessionLocal() as db:
        result = {
            "api": "ok",
            "database": "ok",
            "timestamp": datetime.now(UTC).isoformat(),
            "modelos": {"status": "unknown", "total": 0, "updated_at": None},
            "workers": {
                worker: {"status": "never_run", "stale": True}
                for worker in WORKER_THRESHOLDS_HOURS
            },
        }

        result["modelos"] = _build_modelos_status(db)

        rows = db.execute(
            text(
                """
                WITH ranked AS (
                    SELECT
                        worker,
                        started_at,
                        finished_at,
                        status,
                        bloques_processed,
                        articulos_upserted,
                        documentos_processed,
                        documentos_upserted,
                        doctrina_links_created,
                        rows_processed,
                        errors,
                        duration_ms,
                        error_msg,
                        ROW_NUMBER() OVER (PARTITION BY worker ORDER BY started_at DESC) AS rn
                    FROM sync_log
                )
                SELECT
                    worker,
                    started_at,
                    finished_at,
                    status,
                    bloques_processed,
                    articulos_upserted,
                    documentos_processed,
                    documentos_upserted,
                    doctrina_links_created,
                    rows_processed,
                    errors,
                    duration_ms,
                    error_msg
                FROM ranked
                WHERE rn = 1
                ORDER BY worker
                """
            )
        ).mappings().all()

        for row in rows:
            worker = row["worker"]
            canonical_worker = _canonical_worker_name(worker)
            stale = _is_stale(canonical_worker, row["finished_at"])
            finished_at = _coerce_datetime(row["finished_at"])
            started_at = _coerce_datetime(row["started_at"])

            existing = result["workers"].get(canonical_worker)
            if existing and existing.get("last_run"):
                existing_started_at = _coerce_datetime(existing["last_run"])
                if existing_started_at is not None and started_at is not None and existing_started_at >= started_at:
                    continue

            lag_seconds = None
            if finished_at is not None:
                lag_seconds = (datetime.now(UTC) - finished_at).total_seconds()
            record_worker_metrics(canonical_worker, stale=stale, lag_seconds=lag_seconds)
            record_worker_last_errors(canonical_worker, row["errors"])
            sync_summary = _parse_sync_summary(row["error_msg"])
            record_worker_sync_summary(canonical_worker, sync_summary)

            result["workers"][canonical_worker] = {
                "last_run": _serialize_datetime(row["started_at"]),
                "finished_at": _serialize_datetime(row["finished_at"]),
                "status": row["status"],
                "bloques_processed": row["bloques_processed"],
                "articulos_upserted": row["articulos_upserted"],
                "documentos_processed": row["documentos_processed"],
                "documentos_upserted": row["documentos_upserted"],
                "doctrina_links_created": row["doctrina_links_created"],
                "rows_processed": row["rows_processed"],
                "errors": row["errors"],
                "duration_ms": row["duration_ms"],
                "error": row["error_msg"],
                "sync_summary": sync_summary,
                "stale": stale,
            }

    return result


def refresh_worker_status_metrics() -> None:
    _build_status_payload()


@router.get("/health")
async def health():
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
    return {
        "status": "ok",
        "database": "ok",
        "timestamp": datetime.now(UTC).isoformat(),
    }
