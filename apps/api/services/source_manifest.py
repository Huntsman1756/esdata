"""Source manifest and freshness ledger service."""

from __future__ import annotations

import hashlib
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import text

from services.persistence import dumps_json, ensure_governance_tables, rows_to_dicts


def _find_manifest() -> Path:
    env_path = os.getenv("ESDATA_MANIFEST_PATH")
    if env_path:
        return Path(env_path)

    current = Path(__file__).resolve().parent
    relative_manifest = Path("docs") / "source-manifests" / "sociedad-valores-wave-1.md"
    for _ in range(6):
        candidate = current / relative_manifest
        if candidate.exists():
            return candidate
        current = current.parent

    raise FileNotFoundError(
        "source_manifest no encontrado. Define ESDATA_MANIFEST_PATH o monta docs/source-manifests/sociedad-valores-wave-1.md en el runtime."
    )


def _get_manifest_path() -> Path | None:
    """Lazy-lookup manifest path; returns None if not found (graceful degradation)."""
    try:
        return _find_manifest()
    except FileNotFoundError:
        return None


def _parse_manifest() -> list[dict]:
    manifest_path = _get_manifest_path()
    if not manifest_path or not manifest_path.exists():
        return []
    rows: list[dict] = []
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        if "---" in stripped or "Fuente |" in stripped:
            continue
        parts = [part.strip() for part in stripped.strip("|").split("|")]
        if len(parts) != 6:
            continue
        source_name = parts[0]
        source_id = source_name.lower().replace(" ", "-")
        source_id = {"banco-de-espana": "bde", "cnmv": "cnmv", "sepblac": "sepblac", "eur-lex": "eurlex", "cendoj": "cendoj", "aepd": "aepd"}.get(source_id, source_id)
        meta = SOURCE_METADATA.get(source_id, {})
        rows.append(
            {
                "source_id": source_id,
                "fuente": source_name,
                "referencia_canonica": parts[1],
                "tipo": parts[2],
                "prioridad": parts[3],
                "estado_actual_repo": parts[4],
                "estado_objetivo": parts[5],
                **meta,
            }
        )
    return rows

SOURCE_METADATA = {
    "cnmv": {
        "owner": "compliance",
        "trust_tier": "official-primary",
        "cadencia": "weekly",
        "modo_deteccion_cambios": "sha256",
        "worker": "worker-cnmv",
        "stale_after_hours": 24 * 8,
    },
    "sepblac": {
        "owner": "compliance",
        "trust_tier": "official-primary",
        "cadencia": "weekly",
        "modo_deteccion_cambios": "sha256",
        "worker": "worker-sepblac",
        "stale_after_hours": 24 * 8,
    },
    "eurlex": {
        "owner": "legal",
        "trust_tier": "official-primary",
        "cadencia": "weekly",
        "modo_deteccion_cambios": "etag",
        "worker": "worker-eurlex",
        "stale_after_hours": 24 * 8,
    },
    "cendoj": {
        "owner": "legal",
        "trust_tier": "official-primary",
        "cadencia": "weekly",
        "modo_deteccion_cambios": "sha256",
        "worker": "worker-cendoj",
        "stale_after_hours": 24 * 8,
    },
    "bde": {
        "owner": "risk",
        "trust_tier": "official-primary",
        "cadencia": "weekly",
        "modo_deteccion_cambios": "last-modified",
        "worker": "worker-bde",
        "stale_after_hours": 24 * 8,
    },
    "aepd": {
        "owner": "privacy",
        "trust_tier": "official-primary",
        "cadencia": "weekly",
        "modo_deteccion_cambios": "last-modified",
        "worker": "worker-aepd",
        "stale_after_hours": 24 * 8,
    },
}


def _manifest_hash() -> str:
    manifest_path = _get_manifest_path()
    if not manifest_path or not manifest_path.exists():
        return "missing-manifest"
    return hashlib.sha256(manifest_path.read_bytes()).hexdigest()


def _coerce_datetime(value: str | None):
    if not value:
        return None
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    return value


def _compute_stale(last_success_at: str | None, stale_after_hours: int) -> bool:
    parsed = _coerce_datetime(last_success_at)
    if parsed is None:
        return True
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    age_hours = (datetime.now(UTC) - parsed).total_seconds() / 3600
    return age_hours > stale_after_hours


def get_source_manifest(db) -> list[dict]:
    # MCP 4.3 keeps row-level completeness/provenance in persistence only; this
    # service intentionally remains source-level until that boundary changes.
    ensure_governance_tables()
    sources = _parse_manifest()
    for source in sources:
        row = db.execute(
            text(
                """
                SELECT finished_at, status
                FROM sync_log
                WHERE worker = :worker
                ORDER BY finished_at DESC, id DESC
                LIMIT 1
                """
            ),
            {"worker": source["worker"]},
        ).mappings().first()
        source["last_success_at"] = row["finished_at"] if row and row.get("status") == "ok" else None
        source["last_status"] = row["status"] if row else "never_run"
        source["stale"] = _compute_stale(source["last_success_at"], source["stale_after_hours"])
    return sources


def _persist_freshness_snapshots(db, sources: list[dict]) -> list[dict]:
    ensure_governance_tables()
    snapshot_at = datetime.now(UTC).isoformat()
    snapshot_version = "v1"
    manifest_hash = _manifest_hash()

    for source in sources:
        source["snapshot_at"] = snapshot_at
        source["snapshot_version"] = snapshot_version

        payload = {
            "source_id": source["source_id"],
            "last_success_at": source["last_success_at"],
            "last_status": source["last_status"],
            "stale": source["stale"],
            "cadencia": source["cadencia"],
            "modo_deteccion_cambios": source["modo_deteccion_cambios"],
        }
        db.execute(
            text(
                """
                INSERT INTO source_freshness_snapshot (
                    snapshot_id,
                    source_id,
                    snapshot_version,
                    snapshot_at,
                    last_success_at,
                    last_status,
                    stale,
                    cadencia,
                    modo_deteccion_cambios,
                    manifest_hash,
                    payload
                )
                VALUES (
                    :snapshot_id,
                    :source_id,
                    :snapshot_version,
                    :snapshot_at,
                    :last_success_at,
                    :last_status,
                    :stale,
                    :cadencia,
                    :modo_deteccion_cambios,
                    :manifest_hash,
                    :payload
                )
                """
            ),
            {
                "snapshot_id": uuid4().hex,
                "source_id": source["source_id"],
                "snapshot_version": snapshot_version,
                "snapshot_at": snapshot_at,
                "last_success_at": source["last_success_at"],
                "last_status": source["last_status"],
                "stale": 1 if source["stale"] else 0,
                "cadencia": source["cadencia"],
                "modo_deteccion_cambios": source["modo_deteccion_cambios"],
                "manifest_hash": manifest_hash,
                "payload": dumps_json(payload),
            },
        )
    if hasattr(db, "commit"):
        db.commit()
    return sources


def get_latest_freshness_snapshots(db) -> list[dict]:
    ensure_governance_tables()
    rows = rows_to_dicts(
        db.execute(
            text(
                """
                SELECT s.source_id, s.snapshot_version, s.snapshot_at
                FROM source_freshness_snapshot s
                INNER JOIN (
                    SELECT source_id, MAX(snapshot_at) AS snapshot_at
                    FROM source_freshness_snapshot
                    GROUP BY source_id
                ) latest
                  ON latest.source_id = s.source_id
                 AND latest.snapshot_at = s.snapshot_at
                ORDER BY s.source_id ASC
                """
            )
        )
    )
    return rows


def get_recent_freshness_snapshots(db) -> dict[str, list[dict]]:
    ensure_governance_tables()
    rows = rows_to_dicts(
        db.execute(
            text(
                """
                SELECT source_id, snapshot_version, snapshot_at, manifest_hash, payload
                FROM source_freshness_snapshot
                ORDER BY source_id ASC, snapshot_at DESC
                """
            )
        )
    )
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        bucket = grouped.setdefault(row["source_id"], [])
        if len(bucket) < 2:
            bucket.append(row)
    return grouped


def get_freshness_ledger(db) -> list[dict]:
    sources = _persist_freshness_snapshots(db, get_source_manifest(db))
    latest_snapshots = {row["source_id"]: row for row in get_latest_freshness_snapshots(db)}
    recent_snapshots = get_recent_freshness_snapshots(db)
    return [
        {
            "source_id": source["source_id"],
            "last_success_at": source["last_success_at"],
            "last_status": source["last_status"],
            "stale": source["stale"],
            "cadencia": source["cadencia"],
            "modo_deteccion_cambios": source["modo_deteccion_cambios"],
            "snapshot_at": latest_snapshots.get(source["source_id"], {}).get("snapshot_at", source["snapshot_at"]),
            "snapshot_version": latest_snapshots.get(source["source_id"], {}).get("snapshot_version", source["snapshot_version"]),
            "previous_snapshot_at": (
                recent_snapshots.get(source["source_id"], [None, None])[1]["snapshot_at"]
                if len(recent_snapshots.get(source["source_id"], [])) > 1
                else None
            ),
            "changed_since_previous": _snapshot_changed_since_previous(recent_snapshots.get(source["source_id"], [])),
        }
        for source in sources
    ]


def _snapshot_changed_since_previous(snapshots: list[dict]) -> bool:
    if len(snapshots) < 2:
        return False
    current, previous = snapshots[0], snapshots[1]
    return (
        current.get("manifest_hash") != previous.get("manifest_hash")
        or current.get("payload") != previous.get("payload")
    )


def _parse_cadencia_hours(cadencia: str) -> int:
    mapping = {
        "hourly": 1,
        "daily": 24,
        "weekly": 24 * 7,
        "biweekly": 24 * 14,
        "monthly": 24 * 30,
    }
    return mapping.get(cadencia, 24 * 7)


def check_and_create_freshness_alerts(db) -> list[dict]:
    ensure_governance_tables()
    sources = get_source_manifest(db)
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    created: list[dict] = []

    for source in sources:
        source_id = source["source_id"]
        cadencia = source.get("cadencia", "weekly")
        stale_after = source.get("stale_after_hours", 24 * 8)
        expected_hours = _parse_cadencia_hours(cadencia)
        last_success = source.get("last_success_at")

        is_stale = _compute_stale(last_success, stale_after)

        existing = db.execute(
            text(
                """
                SELECT id, alert_level
                FROM data_freshness_alerts
                WHERE source_id = :source_id
                  AND alert_level IN ('warning', 'critical')
                  AND acknowledged = 0
                   AND DATE(created_at) = :today
                """
            ),
            {"source_id": source_id, "today": today},
        ).mappings().first()

        if is_stale and not existing:
            age_hours = (datetime.now(UTC) - _coerce_datetime(last_success)).total_seconds() / 3600 if last_success else float("inf")
            alert_level = "critical" if age_hours > expected_hours * 2 else "warning"

            message = (
                f"Fuente '{source_id}' sin actualizaciones. "
                f"Ultimo exito: {last_success}. "
                f"Cadencia esperada: {cadencia}. "
                f"Nivel: {alert_level}."
            )

            db.execute(
                text(
                    """
                    INSERT INTO data_freshness_alerts (
                        alert_id, source_id, alert_level, stale_since,
                        expected_interval, message, acknowledged, created_at
                    )
                    VALUES (
                        :alert_id, :source_id, :alert_level, :stale_since,
                        :expected_interval, :message, 0, :created_at
                    )
                    """
                ),
                {
                    "alert_id": uuid4().hex,
                    "source_id": source_id,
                    "alert_level": alert_level,
                    "stale_since": last_success,
                    "expected_interval": cadencia,
                    "message": message,
                    "created_at": datetime.now(UTC).isoformat(),
                },
            )
            created.append({
                "source_id": source_id,
                "alert_level": alert_level,
                "stale_since": last_success,
                "expected_interval": cadencia,
                "message": message,
            })

        elif not is_stale and existing and existing["alert_level"] in ("warning", "critical"):
            db.execute(
                text(
                    """
                    INSERT INTO data_freshness_alerts (
                        alert_id, source_id, alert_level, stale_since,
                        expected_interval, message, acknowledged, created_at, resolved_at
                    )
                    VALUES (
                        :alert_id, :source_id, 'resolved', :stale_since,
                        :expected_interval, :message, 0, :created_at, :resolved_at
                    )
                    """
                ),
                {
                    "alert_id": uuid4().hex,
                    "source_id": source_id,
                    "stale_since": last_success,
                    "expected_interval": cadencia,
                    "message": f"Alerta '{existing['alert_level']}' resuelta para fuente '{source_id}'. Fuente actualizada correctamente.",
                    "created_at": datetime.now(UTC).isoformat(),
                    "resolved_at": datetime.now(UTC).isoformat(),
                },
            )

    if hasattr(db, "commit"):
        db.commit()
    return created


def get_freshness_alerts(db) -> list[dict]:
    ensure_governance_tables()
    rows = rows_to_dicts(
        db.execute(
            text(
                """
                SELECT alert_id, source_id, alert_level, stale_since,
                       expected_interval, message, acknowledged, created_at, resolved_at
                FROM data_freshness_alerts
                WHERE acknowledged = 0
                  AND alert_level IN ('warning', 'critical')
                ORDER BY
                    CASE alert_level WHEN 'critical' THEN 0 WHEN 'warning' THEN 1 END ASC,
                    created_at DESC
                """
            )
        )
    )
    return rows


def get_source_manifest_summary(db) -> dict:
    sources = get_source_manifest(db)
    stale = sum(1 for source in sources if source["stale"])
    check_and_create_freshness_alerts(db)
    return {"total": len(sources), "stale": stale, "ok": len(sources) - stale}
