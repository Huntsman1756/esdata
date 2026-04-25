"""Internal agent monitor — background task for regulatory change detection.

Scans for pending regulatory changes, evaluates impact on applicable obligations,
and creates workflow triggers when impact is detected.

Configured via environment variables:
  AGENT_MONITOR_ENABLED   — 'true'/'false' (default: 'false')
  AGENT_MONITOR_INTERVAL  — seconds between scans (default: 300)
  AGENT_MONITOR_ENTIDAD   — entity profile type (default: 'sociedad_valores')
  AGENT_MONITOR_PRIORIDAD — default trigger priority (default: 'media')
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

from fastapi.testclient import TestClient

from main import app as fastapi_app

logger = logging.getLogger(__name__)


@dataclass
class MonitorStatus:
    enabled: bool
    running: bool = False
    last_scan: float | None = None
    last_scan_duration_ms: float | None = None
    next_scan_in_seconds: float | None = None
    interval_seconds: int = 300
    entidad: str = "sociedad_valores"
    prioridad: str = "media"
    total_scans: int = 0
    total_triggers_created: int = 0
    errors: int = 0
    _started_at: float = field(default_factory=time.time, repr=False)


# Global singleton — initialized lazily on first status call
_monitor_status: MonitorStatus | None = None
_monitor_task: asyncio.Task | None = None
_client = TestClient(fastapi_app)


def _get_status() -> MonitorStatus:
    global _monitor_status
    if _monitor_status is None:
        _monitor_status = MonitorStatus(
            enabled=os.getenv("AGENT_MONITOR_ENABLED", "").lower() == "true",
            interval_seconds=int(os.getenv("AGENT_MONITOR_INTERVAL", "300")),
            entidad=os.getenv("AGENT_MONITOR_ENTIDAD", "sociedad_valores"),
            prioridad=os.getenv("AGENT_MONITOR_PRIORIDAD", "media"),
        )
    return _monitor_status


def get_monitor_status() -> dict[str, Any]:
    """Return current monitor status as a serializable dict."""
    status = _get_status()

    if status.running and status.last_scan is not None:
        next_in = status.interval_seconds - (time.time() - status.last_scan)
        if next_in < 0:
            next_in = 0
        status.next_scan_in_seconds = round(next_in, 1)
    else:
        status.next_scan_in_seconds = None

    return {
        "enabled": status.enabled,
        "running": status.running,
        "last_scan": status.last_scan,
        "last_scan_duration_ms": status.last_scan_duration_ms,
        "next_scan_in_seconds": status.next_scan_in_seconds,
        "interval_seconds": status.interval_seconds,
        "entidad": status.entidad,
        "prioridad": status.prioridad,
        "total_scans": status.total_scans,
        "total_triggers_created": status.total_triggers_created,
        "errors": status.errors,
    }


async def _scan_once(status: MonitorStatus) -> None:
    """Execute a single monitoring cycle."""
    status.running = True
    scan_start = time.time()

    try:
        # Step 1: Get pending changes
        resp = _client.get("/v1/cambios", params={"estado": "pendiente"})
        if resp.status_code != 200:
            logger.warning("Failed to fetch pending changes: %d", resp.status_code)
            status.errors += 1
            return

        cambios = resp.json()
        if not cambios:
            logger.info("No pending changes found")
            return

        logger.info("Found %d pending changes to evaluate", len(cambios))

        # Step 2: Get applicable obligations for the entity profile
        resp = _client.get(
            "/v1/obligaciones/aplicables",
            params={"tipo_entidad": status.entidad},
        )
        if resp.status_code != 200:
            logger.warning("Failed to fetch applicable obligations: %d", resp.status_code)
            status.errors += 1
            return

        oblig_data = resp.json()
        oblig_codes = {o["codigo"] for o in oblig_data.get("obligaciones", [])}
        logger.info("Entity '%s' has %d applicable obligations", status.entidad, len(oblig_codes))

        # Step 3: Evaluate which changes affect applicable obligations
        affected_count = 0
        for cambio in cambios:
            oblig_afectadas = cambio.get("obligaciones_afectadas", [])
            intersection = set(oblig_afectadas) & oblig_codes
            if intersection:
                affected_count += 1
                logger.info(
                    "Change '%s' affects %d applicable obligations: %s",
                    cambio.get("codigo", "?"),
                    len(intersection),
                    ", ".join(sorted(intersection)),
                )

                # Step 4: Create workflow trigger
                await _create_workflow_trigger(cambio, list(intersection), status)

        logger.info(
            "Scan complete: %d/%d changes affect applicable obligations",
            affected_count, len(cambios),
        )

    except Exception:
        logger.exception("Error during monitoring scan")
        status.errors += 1
    finally:
        status.running = False
        status.last_scan = time.time()
        status.last_scan_duration_ms = round((time.time() - scan_start) * 1000, 1)
        status.total_scans += 1


async def _create_workflow_trigger(
    cambio: dict, oblig_codes: list[str], status: MonitorStatus
) -> None:
    """Create a workflow case via the compliance endpoint."""
    try:
        # Check if a trigger already exists for this change+obligation combo
        existing_resp = _client.get("/v1/compliance/workflow")
        existing = existing_resp.json() if existing_resp.status_code == 200 else []

        for case in existing:
            if case.get("cambio_codigo") == cambio.get("codigo"):
                for existing_obl in case.get("obligacion_codigo", []):
                    if existing_obl in oblig_codes:
                        logger.info(
                            "Skipping duplicate trigger: %s for %s",
                            cambio.get("codigo"), existing_obl,
                        )
                        return

        # Create new workflow case
        payload = {
            "cambio_codigo": cambio.get("codigo"),
            "obligacion_codigo": oblig_codes,
            "estado": "pendiente",
            "owner_rol": "compliance_officer",
            "prioridad": status.prioridad,
            "notas": f"Auto-generated trigger from agent monitor. Change: {cambio.get('descripcion', cambio.get('codigo', ''))}",
        }

        resp = _client.post("/v1/compliance/workflow", json=payload)
        if resp.status_code in (200, 201):
            status.total_triggers_created += 1
            logger.info("Created workflow trigger for %s", cambio.get("codigo"))
        else:
            logger.warning(
                "Failed to create workflow trigger: %d %s",
                resp.status_code, resp.text[:200],
            )
            status.errors += 1

    except Exception:
        logger.exception("Error creating workflow trigger")
        status.errors += 1


async def _monitor_loop() -> None:
    """Main monitoring loop."""
    status = _get_status()
    status.running = True

    while True:
        await asyncio.sleep(status.interval_seconds)
        logger.info("Agent monitor scan starting...")
        await _scan_once(status)
        logger.info("Agent monitor scan complete")


def start_agent_monitor() -> None:
    """Start the agent monitor background task.

    Only starts if AGENT_MONITOR_ENABLED=true.
    Should be called from FastAPI lifespan.
    """
    status = _get_status()
    if not status.enabled:
        logger.info("Agent monitor disabled (set AGENT_MONITOR_ENABLED=true to enable)")
        return

    global _monitor_task
    if _monitor_task is not None and not _monitor_task.done():
        logger.warning("Agent monitor already running")
        return

    _monitor_task = asyncio.create_task(_monitor_loop())
    logger.info(
        "Agent monitor started (interval=%ds, entidad=%s, prioridad=%s)",
        status.interval_seconds, status.entidad, status.prioridad,
    )


def stop_agent_monitor() -> None:
    """Stop the agent monitor background task."""
    global _monitor_task
    if _monitor_task is not None and not _monitor_task.done():
        _monitor_task.cancel()
        logger.info("Agent monitor stopped")
