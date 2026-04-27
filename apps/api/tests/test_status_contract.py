"""Operational contract tests for /status."""

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))


def _get_app_and_engine():
    from db import engine
    from main import app

    return app, engine


def _seed_sync_log(worker: str, *, finished_at: datetime, status: str = "success") -> None:
    _, engine = _get_app_and_engine()
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM sync_log WHERE worker = :worker"), {"worker": worker})
        conn.execute(
            text(
                """
                INSERT INTO sync_log (
                    worker, started_at, finished_at, status,
                    bloques_processed, articulos_upserted, documentos_processed,
                    documentos_upserted, doctrina_links_created, error_msg,
                    rows_processed, errors, duration_ms
                ) VALUES (
                    :worker, :started_at, :finished_at, :status,
                    :bloques_processed, :articulos_upserted, :documentos_processed,
                    :documentos_upserted, :doctrina_links_created, :error_msg,
                    :rows_processed, :errors, :duration_ms
                )
                """
            ),
            {
                "worker": worker,
                "started_at": (finished_at - timedelta(minutes=2)).isoformat(),
                "finished_at": finished_at.isoformat(),
                "status": status,
                "bloques_processed": 3,
                "articulos_upserted": 2,
                "documentos_processed": 1,
                "documentos_upserted": 1,
                "doctrina_links_created": 0,
                "error_msg": None,
                "rows_processed": 6,
                "errors": 0,
                "duration_ms": 120000,
            },
        )


@pytest.mark.asyncio
async def test_status_marks_worker_stale_when_last_sync_exceeds_threshold():
    app, _ = _get_app_and_engine()
    _seed_sync_log("worker-boe", finished_at=datetime.now(UTC) - timedelta(hours=30))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/status")

    assert response.status_code == 200
    worker = response.json()["workers"]["worker-boe"]
    assert worker["status"] == "success"
    assert worker["stale"] is True


@pytest.mark.asyncio
async def test_status_exposes_common_operability_metrics_from_sync_log():
    app, _ = _get_app_and_engine()
    _seed_sync_log("worker-dgt", finished_at=datetime.now(UTC) - timedelta(hours=1))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/status")

    assert response.status_code == 200
    worker = response.json()["workers"]["worker-dgt"]
    assert worker["rows_processed"] == 6
    assert worker["errors"] == 0
    assert worker["duration_ms"] == 120000
    assert worker["stale"] is False
