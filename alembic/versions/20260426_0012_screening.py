"""add screening tables for sanctions, PEPs and entity resolution

Creates screening_lists, screening_entries and screening_matches tables
to support compliance screening against sanctions and PEPs lists.

# Revision ID: 20260426_0012_screening
# Revises: 20260426_0011_entity_identity
# Create Date: 2026-04-26 00:00:00

"""

from alembic import op
import sqlalchemy as sa

revision = "20260426_0012_screening"
down_revision = "20260426_0011_entity_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # screening_lists: catalog of sanction/PEP lists
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS screening_lists (
            id SERIAL PRIMARY KEY,
            codigo TEXT NOT NULL UNIQUE,
            nombre TEXT NOT NULL,
            tipo TEXT NOT NULL CHECK (tipo IN ('sanctions', 'pep', 'watchlist')),
            organismo TEXT NOT NULL,
            pais CHAR(2),
            url_fuente TEXT,
            descripcion TEXT,
            actualizada DATE,
            activo BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_screening_lists_tipo
            ON screening_lists(tipo)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_screening_lists_activo
            ON screening_lists(activo)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_screening_lists_pais
            ON screening_lists(pais)
        """
    )

    # screening_entries: individual sanctioned entities/persons from each list
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS screening_entries (
            id SERIAL PRIMARY KEY,
            list_id INTEGER NOT NULL REFERENCES screening_lists(id),
            entidad_id TEXT NOT NULL,
            nombre TEXT NOT NULL,
            nombre_normalizado TEXT NOT NULL,
            tipo_entidad TEXT NOT NULL CHECK (tipo_entidad IN ('person', 'entity', 'vessel', 'aircraft')),
            pais CHAR(2),
            nif TEXT,
            fecha_nacimiento DATE,
            aliases TEXT[],
            categorias TEXT[],
            descripcion TEXT,
            fecha_sancion DATE,
            fecha_alta DATE,
            fecha_baja DATE,
            activo BOOLEAN NOT NULL DEFAULT true,
            metadata_json JSONB,
            created_at TIMESTAMPTZ DEFAULT now(),
            UNIQUE (list_id, entidad_id)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_screening_entries_list
            ON screening_entries(list_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_screening_entries_nombre_trgm
            ON screening_entries USING gin (nombre gin_trgm_ops)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_screening_entries_normalizado_trgm
            ON screening_entries USING gin (nombre_normalizado gin_trgm_ops)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_screening_entries_tipo_entidad
            ON screening_entries(tipo_entidad)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_screening_entries_pais
            ON screening_entries(pais)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_screening_entries_activo
            ON screening_entries(activo)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_screening_entries_nif
            ON screening_entries(nif)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_screening_entries_nif_trgm
            ON screening_entries USING gin (nif gin_trgm_ops)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_screening_entries_metadata
            ON screening_entries USING gin (metadata_json)
        """
    )
    op.execute(
        sa.text(
            """
            CREATE OR REPLACE FUNCTION immutable_array_to_string(arr text[], sep text)
            RETURNS text LANGUAGE sql IMMUTABLE STRICT AS
            $$ SELECT array_to_string(arr, sep); $$
            """
        )
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_screening_entries_ali_trgm
            ON screening_entries
            USING gin (immutable_array_to_string(aliases, ' ') gin_trgm_ops)
        """
    )

    # screening_matches: results of screening checks with scoring
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS screening_matches (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL REFERENCES empresa(id),
            entry_id INTEGER NOT NULL REFERENCES screening_entries(id),
            list_id INTEGER NOT NULL REFERENCES screening_lists(id),
            confianza NUMERIC(3,2) NOT NULL,
            motivo TEXT NOT NULL,
            match_campo TEXT NOT NULL,
            match_texto TEXT,
            revisado BOOLEAN NOT NULL DEFAULT false,
            revisor TEXT,
            revisado_at TIMESTAMPTZ,
            notas TEXT,
            created_at TIMESTAMPTZ DEFAULT now(),
            UNIQUE (empresa_id, entry_id)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_screening_matches_empresa
            ON screening_matches(empresa_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_screening_matches_entry
            ON screening_matches(entry_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_screening_matches_list
            ON screening_matches(list_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_screening_matches_confianza
            ON screening_matches(confianza)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_screening_matches_revisado
            ON screening_matches(revisado)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_screening_matches_motivo
            ON screening_matches(motivo)
        """
    )


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS idx_screening_entries_ali_trgm"))
    op.execute(
        sa.text("DROP FUNCTION IF EXISTS immutable_array_to_string(text[], text)")
    )
    op.drop_table("screening_matches")
    op.drop_table("screening_entries")
    op.drop_table("screening_lists")
