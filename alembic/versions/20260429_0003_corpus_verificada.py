"""add fuente_verificada column to editorial corpus tables

Enforces Corpus Autoritativo rule (AGENTS.md #17): no LLM text
becomes authoritative without human verification.

- fuente_verificada (boolean, default false): set to true only by
  human-approved workflow. LLM-generated content starts as unverified.
- CHECK constraint (Postgres only): fuente_oficial_referencia NOT NULL
  when estado IN ('vigente', 'revisar').

# Revision ID: 20260429_0003_corpus_verificada
# Revises: 20260429_0002_revoke_function_execute
# Create Date: 2026-04-29 00:00:00

"""

from alembic import op
import sqlalchemy as sa

revision = "20260429_0003_corpus_verificada"
down_revision = "20260429_0002_revoke_function_execute"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    dialect_name = inspector.engine.dialect.name

    # nota_editorial_interna
    op.add_column(
        "nota_editorial_interna",
        sa.Column(
            "fuente_verificada",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="True si un humano verifico la fuente oficial",
        ),
    )

    # CHECK constraints only on Postgres (SQLite doesn't support them)
    if dialect_name == "postgresql":
        op.execute(
            """
            ALTER TABLE nota_editorial_interna
            ADD CONSTRAINT chk_nota_fuente_required
            CHECK (
                (estado NOT IN ('vigente', 'revisar'))
                OR (fuente_oficial_referencia IS NOT NULL AND fuente_oficial_referencia != '')
            )
            """
        )

    # posicion_interpretativa
    op.add_column(
        "posicion_interpretativa",
        sa.Column(
            "fuente_verificada",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="True si un humano verifico la fuente oficial",
        ),
    )

    if dialect_name == "postgresql":
        op.execute(
            """
            ALTER TABLE posicion_interpretativa
            ADD CONSTRAINT chk_posicion_fuente_required
            CHECK (
                (estado NOT IN ('vigente', 'revisar'))
                OR (fuente_oficial_referencia IS NOT NULL AND fuente_oficial_referencia != '')
            )
            """
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    dialect_name = inspector.engine.dialect.name

    op.drop_constraint(
        "chk_nota_fuente_required",
        "nota_editorial_interna",
        type_="check",
    )
    op.drop_column("nota_editorial_interna", "fuente_verificada")

    op.drop_constraint(
        "chk_posicion_fuente_required",
        "posicion_interpretativa",
        type_="check",
    )
    op.drop_column("posicion_interpretativa", "fuente_verificada")
