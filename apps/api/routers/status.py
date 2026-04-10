# apps/api/routers/status.py
# Ajuste 3: healthcheck por servicio, no solo para la API.
# Cada worker registra su estado en sync_log; este endpoint lo agrega.

from fastapi import APIRouter
from sqlalchemy import text
from db import get_db
from datetime import datetime, timezone

router = APIRouter()

WORKERS = [
    "worker-boe",
    "worker-doctrina",
    "cron-boe-daily",
    "cron-doctrina-weekly",
]

@router.get("/status")
async def status():
    """
    Estado en tiempo real de cada worker.
    Devuelve el último sync conocido, el resultado y si hay errores recientes.
    """
    db = next(get_db())
    result = {"workers": {}, "api": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}

    for worker in WORKERS:
        row = db.execute(text("""
            SELECT started_at, finished_at, status, bloques_processed, articulos_upserted, error_msg
            FROM sync_log
            WHERE worker = :worker
            ORDER BY started_at DESC
            LIMIT 1
        """), {"worker": worker}).fetchone()

        if row:
            result["workers"][worker] = {
                "last_run": row.started_at.isoformat() if row.started_at else None,
                "finished_at": row.finished_at.isoformat() if row.finished_at else None,
                "status": row.status,
                "bloques_processed": row.bloques_processed,
                "articulos_upserted": row.articulos_upserted,
                "error": row.error_msg,
                "stale": _is_stale(worker, row.finished_at),
            }
        else:
            result["workers"][worker] = {"status": "never_run", "stale": True}

    return result


def _is_stale(worker: str, finished_at) -> bool:
    """Un worker se considera stale si lleva más tiempo del esperado sin completar."""
    if not finished_at:
        return True
    now = datetime.now(timezone.utc)
    age_hours = (now - finished_at).total_seconds() / 3600
    thresholds = {
        "worker-boe": 25,           # diario, alerta si >25h sin sync
        "worker-doctrina": 170,     # semanal, alerta si >7 días + 2h
        "cron-boe-daily": 25,
        "cron-doctrina-weekly": 170,
    }
    return age_hours > thresholds.get(worker, 25)

@router.get("/health")
async def health():
    return {"status": "ok"}
