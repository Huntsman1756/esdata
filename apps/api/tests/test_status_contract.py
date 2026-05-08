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


def _seed_sync_log(
    worker: str,
    *,
    finished_at: datetime,
    status: str = "success",
    error_msg: str | None = None,
    errors: int = 0,
) -> None:
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
                "error_msg": error_msg,
                "rows_processed": 6,
                "errors": errors,
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


@pytest.mark.asyncio
async def test_status_normalizes_historical_modelos_worker_name():
    app, _ = _get_app_and_engine()
    _seed_sync_log("worker-aeat-modelos", finished_at=datetime.now(UTC) - timedelta(hours=1), status="partial")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/status")

    assert response.status_code == 200
    worker = response.json()["workers"]["worker-modelos"]
    assert worker["status"] == "partial"
    assert worker["stale"] is False


@pytest.mark.asyncio
async def test_status_ignores_historical_modelos_alias_metrics(monkeypatch):
    app, _ = _get_app_and_engine()
    now = datetime.now(UTC)
    _seed_sync_log("modelos", finished_at=now - timedelta(hours=2), status="error")
    _seed_sync_log("worker-modelos", finished_at=now - timedelta(minutes=30), status="ok")

    recorded_errors = {}
    recorded_metrics = {}

    def _capture_errors(worker: str, errors: int | None) -> None:
        recorded_errors[worker] = errors

    def _capture_metrics(worker: str, stale: bool, lag_seconds: float | None) -> None:
        recorded_metrics[worker] = {"stale": stale, "lag_seconds": lag_seconds}

    monkeypatch.setattr("routers.status.record_worker_last_errors", _capture_errors)
    monkeypatch.setattr("routers.status.record_worker_metrics", _capture_metrics)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/status")

    assert response.status_code == 200
    assert "modelos" not in recorded_errors
    assert recorded_errors["worker-modelos"] == 0
    assert "modelos" not in recorded_metrics
    assert response.json()["workers"]["worker-modelos"]["status"] == "ok"


@pytest.mark.asyncio
async def test_status_keeps_weekly_cron_healthy_with_three_day_lag():
    app, _ = _get_app_and_engine()
    _seed_sync_log(
        "cron-cnmv-weekly",
        finished_at=datetime.now(UTC) - timedelta(hours=72),
        status="ok",
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/status")

    assert response.status_code == 200
    worker = response.json()["workers"]["cron-cnmv-weekly"]
    assert worker["status"] == "ok"
    assert worker["stale"] is False


@pytest.mark.asyncio
async def test_status_exposes_structured_sync_log_summary_fields():
    app, _ = _get_app_and_engine()
    _seed_sync_log(
        "cron-eurlex-weekly",
        finished_at=datetime.now(UTC) - timedelta(minutes=10),
        status="ok",
        error_msg="summary: unchanged=1623; no_index=0; fetch_errors=0",
        errors=0,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/status")

    assert response.status_code == 200
    worker = response.json()["workers"]["cron-eurlex-weekly"]
    assert worker["error"] == "summary: unchanged=1623; no_index=0; fetch_errors=0"
    assert worker["sync_summary"] == {
        "unchanged": 1623,
        "no_index": 0,
        "fetch_errors": 0,
    }


@pytest.mark.asyncio
async def test_status_keeps_weekly_cron_healthy_with_three_day_lag():
    app, _ = _get_app_and_engine()
    _seed_sync_log(
        "cron-cnmv-weekly",
        finished_at=datetime.now(UTC) - timedelta(hours=72),
        status="ok",
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/status")

    assert response.status_code == 200
    worker = response.json()["workers"]["cron-cnmv-weekly"]
    assert worker["status"] == "ok"
    assert worker["stale"] is False


@pytest.mark.asyncio
async def test_status_omits_sync_summary_when_error_message_is_not_structured():
    app, _ = _get_app_and_engine()
    _seed_sync_log(
        "worker-eurlex",
        finished_at=datetime.now(UTC) - timedelta(minutes=10),
        status="error",
        error_msg="boom",
        errors=1,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/status")

    assert response.status_code == 200
    worker = response.json()["workers"]["worker-eurlex"]
    assert worker["error"] == "boom"
    assert worker["sync_summary"] is None
