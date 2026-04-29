"""add durable AI governance persistence tables

# Revision ID: 20260426_0030_ai_governance_persistence
# Revises: 20260426_0029_international_obligations
# Create Date: 2026-04-26 00:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260426_0030_ai_governance_persistence"
down_revision = "20260426_0029_international_obligations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_audit_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("request_id", sa.Text(), nullable=False, server_default=""),
        sa.Column("timestamp", sa.Text(), nullable=False),
        sa.Column("componente", sa.Text(), nullable=False),
        sa.Column("accion", sa.Text(), nullable=False),
        sa.Column("configuracion", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("resultado_resumen", sa.Text(), nullable=False, server_default=""),
        sa.Column("latencia_ms", sa.Float(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("user_id", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.Text(), nullable=True),
    )
    op.create_index("idx_ai_audit_request", "ai_audit_log", ["request_id"])
    op.create_index("idx_ai_audit_component", "ai_audit_log", ["componente"])
    op.create_index("idx_ai_audit_timestamp", "ai_audit_log", ["timestamp"])

    op.create_table(
        "data_lineage",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("entry_id", sa.Text(), nullable=False, unique=True),
        sa.Column("tabla", sa.Text(), nullable=False),
        sa.Column("campo", sa.Text(), nullable=False),
        sa.Column("fuente_origen", sa.Text(), nullable=False),
        sa.Column("transformacion", sa.Text(), nullable=False, server_default=""),
        sa.Column("fecha_ingestion", sa.Text(), nullable=False),
        sa.Column("worker_correspondiente", sa.Text(), nullable=False, server_default="unknown"),
        sa.Column("calidad_score", sa.Float(), nullable=False, server_default="100"),
        sa.Column("observaciones", sa.Text(), nullable=False, server_default=""),
    )
    op.create_index("idx_data_lineage_table", "data_lineage", ["tabla"])
    op.create_index("idx_data_lineage_table_field", "data_lineage", ["tabla", "campo"])

    op.create_table(
        "human_review",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("review_id", sa.Text(), nullable=False, unique=True),
        sa.Column("request_id", sa.Text(), nullable=False),
        sa.Column("decision_type", sa.Text(), nullable=False),
        sa.Column("ai_response_id", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("reviewer_id", sa.Text(), nullable=True),
        sa.Column("action", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("confidence_threshold", sa.Float(), nullable=False, server_default="0"),
        sa.Column("ai_confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("required_for", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("reviewed_at", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.create_index("idx_human_review_request", "human_review", ["request_id"])
    op.create_index("idx_human_review_status", "human_review", ["status"])

    op.create_table(
        "ai_model_registry",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("model_id", sa.Text(), nullable=False, unique=True),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("tipo", sa.Text(), nullable=False),
        sa.Column("proveedor", sa.Text(), nullable=False),
        sa.Column("hash_modelo", sa.Text(), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False, server_default=""),
        sa.Column("fecha_despliegue", sa.Text(), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("configuracion", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.create_index("idx_ai_model_tipo", "ai_model_registry", ["tipo"])
    op.create_index("idx_ai_model_activo", "ai_model_registry", ["activo"])

    op.create_table(
        "ai_config_version",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("version_id", sa.Text(), nullable=False, unique=True),
        sa.Column("hybrid_weight", sa.Float(), nullable=False),
        sa.Column("rrf_k", sa.Float(), nullable=False),
        sa.Column("limit_default", sa.Integer(), nullable=False),
        sa.Column("modo_review", sa.Text(), nullable=False),
        sa.Column("fecha_cambio", sa.Text(), nullable=False),
        sa.Column("cambiado_por", sa.Text(), nullable=False),
        sa.Column("configuracion_completa", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.create_index("idx_ai_config_fecha", "ai_config_version", ["fecha_cambio"])

    op.create_table(
        "query_audit_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("entry_id", sa.Text(), nullable=False, unique=True),
        sa.Column("request_id", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=True),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("retrieved_chunks", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("response_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("model_version", sa.Text(), nullable=True),
        sa.Column("config_version", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
    )
    op.create_index("idx_query_audit_request", "query_audit_log", ["request_id"])
    op.create_index("idx_query_audit_path", "query_audit_log", ["path"])
    op.create_index("idx_query_audit_created", "query_audit_log", ["created_at"])


def downgrade() -> None:
    op.drop_index("idx_query_audit_created", table_name="query_audit_log")
    op.drop_index("idx_query_audit_path", table_name="query_audit_log")
    op.drop_index("idx_query_audit_request", table_name="query_audit_log")
    op.drop_table("query_audit_log")
    op.drop_index("idx_ai_config_fecha", table_name="ai_config_version")
    op.drop_table("ai_config_version")
    op.drop_index("idx_ai_model_activo", table_name="ai_model_registry")
    op.drop_index("idx_ai_model_tipo", table_name="ai_model_registry")
    op.drop_table("ai_model_registry")
    op.drop_index("idx_human_review_status", table_name="human_review")
    op.drop_index("idx_human_review_request", table_name="human_review")
    op.drop_table("human_review")
    op.drop_index("idx_data_lineage_table_field", table_name="data_lineage")
    op.drop_index("idx_data_lineage_table", table_name="data_lineage")
    op.drop_table("data_lineage")
    op.drop_index("idx_ai_audit_timestamp", table_name="ai_audit_log")
    op.drop_index("idx_ai_audit_component", table_name="ai_audit_log")
    op.drop_index("idx_ai_audit_request", table_name="ai_audit_log")
    op.drop_table("ai_audit_log")
