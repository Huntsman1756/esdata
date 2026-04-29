from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import text

from db import get_db

router = APIRouter()

WORKER_THRESHOLDS_HOURS = {
    "worker-boe": 25,
    "cron-boe-daily": 25,
    "worker-dgt": 24 * 8,
    "cron-dgt-weekly": 24 * 8,
    "worker-teac": 24 * 8,
    "cron-teac-weekly": 24 * 8,
    "worker-modelos": 26,
    "cron-modelos-daily": 26,
    "worker-bdns": 24 * 8,
    "cron-bdns-weekly": 24 * 8,
    "worker-borme": 24 * 8,
    "cron-borme-weekly": 24 * 8,
    "worker-cnmv": 24 * 8,
    "cron-cnmv-weekly": 24 * 8,
    "worker-sepblac": 24 * 8,
    "cron-sepblac-weekly": 24 * 8,
    "worker-cendoj": 24 * 8,
    "worker-eurlex": 24 * 8,
    "worker-bde": 24 * 8,
    "cron-bde-weekly": 24 * 8,
    "worker-aepd": 24 * 8,
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

    now = datetime.now(timezone.utc)
    age_hours = (now - finished_at_dt).total_seconds() / 3600
    return age_hours > WORKER_THRESHOLDS_HOURS.get(worker, 25)


@router.get("/status")
async def status():
    """Estado agregado de la API y de los workers presentes en sync_log."""
    db = next(get_db())
    result = {
        "api": "ok",
        "database": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "workers": {
            worker: {"status": "never_run", "stale": True}
            for worker in WORKER_THRESHOLDS_HOURS
        },
    }

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
        result["workers"][worker] = {
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
            "stale": _is_stale(worker, row["finished_at"]),
        }

    return result


@router.get("/health")
async def health():
    db = next(get_db())
    db.execute(text("SELECT 1"))
    return {
        "status": "ok",
        "database": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
