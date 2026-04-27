from datetime import UTC, datetime

from db import db_session
from fastapi import APIRouter
from middleware.metrics import record_worker_metrics
from services.modelos import get_modelos_status
from services.source_manifest import get_source_manifest_summary
from sqlalchemy import text

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
    "worker-cendoj",
    "cron-cendoj-weekly",
    "worker-eurlex",
    "cron-eurlex-weekly",
    "worker-bde",
    "cron-bde-weekly",
    "worker-aepd",
    "cron-aepd-weekly",
]


@router.get("/status")
async def status():
    """Estado agregado de la API y de los workers desplegados."""
    result = {
        "workers": {},
        "api": "ok",
        "timestamp": datetime.now(UTC).isoformat(),
    }

    with db_session() as db:
        try:
            result["modelos"] = get_modelos_status(db)
        except Exception:
            db.rollback()
            result["modelos"] = {"error": "unavailable"}

        try:
            result["fuentes"] = get_source_manifest_summary(db)
        except Exception:
            db.rollback()
            result["fuentes"] = {"total": 0, "stale": 0, "ok": 0}

        for worker in WORKERS:
            try:
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
                            error_msg,
                            rows_processed,
                            errors,
                            duration_ms
                        FROM sync_log
                        WHERE worker = :worker
                        ORDER BY started_at DESC
                        LIMIT 1
                        """
                    ),
                    {"worker": worker},
                ).fetchone()

                if row:
                    stale = _is_stale(worker, row.finished_at)
                    lag_seconds = _compute_lag_seconds(row.finished_at)
                    result["workers"][worker] = {
                        "last_run": _serialize_datetime(row.started_at),
                        "finished_at": _serialize_datetime(row.finished_at),
                        "status": row.status,
                        "bloques_processed": row.bloques_processed,
                        "articulos_upserted": row.articulos_upserted,
                        "documentos_processed": row.documentos_processed,
                        "documentos_upserted": row.documentos_upserted,
                        "doctrina_links_created": row.doctrina_links_created,
                        "rows_processed": _coalesce_rows_processed(row),
                        "errors": _coalesce_errors(row),
                        "duration_ms": row.duration_ms,
                        "error": row.error_msg,
                        "stale": stale,
                    }
                    record_worker_metrics(worker, stale=stale, lag_seconds=lag_seconds)
                else:
                    result["workers"][worker] = {"status": "never_run", "stale": True}
                    record_worker_metrics(worker, stale=True, lag_seconds=None)
            except Exception:
                db.rollback()
                result["workers"][worker] = {"status": "error", "stale": True}
                record_worker_metrics(worker, stale=True, lag_seconds=None)

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

    now = datetime.now(UTC)
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
        "worker-cendoj": 24 * 8,
        "cron-cendoj-weekly": 24 * 8,
        "worker-eurlex": 24 * 8,
        "cron-eurlex-weekly": 24 * 8,
        "worker-bde": 24 * 8,
        "cron-bde-weekly": 24 * 8,
        "worker-aepd": 24 * 8,
        "cron-aepd-weekly": 24 * 8,
    }
    return age_hours > thresholds.get(worker, 25)


def _compute_lag_seconds(finished_at) -> float | None:
    finished_at_dt = _coerce_datetime(finished_at)
    if not finished_at_dt:
        return None
    return max(0.0, (datetime.now(UTC) - finished_at_dt).total_seconds())


def _coalesce_rows_processed(row) -> int | None:
    if getattr(row, "rows_processed", None) is not None:
        return row.rows_processed
    for value in (
        getattr(row, "bloques_processed", None),
        getattr(row, "articulos_upserted", None),
        getattr(row, "documentos_processed", None),
        getattr(row, "documentos_upserted", None),
    ):
        if value is not None:
            return value
    return None


def _coalesce_errors(row) -> int:
    if getattr(row, "errors", None) is not None:
        return row.errors
    return 0 if not getattr(row, "error_msg", None) else 1


@router.get("/health")
async def health():
    try:
        from db import engine
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except Exception:
        return {"status": "degraded", "db": "disconnected"}
