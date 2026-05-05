import sys
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
