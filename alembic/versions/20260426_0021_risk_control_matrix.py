"""Alembic migration — Fase 22: matriz de controles, riesgos y pruebas.

Crea:
- riesgo_regulatorio: riesgos vinculados a obligaciones regulatorias
- control_interno: controles que mitigan riesgos
- riesgo_control_link: mapping riesgo -> control con estado y frecuencia
- prueba_control: evidencias de pruebas/ejecucion de controles

No elimina ni modifica tablas existentes.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260426_0021_risk_control_matrix"
down_revision: str | None = "20260426_0020_linea_criterio_ambitos"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- riesgo_regulatorio ---
    op.create_table(
        "riesgo_regulatorio",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("codigo", sa.Text(), nullable=False),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("obligacion_codigo", sa.Text(), nullable=True),
        sa.Column("categoria", sa.Text(), nullable=True),
        sa.Column("severidad", sa.Text(), nullable=True, default="media"),
        sa.Column("probabilidad", sa.Text(), nullable=True, default="media"),
        sa.Column("riesgo_inherente", sa.Text(), nullable=True, default="media"),
        sa.Column("area_responsable", sa.Text(), nullable=True),
        sa.Column("owner_rol", sa.Text(), nullable=True),
        sa.Column("estado", sa.Text(), nullable=False, default="identificado"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_riesgo_regulatorio_codigo", "codigo"),
        sa.Index("ix_riesgo_regulatorio_obligacion", "obligacion_codigo"),
        sa.Index("ix_riesgo_regulatorio_estado", "estado"),
        sa.Index("ix_riesgo_regulatorio_severidad", "severidad"),
        sa.Index("ix_riesgo_regulatorio_nombre_trgm", "nombre", postgresql_ops={"nombre": "gin_trgm_ops"}),
    )

    # --- control_interno ---
    op.create_table(
        "control_interno",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("codigo", sa.Text(), nullable=False),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("tipo_control", sa.Text(), nullable=True, default="preventivo"),
        sa.Column("frecuencia", sa.Text(), nullable=True),
        sa.Column("owner_rol", sa.Text(), nullable=True),
        sa.Column("sistema_apoyo", sa.Text(), nullable=True),
        sa.Column("estado", sa.Text(), nullable=False, default="activo"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_control_interno_codigo", "codigo"),
        sa.Index("ix_control_interno_estado", "estado"),
        sa.Index("ix_control_interno_nombre_trgm", "nombre", postgresql_ops={"nombre": "gin_trgm_ops"}),
    )

    # --- riesgo_control_link (mapping riesgo -> control) ---
    op.create_table(
        "riesgo_control_link",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("riesgo_id", sa.Integer(), sa.ForeignKey("riesgo_regulatorio.id", ondelete="CASCADE"), nullable=False),
        sa.Column("control_id", sa.Integer(), sa.ForeignKey("control_interno.id", ondelete="CASCADE"), nullable=False),
        sa.Column("efectividad", sa.Text(), nullable=True, default="no_evaluada"),
        sa.Column("riesgo_residual", sa.Text(), nullable=True, default="no_evaluada"),
        sa.Column("frecuencia_prueba", sa.Text(), nullable=True),
        sa.Column("criterio_suficiencia", sa.Text(), nullable=True),
        sa.Column("caducidad_dias", sa.Integer(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_riesgo_control_link_riesgo", "riesgo_id"),
        sa.Index("ix_riesgo_control_link_control", "control_id"),
        sa.UniqueConstraint("riesgo_id", "control_id", name="uq_riesgo_control_link"),
    )

    # --- prueba_control (evidencia de prueba/ejecucion de control) ---
    op.create_table(
        "prueba_control",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("link_id", sa.Integer(), sa.ForeignKey("riesgo_control_link.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fecha_prueba", sa.Date(), nullable=False),
        sa.Column("resultado", sa.Text(), nullable=False),
        sa.Column("evidencia_descripcion", sa.Text(), nullable=True),
        sa.Column("evidencia_url", sa.Text(), nullable=True),
        sa.Column("ejecutado_por", sa.Text(), nullable=True),
        sa.Column("nota", sa.Text(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_prueba_control_link", "link_id"),
        sa.Index("ix_prueba_control_fecha", "fecha_prueba"),
        sa.Index("ix_prueba_control_resultado", "resultado"),
    )

    # --- Seed data ---
    op.execute(
        """
        INSERT INTO riesgo_regulatorio (codigo, nombre, descripcion, obligacion_codigo,
            categoria, severidad, probabilidad, riesgo_inherente, area_responsable,
            owner_rol, estado)
        VALUES
        ('RIESGO-CNMV-001', 'No presentacion de informes CNMV',
         'Incumplimiento de obligaciones de informacion periodica ante la CNMV',
         'CNMV-IR-RESERVADA', 'reporting', 'alta', 'media', 'alto',
         'compliance', 'compliance_officer', 'identificado'),
        ('RIESGO-CNMV-002', 'Informacion inexacta o incompleta',
         'Presentacion de datos erroneos ante regulador',
         'CNMV-IR-RESERVADA', 'calidad_datos', 'alta', 'baja', 'medio',
         'finanzas', 'cfo', 'identificado'),
        ('RIESGO-MIFID-001', 'Incumplimiento MiFID adecuacion cliente',
         'No evaluar adecuadamente la adecuacion y conveniencia de productos para clientes',
         'MICRO-MIFID-001', 'mifid', 'alta', 'media', 'alto',
         'compliance', 'compliance_officer', 'identificado'),
        ('RIESGO-PBCFT-001', 'Incumplimiento prevencion blanqueo',
         'No aplicar debida diligencia KYC o no reportar operaciones sospechosas a SEPBLAC',
         'MICRO-PBCFT-001', 'pbcft', 'critica', 'media', 'alto',
         'compliance', 'mlco', 'identificado'),
        ('RIESGO-IVA-001', 'Retraso en presentacion modelo 303',
         'Multa por presentacion fuera de plazo del IVA',
         'OBL-IVA-303', 'fiscal', 'media', 'baja', 'medio',
         'finanzas', 'responsable_fiscal', 'identificado')
        """
    )

    op.execute(
        """
        INSERT INTO control_interno (codigo, nombre, descripcion, tipo_control,
            frecuencia, owner_rol, sistema_apoyo, estado)
        VALUES
        ('CTRL-REPOR-001', 'Revision quincenal datos CNMV',
         'Revisar y validar datos antes de envio a CNMV',
         'preventivo', 'quincenal', 'compliance', 'esdata', 'activo'),
        ('CTRL-REPOR-002', 'Doble firma informes periodicos',
         'Dos personas revisan y firman antes de envio',
         'detectivo', 'por_envio', 'finanzas', 'esdata', 'activo'),
        ('CTRL-MIFID-001', 'Checklist adecuacion MiFID',
         'Checklist obligatorio antes de recomendar producto',
         'preventivo', 'por_operacion', 'compliance', 'esdata', 'activo'),
        ('CTRL-KYC-001', 'Debida diligencia cliente nuevo',
         'KYC completo y aprobacion antes de relacion comercial',
         'preventivo', 'por_onboarding', 'compliance', 'esdata', 'activo'),
        ('CTRL-FISCAL-001', 'Calendario presentaciones fiscales',
         'Alertas automatizadas de plazos fiscales en esdata',
         'preventivo', 'mensual', 'finanzas', 'esdata', 'activo')
        """
    )

    op.execute(
        """
        INSERT INTO riesgo_control_link (riesgo_id, control_id, efectividad,
            riesgo_residual, frecuencia_prueba, criterio_suficiencia, caducidad_dias, activo)
        SELECT r.id, c.id, 'no_evaluada', 'no_evaluada', 'trimestral',
               'evidencia documentada por prueba', 90, true
        FROM riesgo_regulatorio r, control_interno c
        WHERE r.codigo = 'RIESGO-CNMV-001' AND c.codigo = 'CTRL-REPOR-001'
        UNION ALL
        SELECT r.id, c.id, 'no_evaluada', 'no_evaluada', 'trimestral',
               'evidencia documentada por prueba', 90, true
        FROM riesgo_regulatorio r, control_interno c
        WHERE r.codigo = 'RIESGO-CNMV-001' AND c.codigo = 'CTRL-REPOR-002'
        UNION ALL
        SELECT r.id, c.id, 'no_evaluada', 'no_evaluada', 'mensual',
               'evidencia documentada por prueba', 30, true
        FROM riesgo_regulatorio r, control_interno c
        WHERE r.codigo = 'RIESGO-MIFID-001' AND c.codigo = 'CTRL-MIFID-001'
        UNION ALL
        SELECT r.id, c.id, 'no_evaluada', 'no_evaluada', 'por_onboarding',
               'evidencia documentada por prueba', 180, true
        FROM riesgo_regulatorio r, control_interno c
        WHERE r.codigo = 'RIESGO-PBCFT-001' AND c.codigo = 'CTRL-KYC-001'
        UNION ALL
        SELECT r.id, c.id, 'no_evaluada', 'no_evaluada', 'mensual',
               'evidencia documentada por prueba', 30, true
        FROM riesgo_regulatorio r, control_interno c
        WHERE r.codigo = 'RIESGO-IVA-001' AND c.codigo = 'CTRL-FISCAL-001'
        """
    )


def downgrade() -> None:
    op.drop_table("prueba_control")
    op.drop_table("riesgo_control_link")
    op.drop_table("control_interno")
    op.drop_table("riesgo_regulatorio")
