"""Tests for status-derived Prometheus sync summary metrics."""

import sys
from pathlib import Path
from unittest.mock import patch

from httpx import ASGITransport, AsyncClient


def test_metrics_endpoint_exposes_worker_sync_summary_metrics():
    from middleware.metrics import record_worker_sync_summary

    with patch.dict("os.environ", {"APP_ENV": "test", "ESDATA_API_KEY": "test-key", "MCP_API_KEY": "test-key"}):
        if "main" in sys.modules:
            del sys.modules["main"]
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from main import app as metrics_app

    record_worker_sync_summary("cron-eurlex-weekly", {"unchanged": 1623, "no_index": 0, "fetch_errors": 0})

    client = AsyncClient(transport=ASGITransport(app=metrics_app), base_url="http://test")

    async def _check():
        return await client.get("/metrics")

    import asyncio

    loop = asyncio.new_event_loop()
    try:
        response = loop.run_until_complete(_check())
    finally:
        loop.close()

    assert response.status_code == 200
    assert "worker_sync_summary" in response.text
    assert 'worker_sync_summary{kind="unchanged",worker="cron-eurlex-weekly"} 1623.0' in response.text
    assert 'worker_sync_summary{kind="no_index",worker="cron-eurlex-weekly"} 0.0' in response.text
    assert 'worker_sync_summary{kind="fetch_errors",worker="cron-eurlex-weekly"} 0.0' in response.text
