"""Tests for shared change detection module."""

import hashlib
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from change_detection import (
    SourceChange,
    check_content_changed,
    compute_content_hash,
    ensure_source_revision_table,
    invalidate_old_embeddings,
    record_revision,
)


@pytest.fixture()
def engine():
    return create_engine("sqlite:////tmp/test_change_detection.sqlite3")


@pytest.fixture(autouse=True)
def _setup(engine):
    with engine.begin() as conn:
        ensure_source_revision_table(conn)
    yield
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS source_revision"))


def test_compute_content_hash_str():
    h = compute_content_hash("hello")
    expected = hashlib.sha256(b"hello").hexdigest()
    assert h == expected


def test_compute_content_hash_bytes():
    h = compute_content_hash(b"hello")
    expected = hashlib.sha256(b"hello").hexdigest()
    assert h == expected


def test_check_content_changed_new_entity(engine):
    with engine.begin() as conn:
        ensure_source_revision_table(conn)
        result = check_content_changed(
            conn, "worker-boe", "bloque", "bloque-1", "some content"
        )
    assert result.changed is True
    assert result.old_hash is None
    assert result.new_hash is not None


def test_check_content_changed_unchanged(engine):
    with engine.begin() as conn:
        ensure_source_revision_table(conn)
        record_revision(conn, "worker-boe", "bloque", "bloque-1", "content v1")

        result = check_content_changed(
            conn, "worker-boe", "bloque", "bloque-1", "content v1"
        )
    assert result.changed is False
    assert result.old_hash is not None
    assert result.new_hash is None


def test_check_content_changed_modified(engine):
    with engine.begin() as conn:
        ensure_source_revision_table(conn)
        record_revision(conn, "worker-boe", "bloque", "bloque-1", "content v1")

        result = check_content_changed(
            conn, "worker-boe", "bloque", "bloque-1", "content v2"
        )
    assert result.changed is True
    assert result.old_hash != result.new_hash


def test_record_revision_upserts(engine):
    with engine.begin() as conn:
        ensure_source_revision_table(conn)

        record_revision(conn, "worker-boe", "bloque", "bloque-1", "content v1")
        record_revision(conn, "worker-boe", "bloque", "bloque-1", "content v2")

        row = conn.execute(
            text("SELECT content_hash_sha256 FROM source_revision WHERE source_entity_id = 'bloque-1'")
        ).fetchone()
    assert row is not None
    assert row[0] == compute_content_hash("content v2")


def test_record_revision_stores_etag_and_last_modified(engine):
    with engine.begin() as conn:
        ensure_source_revision_table(conn)

        record_revision(
            conn,
            "worker-boe",
            "bloque",
            "bloque-1",
            "content",
            etag='"abc123"',
            last_modified="Mon, 27 Apr 2026 00:00:00 GMT",
        )

        row = conn.execute(
            text(
                "SELECT etag, last_modified FROM source_revision WHERE source_entity_id = 'bloque-1'"
            )
        ).fetchone()
    assert row[0] == '"abc123"'
    assert row[1] == "Mon, 27 Apr 2026 00:00:00 GMT"


def test_check_content_changed_preserves_stored_revision_on_no_change(engine):
    with engine.begin() as conn:
        ensure_source_revision_table(conn)
        record_revision(conn, "worker-boe", "bloque", "bloque-1", "original")

        check_content_changed(conn, "worker-boe", "bloque", "bloque-1", "original")

        row = conn.execute(
            text("SELECT content_hash_sha256 FROM source_revision WHERE source_entity_id = 'bloque-1'")
        ).fetchone()
    assert row[0] == compute_content_hash("original")


def test_invalidate_old_embeddings(engine):
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS version_articulo"))
        conn.execute(text("""
            CREATE TABLE version_articulo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                boe_bloque_id TEXT,
                texto TEXT,
                embedding TEXT
            )
        """))
        conn.execute(text("""
            INSERT INTO version_articulo (boe_bloque_id, texto, embedding)
            VALUES ('bloque-1', 'text with embedding', '[0.1, 0.2, 0.3]')
        """))
        conn.execute(text("""
            INSERT INTO version_articulo (boe_bloque_id, texto, embedding)
            VALUES ('bloque-2', 'text without embedding', NULL)
        """))

        count = invalidate_old_embeddings(conn, "bloque-1")
    assert count == 1

    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT embedding FROM version_articulo WHERE boe_bloque_id = 'bloque-1'")
        ).fetchone()
    assert row[0] is None
