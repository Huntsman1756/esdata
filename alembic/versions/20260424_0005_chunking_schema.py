"""add chunking tables: documento_seccion and documento_fragmento

# Revision ID: 20260424_0005_chunking_schema
# Revises: 20260424_0004_doctrina_fulltext
# Create Date: 2026-04-24 00:00:00

Creates:
  - documento_seccion: natural document boundaries (chapters, sections, parts)
  - documento_fragmento: search-optimized chunks with tsvector + trigger

Dialect: PostgreSQL only. SQLite tests use conftest.py schema (no Alembic).

Design decisions:
  - documento_seccion has NO FK to any document table; uses (tipo, id) pair
    to allow linking across corpora (legislation, doctrine, BDNS, BORME, CNMV, SEPBLAC).
  - documento_fragmento has:
    - (documento_origen_tipo, documento_origen_id) for parent lookup
    - seccion_id -> documento_seccion(id) for section navigation
    - chunk_index for ordering within a document
    - search_vector TSVECTOR with auto-update trigger
  - All CREATE statements use IF NOT EXISTS for idempotency.
  - No FK from obligacion_regulatoria to chunks (phased approach).
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260424_0005_chunking_schema"
down_revision = "20260424_0004_doctrina_fulltext"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. documento_seccion ──────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS documento_seccion (
            id SERIAL PRIMARY KEY,
            documento_origen_tipo TEXT NOT NULL,
            documento_origen_id INTEGER NOT NULL,
            tipo_seccion TEXT NOT NULL,
            numero TEXT,
            titulo TEXT,
            nivel INTEGER DEFAULT 0,
            orden INTEGER DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_documento_seccion_origen
            ON documento_seccion(documento_origen_tipo, documento_origen_id)
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_documento_seccion_tipo
            ON documento_seccion(tipo_seccion)
        """
    )

    # ── 2. documento_fragmento ────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS documento_fragmento (
            id SERIAL PRIMARY KEY,
            documento_origen_tipo TEXT NOT NULL,
            documento_origen_id INTEGER NOT NULL,
            seccion_id INTEGER,
            chunk_index INTEGER NOT NULL,
            chunk_type TEXT NOT NULL DEFAULT 'natural',
            titulo TEXT,
            texto TEXT NOT NULL,
            char_start INTEGER,
            char_end INTEGER,
            token_count INTEGER,
            search_vector TSVECTOR,
            created_at TIMESTAMPTZ DEFAULT now(),
            UNIQUE(documento_origen_tipo, documento_origen_id, chunk_index)
        )
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_documento_fragmento_origen
            ON documento_fragmento(documento_origen_tipo, documento_origen_id)
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_documento_fragmento_seccion
            ON documento_fragmento(seccion_id)
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_documento_fragmento_chunk_type
            ON documento_fragmento(chunk_type)
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_documento_fragmento_search_vector
            ON documento_fragmento USING GIN (search_vector)
        """
    )

    # ── 3. Trigger function + trigger ─────────────────────────────────
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_documento_fragmento_search_vector()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.search_vector := to_tsvector('spanish',
                COALESCE(NEW.titulo, '') || ' ' || NEW.texto);
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )

    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_documento_fragmento_search_vector
            ON documento_fragmento
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_documento_fragmento_search_vector
            BEFORE INSERT OR UPDATE OF texto, titulo ON documento_fragmento
            FOR EACH ROW
            EXECUTE FUNCTION update_documento_fragmento_search_vector()
        """
    )


def downgrade() -> None:
    # Drop in reverse order of creation

    # 1. Trigger + function
    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_documento_fragmento_search_vector
            ON documento_fragmento
        """
    )

    op.execute(
        """
        DROP FUNCTION IF EXISTS update_documento_fragmento_search_vector()
        """
    )

    # 2. Indexes
    op.execute(
        "DROP INDEX IF EXISTS idx_documento_fragmento_search_vector"
    )
    op.execute(
        "DROP INDEX IF EXISTS idx_documento_fragmento_chunk_type"
    )
    op.execute(
        "DROP INDEX IF EXISTS idx_documento_fragmento_seccion"
    )
    op.execute(
        "DROP INDEX IF EXISTS idx_documento_fragmento_origen"
    )
    op.execute(
        "DROP INDEX IF EXISTS idx_documento_seccion_tipo"
    )
    op.execute(
        "DROP INDEX IF EXISTS idx_documento_seccion_origen"
    )

    # 3. Tables (reverse creation order)
    op.execute("DROP TABLE IF EXISTS documento_fragmento")
    op.execute("DROP TABLE IF EXISTS documento_seccion")
