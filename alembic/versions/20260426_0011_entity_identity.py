"""add entity_identity tables for LEI and vLEI support

Creates the entity_identifiers and entity_aliases tables to support
Global Legal Entity Identifier (LEI) and vLEI entity identity management.

# Revision ID: 20260426_0011_entity_identity
# Revises: 20260425_0010_pgc
# Create Date: 2026-04-26 00:00:00

"""

from alembic import op

revision = "20260426_0011_entity_identity"
down_revision = "20260425_0010_pgc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # entity_identifiers: LEI, vLEI, and identity metadata for regulated entities
    op.execute(
        """
        CREATE TABLE entity_identifiers (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL REFERENCES empresa(id),
            lei TEXT,
            nombre_legal TEXT,
            pais CHAR(2),
            estado TEXT NOT NULL DEFAULT 'active',
            vigencia_desde DATE,
            vigencia_hasta DATE,
            vlei_status TEXT,
            vlei_cred_url TEXT,
            fuente_ref TEXT,
            created_at TIMESTAMPTZ DEFAULT now(),
            UNIQUE (empresa_id, lei)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_entity_identifiers_lei
            ON entity_identifiers(lei)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_entity_identifiers_lei_trgm
            ON entity_identifiers USING gin (lei gin_trgm_ops)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_entity_identifiers_empresa
            ON entity_identifiers(empresa_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_entity_identifiers_estado
            ON entity_identifiers(estado)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_entity_identifiers_pais
            ON entity_identifiers(pais)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_entity_identifiers_legal_trgm
            ON entity_identifiers USING gin (nombre_legal gin_trgm_ops)
        """
    )

    # entity_aliases: normalized aliases and legal name variants for entity matching
    op.execute(
        """
        CREATE TABLE entity_aliases (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL REFERENCES empresa(id),
            alias TEXT NOT NULL,
            alias_normalizado TEXT NOT NULL,
            fuente TEXT NOT NULL,
            confianza NUMERIC(3,2) NOT NULL DEFAULT 0.0,
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_entity_aliases_empresa
            ON entity_aliases(empresa_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_entity_aliases_alias_trgm
            ON entity_aliases USING gin (alias gin_trgm_ops)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_entity_aliases_normalizado_trgm
            ON entity_aliases USING gin (alias_normalizado gin_trgm_ops)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_entity_aliases_fuente
            ON entity_aliases(fuente)
        """
    )


def downgrade() -> None:
    op.drop_table("entity_aliases")
    op.drop_table("entity_identifiers")
