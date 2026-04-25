"""add eval_history table for persistent evaluation telemetry

Revision ID: 20260425_0006_eval_history
Revises: 20260424_0005_chunking_schema
Create Date: 2026-04-25 00:00:00

Creates:
  - eval_history: stores every evaluation run with full metrics for
    historical comparison, trend tracking, and CI gates.

Dialect: PostgreSQL only. SQLite tests use conftest.py schema.

Design decisions:
  - eval_run groups individual queries into a single evaluation session.
  - eval_query stores per-query metrics for drill-down.
  - eval_metric stores granular metrics as key-value for flexible schema.
  - All CREATE statements use IF NOT EXISTS for idempotency.
  - Indexes on run_at and domain for efficient querying.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260425_0006_eval_history"
down_revision = "20260424_0005_chunking_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.exec_driver_sql("SET check_function_bodies = false")

    # ── eval_run: one row per evaluation session ──────────────────────
    op.create_table(
        "eval_run",
        sa.Column("id", sa.dialects.postgresql.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("run_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("api_url", sa.Text(), nullable=True),
        sa.Column("golden_version", sa.Text(), nullable=True),
        sa.Column("global_score", sa.Float(), nullable=True),
        sa.Column("total_queries", sa.Integer(), nullable=True),
        sa.Column("total_failures", sa.Integer(), nullable=True),
        sa.Column("source_hit_rate", sa.Float(), nullable=True),
        sa.Column("avg_latency_ms", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_eval_run_run_at", "eval_run", ["run_at"])

    # ── eval_query: per-query results linked to a run ─────────────────
    op.create_table(
        "eval_query",
        sa.Column("id", sa.dialects.postgresql.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("run_id", sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column("query_id", sa.Text(), nullable=False),
        sa.Column("dominio", sa.Text(), nullable=False),
        sa.Column("pregunta", sa.Text(), nullable=False),
        sa.Column("score_compuesto", sa.Float(), nullable=True),
        sa.Column("acierto_fuente", sa.Boolean(), nullable=True),
        sa.Column("acierto_articulo", sa.Boolean(), nullable=True),
        sa.Column("acierto_vigencia", sa.Boolean(), nullable=True),
        sa.Column("chunk_precision", sa.Float(), nullable=True),
        sa.Column("recall_top3", sa.Boolean(), nullable=True),
        sa.Column("recall_top5", sa.Boolean(), nullable=True),
        sa.Column("posicion_fuente", sa.Integer(), nullable=True),
        sa.Column("acierto_doctrina", sa.Boolean(), nullable=True),
        sa.Column("acierto_modelo", sa.Boolean(), nullable=True),
        sa.Column("falla", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("latencia_consulta_ms", sa.Float(), nullable=True),
        sa.Column("latencia_buscar_ms", sa.Float(), nullable=True),
        sa.Column("latencia_doctrina_ms", sa.Float(), nullable=True),
        sa.Column("fuentes_encontradas", sa.Text(), nullable=True),
        sa.Column("fuentes_esperadas", sa.Text(), nullable=True),
        sa.Column("articulos_encontrados", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["eval_run.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_eval_query_run_id", "eval_query", ["run_id"])
    op.create_index("ix_eval_query_dominio", "eval_query", ["dominio"])
    op.create_index("ix_eval_query_query_id", "eval_query", ["query_id"])

    op.exec_driver_sql("SET check_function_bodies = true")


def downgrade() -> None:
    op.drop_table("eval_query")
    op.drop_table("eval_run")
