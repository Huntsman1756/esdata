"""Tests for shared change detection module."""

import hashlib
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from change_detection import (
    check_content_changed,
    compute_content_hash,
    ensure_source_revision_table,
    invalidate_old_embeddings,
    invalidate_old_embeddings_by_entity,
    record_embedding_version,
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


def test_record_revision_accepts_bytes_content(engine):
    with engine.begin() as conn:
        ensure_source_revision_table(conn)

        record_revision(conn, "worker-bde", "documento", "doc-bytes-1", b"binary-pdf-content")

        row = conn.execute(
            text(
                "SELECT content_hash_sha256, content_length FROM source_revision WHERE source_entity_id = 'doc-bytes-1'"
            )
        ).fetchone()

    assert row[0] == compute_content_hash(b"binary-pdf-content")
    assert row[1] == len(b"binary-pdf-content")


def test_record_revision_acquires_postgres_advisory_lock_before_upsert(monkeypatch):
    calls = []

    class FakeDialect:
        name = "postgresql"

    class FakeEngine:
        dialect = FakeDialect()

    class FakeConn:
        engine = FakeEngine()

        def execute(self, stmt, params=None):
            sql = str(stmt)
            calls.append((sql, params))

            class Result:
                def fetchone(self):
                    return None

                def scalar(self):
                    return None

            return Result()

    conn = FakeConn()

    record_revision(conn, "worker-sepblac", "documento", "SEPBLAC-COMUNICACION-INDICIO", "body")

    assert "pg_advisory_xact_lock" in calls[0][0]
    assert calls[0][1]["lock_key"] == "worker-sepblac:documento:SEPBLAC-COMUNICACION-INDICIO"
    assert any("INSERT INTO source_revision" in sql for sql, _ in calls[1:])


def test_invalidate_old_embeddings(engine):
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS version_articulo"))
        conn.execute(text("""
            CREATE TABLE version_articulo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                boe_bloque_id TEXT,
                texto TEXT,
                embedding TEXT,
                embedding_model_name TEXT,
                content_hash TEXT
            )
        """))
        conn.execute(text("""
            INSERT INTO version_articulo (boe_bloque_id, texto, embedding, embedding_model_name, content_hash)
            VALUES ('bloque-1', 'text with embedding', '[0.1, 0.2, 0.3]', 'MiniLM-L12-v2', 'hash1')
        """))
        conn.execute(text("""
            INSERT INTO version_articulo (boe_bloque_id, texto, embedding)
            VALUES ('bloque-2', 'text without embedding', NULL)
        """))

        count = invalidate_old_embeddings(conn, "bloque-1")
    assert count == 1

    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT embedding, embedding_model_name, content_hash FROM version_articulo WHERE boe_bloque_id = 'bloque-1'")
        ).fetchone()
    assert row[0] is None
    assert row[1] is None
    assert row[2] is None


def test_invalidate_old_embeddings_by_entity(engine):
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS documento_fragmento"))
        conn.execute(text("""
            CREATE TABLE documento_fragmento (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                seccion TEXT,
                embedding TEXT,
                embedding_model_name TEXT,
                content_hash TEXT
            )
        """))
        conn.execute(text("""
            INSERT INTO documento_fragmento (seccion, embedding, embedding_model_name, content_hash)
            VALUES ('sec-1', '[0.1]', 'MiniLM', 'hash1')
        """))
        conn.execute(text("""
            INSERT INTO documento_fragmento (seccion, embedding)
            VALUES ('sec-2', NULL)
        """))

        count = invalidate_old_embeddings_by_entity(
            conn, "documento_fragmento", "seccion", "sec-1"
        )
    assert count == 1

    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT embedding, embedding_model_name, content_hash FROM documento_fragmento WHERE seccion = 'sec-1'")
        ).fetchone()
    assert row[0] is None
    assert row[1] is None
    assert row[2] is None


def test_invalidate_old_embeddings_by_entity_returns_zero_when_embedding_column_missing(engine):
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS documento_interpretativo"))
        conn.execute(text("""
            CREATE TABLE documento_interpretativo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referencia TEXT,
                embedding_model_name TEXT,
                content_hash TEXT
            )
        """))
        conn.execute(text("""
            INSERT INTO documento_interpretativo (referencia, embedding_model_name, content_hash)
            VALUES ('DOC-1', 'MiniLM', 'hash-doc-1')
        """))

        count = invalidate_old_embeddings_by_entity(
            conn, "documento_interpretativo", "referencia", "DOC-1"
        )

    assert count == 0

    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT embedding_model_name, content_hash FROM documento_interpretativo WHERE referencia = 'DOC-1'")
        ).fetchone()
    assert row == ("MiniLM", "hash-doc-1")


def test_record_embedding_version(engine):
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS embedding_version"))
        conn.execute(text("""
            CREATE TABLE embedding_version (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_table TEXT NOT NULL,
                entity_id INTEGER NOT NULL,
                model_name TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                dimensions INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT (datetime('now')),
                invalidated_at TIMESTAMP,
                UNIQUE(entity_table, entity_id, model_name, content_hash)
            )
        """))

        record_embedding_version(
            conn, "version_articulo", 1, "MiniLM", "hash1", 384
        )

        row = conn.execute(
            text("SELECT model_name, content_hash, dimensions, invalidated_at FROM embedding_version WHERE entity_id = 1")
        ).fetchone()
    assert row[0] == "MiniLM"
    assert row[1] == "hash1"
    assert row[2] == 384
    assert row[3] is None


def test_record_embedding_version_invalidates_old(engine):
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS embedding_version"))
        conn.execute(text("""
            CREATE TABLE embedding_version (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_table TEXT NOT NULL,
                entity_id INTEGER NOT NULL,
                model_name TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                dimensions INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT (datetime('now')),
                invalidated_at TIMESTAMP,
                UNIQUE(entity_table, entity_id, model_name, content_hash)
            )
        """))

        record_embedding_version(
            conn, "version_articulo", 1, "MiniLM", "hash1", 384
        )
        record_embedding_version(
            conn, "version_articulo", 1, "MiniLM", "hash2", 384
        )

        old_row = conn.execute(
            text("SELECT invalidated_at FROM embedding_version WHERE content_hash = 'hash1'")
        ).fetchone()
        new_row = conn.execute(
            text("SELECT invalidated_at FROM embedding_version WHERE content_hash = 'hash2'")
        ).fetchone()
    assert old_row[0] is not None
    assert new_row[0] is None
