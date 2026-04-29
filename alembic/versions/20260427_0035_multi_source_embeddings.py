"""add vector embedding columns and indices for multi-source retrieval

- pgc_cuenta: vector embedding for codigo + descripcion + grupo + nota
- aeat_modelo: vector embedding for codigo + nombre + impuesto
- screening_entries: vector embedding for nombre + aliases + categorias + descripcion
- empresa: vector embedding for nombre + nif
- norma: vector embedding for codigo + nombre + numero_boe + titulo
- articulo: vector embedding for numero + contenido + titulo

# Revision ID: 20260427_0035_multi_source_embeddings
# Revises: 20260427_0034_embedding_versioning
# Create Date: 2026-04-27 00:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260427_0035_multi_source_embeddings"
down_revision = "20260427_0034_embedding_versioning"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"

    def _add_vector_col(table, col="embedding_384"):
        if is_pg:
            op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} vector(384)")
        else:
            op.add_column(table, sa.Column(col, sa.dialects.postgresql.ARRAY(sa.Float()), nullable=True))

    # --- pgc_cuenta: embedding for accounting chart of accounts search ---
    _add_vector_col("pgc_cuenta")
    op.execute("""ALTER TABLE pgc_cuenta ADD COLUMN IF NOT EXISTS embedding_model_name TEXT""")
    op.execute("""ALTER TABLE pgc_cuenta ADD COLUMN IF NOT EXISTS content_hash TEXT""")
    if is_pg:
        op.execute("""
            CREATE INDEX IF NOT EXISTS idx_pgc_cuenta_embedding ON pgc_cuenta
            USING hnsw (embedding_384 vector_l2_ops)
            WITH (m=16, ef_construction=64)
        """)

    # --- aeat_modelo: embedding for tax form search ---
    _add_vector_col("aeat_modelo")
    op.execute("""ALTER TABLE aeat_modelo ADD COLUMN IF NOT EXISTS embedding_model_name TEXT""")
    op.execute("""ALTER TABLE aeat_modelo ADD COLUMN IF NOT EXISTS content_hash TEXT""")
    if is_pg:
        op.execute("""
            CREATE INDEX IF NOT EXISTS idx_aeat_modelo_embedding ON aeat_modelo
            USING hnsw (embedding_384 vector_l2_ops)
            WITH (m=16, ef_construction=64)
        """)

    # --- screening_entries: embedding for sanctions/PEP search ---
    _add_vector_col("screening_entries")
    op.execute("""ALTER TABLE screening_entries ADD COLUMN IF NOT EXISTS embedding_model_name TEXT""")
    op.execute("""ALTER TABLE screening_entries ADD COLUMN IF NOT EXISTS content_hash TEXT""")
    if is_pg:
        op.execute("""
            CREATE INDEX IF NOT EXISTS idx_screening_entries_embedding ON screening_entries
            USING hnsw (embedding_384 vector_l2_ops)
            WITH (m=16, ef_construction=64)
        """)

    # --- empresa: embedding for entity resolution ---
    _add_vector_col("empresa")
    op.execute("""ALTER TABLE empresa ADD COLUMN IF NOT EXISTS embedding_model_name TEXT""")
    op.execute("""ALTER TABLE empresa ADD COLUMN IF NOT EXISTS content_hash TEXT""")
    if is_pg:
        op.execute("""
            CREATE INDEX IF NOT EXISTS idx_empresa_embedding ON empresa
            USING hnsw (embedding_384 vector_l2_ops)
            WITH (m=16, ef_construction=64)
        """)

    # --- norma: embedding for BOE law search ---
    _add_vector_col("norma")
    op.execute("""ALTER TABLE norma ADD COLUMN IF NOT EXISTS embedding_model_name TEXT""")
    op.execute("""ALTER TABLE norma ADD COLUMN IF NOT EXISTS content_hash TEXT""")
    if is_pg:
        op.execute("""
            CREATE INDEX IF NOT EXISTS idx_norma_embedding ON norma
            USING hnsw (embedding_384 vector_l2_ops)
            WITH (m=16, ef_construction=64)
        """)

    # --- articulo: embedding for legal article search ---
    _add_vector_col("articulo")
    op.execute("""ALTER TABLE articulo ADD COLUMN IF NOT EXISTS embedding_model_name TEXT""")
    op.execute("""ALTER TABLE articulo ADD COLUMN IF NOT EXISTS content_hash TEXT""")
    if is_pg:
        op.execute("""
            CREATE INDEX IF NOT EXISTS idx_articulo_embedding ON articulo
            USING hnsw (embedding_384 vector_l2_ops)
            WITH (m=16, ef_construction=64)
        """)


def downgrade() -> None:
    op.drop_index("idx_articulo_embedding", table_name="articulo")
    op.drop_column("articulo", "content_hash")
    op.drop_column("articulo", "embedding_model_name")
    op.drop_column("articulo", "embedding_384")

    op.drop_index("idx_norma_embedding", table_name="norma")
    op.drop_column("norma", "content_hash")
    op.drop_column("norma", "embedding_model_name")
    op.drop_column("norma", "embedding_384")

    op.drop_index("idx_empresa_embedding", table_name="empresa")
    op.drop_column("empresa", "content_hash")
    op.drop_column("empresa", "embedding_model_name")
    op.drop_column("empresa", "embedding_384")

    op.drop_index("idx_screening_entries_embedding", table_name="screening_entries")
    op.drop_column("screening_entries", "content_hash")
    op.drop_column("screening_entries", "embedding_model_name")
    op.drop_column("screening_entries", "embedding_384")

    op.drop_index("idx_aeat_modelo_embedding", table_name="aeat_modelo")
    op.drop_column("aeat_modelo", "content_hash")
    op.drop_column("aeat_modelo", "embedding_model_name")
    op.drop_column("aeat_modelo", "embedding_384")

    op.drop_index("idx_pgc_cuenta_embedding", table_name="pgc_cuenta")
    op.drop_column("pgc_cuenta", "content_hash")
    op.drop_column("pgc_cuenta", "embedding_model_name")
    op.drop_column("pgc_cuenta", "embedding_384")


def _is_pg(bind):
    try:
        return bind.dialect.name == "postgresql"
    except Exception:
        return False
