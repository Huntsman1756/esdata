from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import text

from db import db_session
from services.modelos import get_modelos_status

router = APIRouter()

WORKERS = [
    "worker-boe",
    "cron-boe-daily",
    "worker-dgt",
    "cron-dgt-weekly",
    "worker-teac",
    "cron-teac-weekly",
    "worker-bdns",
    "cron-bdns-weekly",
    "worker-borme",
    "cron-borme-weekly",
    "worker-cnmv",
    "cron-cnmv-weekly",
    "worker-sepblac",
    "cron-sepblac-weekly",
    "worker-modelos",
    "cron-modelos-daily",
]


@router.get("/status")
async def status():
    """Estado agregado de la API y de los workers desplegados."""
    result = {
        "workers": {},
        "api": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    with db_session() as db:
        result["modelos"] = get_modelos_status(db)

        for worker in WORKERS:
            row = db.execute(
                text(
                    """
                    SELECT
                        started_at,
                        finished_at,
                        status,
                        bloques_processed,
                        articulos_upserted,
                        documentos_processed,
                        documentos_upserted,
                        doctrina_links_created,
                        error_msg
                    FROM sync_log
                    WHERE worker = :worker
                    ORDER BY started_at DESC
                    LIMIT 1
                    """
                ),
                {"worker": worker},
            ).fetchone()

            if row:
                result["workers"][worker] = {
                    "last_run": _serialize_datetime(row.started_at),
                    "finished_at": _serialize_datetime(row.finished_at),
                    "status": row.status,
                    "bloques_processed": row.bloques_processed,
                    "articulos_upserted": row.articulos_upserted,
                    "documentos_processed": row.documentos_processed,
                    "documentos_upserted": row.documentos_upserted,
                    "doctrina_links_created": row.doctrina_links_created,
                    "error": row.error_msg,
                    "stale": _is_stale(worker, row.finished_at),
                }
            else:
                result["workers"][worker] = {"status": "never_run", "stale": True}

    return result


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
    """Un worker se considera stale si lleva mas tiempo del esperado sin completar."""
    finished_at_dt = _coerce_datetime(finished_at)
    if not finished_at_dt:
        return True

    now = datetime.now(timezone.utc)
    age_hours = (now - finished_at_dt).total_seconds() / 3600
    thresholds = {
        "worker-boe": 25,
        "cron-boe-daily": 25,
        "worker-dgt": 24 * 8,
        "cron-dgt-weekly": 24 * 8,
        "worker-teac": 24 * 8,
        "cron-teac-weekly": 24 * 8,
        "worker-bdns": 24 * 8,
        "cron-bdns-weekly": 24 * 8,
        "worker-borme": 24 * 8,
        "cron-borme-weekly": 24 * 8,
        "worker-cnmv": 24 * 8,
        "cron-cnmv-weekly": 24 * 8,
        "worker-sepblac": 24 * 8,
        "cron-sepblac-weekly": 24 * 8,
        "worker-modelos": 25,
        "cron-modelos-daily": 25,
    }
    return age_hours > thresholds.get(worker, 25)


@router.get("/health")
async def health():
    return {"status": "ok"}
