import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import create_engine, text

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))


def test_find_manifest_uses_env_override(monkeypatch):
    from services import source_manifest

    manifest = Path(__file__).resolve().parents[3] / "docs" / "source-manifests" / "sociedad-valores-wave-1.md"
    monkeypatch.setenv("ESDATA_MANIFEST_PATH", str(manifest))

    assert source_manifest._find_manifest() == manifest


def test_find_manifest_searches_upwards_from_module(monkeypatch):
    from services import source_manifest

    monkeypatch.delenv("ESDATA_MANIFEST_PATH", raising=False)
    manifest = source_manifest._find_manifest()

    assert manifest.name == "sociedad-valores-wave-1.md"
    assert manifest.exists()


def test_get_source_manifest_remains_source_level_when_row_quality_exists(monkeypatch):
    from services import source_manifest

    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE sync_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    worker TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    status TEXT NOT NULL
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE documento_interpretativo (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    organismo TEXT NOT NULL,
                    titulo TEXT NOT NULL,
                    row_completeness REAL,
                    row_provenance TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO sync_log (worker, started_at, finished_at, status)
                VALUES ('worker-cnmv', '2026-05-04T00:00:00+00:00', '2026-05-04T00:05:00+00:00', 'ok')
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO documento_interpretativo (organismo, titulo, row_completeness, row_provenance)
                VALUES ('CNMV', 'Circular interpretativa', 0.98, '{"source": "cnmv", "method": "ingestion"}')
                """
            )
        )

    monkeypatch.setattr(source_manifest, "ensure_governance_tables", lambda: None)
    monkeypatch.setattr(
        source_manifest,
        "_parse_manifest",
        lambda: [
            {
                "source_id": "cnmv",
                "fuente": "CNMV",
                "referencia_canonica": "https://www.cnmv.es/",
                "tipo": "regulatorio",
                "prioridad": "alta",
                "estado_actual_repo": "ingestado",
                "estado_objetivo": "operativo",
                "owner": "compliance",
                "trust_tier": "official-primary",
                "cadencia": "weekly",
                "modo_deteccion_cambios": "sha256",
                "worker": "worker-cnmv",
                "stale_after_hours": 24 * 8,
            }
        ],
    )

    with engine.begin() as conn:
        row_quality = conn.execute(
            text(
                """
                SELECT row_completeness, row_provenance
                FROM documento_interpretativo
                WHERE organismo = 'CNMV'
                LIMIT 1
                """
            )
        ).mappings().one()
        sources = source_manifest.get_source_manifest(conn)

    assert row_quality["row_completeness"] == 0.98
    assert row_quality["row_provenance"] == '{"source": "cnmv", "method": "ingestion"}'
    assert sources[0]["last_status"] == "ok"
    assert "row_completeness" not in sources[0]
    assert "row_provenance" not in sources[0]


def test_get_source_manifest_uses_cron_alias_when_it_is_latest_success(monkeypatch):
    from services import source_manifest

    now = datetime.now(UTC)
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE sync_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    worker TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    status TEXT NOT NULL
                )
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO sync_log (worker, started_at, finished_at, status)
                VALUES
                    ('worker-cnmv', :old_started, :old_finished, 'error'),
                    ('cron-cnmv-weekly', :new_started, :new_finished, 'ok')
                """
            ),
            {
                "old_started": (now - timedelta(days=10)).isoformat(),
                "old_finished": (now - timedelta(days=10)).isoformat(),
                "new_started": (now - timedelta(hours=1)).isoformat(),
                "new_finished": (now - timedelta(hours=1)).isoformat(),
            },
        )

    monkeypatch.setattr(source_manifest, "ensure_governance_tables", lambda: None)
    monkeypatch.setattr(
        source_manifest,
        "_parse_manifest",
        lambda: [
            {
                "source_id": "cnmv",
                "fuente": "CNMV",
                "referencia_canonica": "https://www.cnmv.es/",
                "tipo": "regulatorio",
                "prioridad": "alta",
                "estado_actual_repo": "ingestado",
                "estado_objetivo": "operativo",
                "owner": "compliance",
                "trust_tier": "official-primary",
                "cadencia": "weekly",
                "modo_deteccion_cambios": "sha256",
                "worker": "worker-cnmv",
                "cron_worker": "cron-cnmv-weekly",
                "stale_after_hours": 24 * 8,
            }
        ],
    )

    with engine.begin() as conn:
        sources = source_manifest.get_source_manifest(conn)

    assert sources[0]["last_status"] == "ok"
    assert sources[0]["last_success_at"] is not None
    assert sources[0]["stale"] is False


def test_persist_freshness_snapshot_serializes_datetime_payload(monkeypatch):
    from services import source_manifest

    class FakeDb:
        def __init__(self):
            self.params = []
            self.committed = False

        def execute(self, _statement, params=None):
            self.params.append(params or {})

        def commit(self):
            self.committed = True

    db = FakeDb()
    last_success_at = datetime.now(UTC)
    monkeypatch.setattr(source_manifest, "ensure_governance_tables", lambda: None)
    monkeypatch.setattr(source_manifest, "_manifest_hash", lambda: "hash")

    source_manifest._persist_freshness_snapshots(
        db,
        [
            {
                "source_id": "cnmv",
                "last_success_at": last_success_at,
                "last_status": "ok",
                "stale": False,
                "cadencia": "weekly",
                "modo_deteccion_cambios": "sha256",
            }
        ],
    )

    assert db.committed is True
    assert last_success_at.isoformat() in db.params[0]["payload"]
