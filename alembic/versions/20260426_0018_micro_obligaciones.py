"""Alembic migration — Fase 20: micro-obligaciones MiFID/CNMV/SEPBLAC.

Crea:
- micro_obligacion: taxonomia de micro-obligaciones operativas
- obligacion_micro_obligacion: mapeo N:M obligacion_regulatoria -> micro_obligacion

No elimina ni modifica tablas existentes.
"""

import sqlalchemy as sa

from alembic import op

revision = "20260426_0018_micro_obligaciones"
down_revision = "20260426_0017_playbooks_evidencia"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "micro_obligacion",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("codigo", sa.Text(), nullable=False, unique=True),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("regulacion_relacionada", sa.Text(), nullable=False),
        sa.Column("ambito", sa.Text(), nullable=False),
        sa.Column("trigger_evento", sa.Text(), nullable=True),
        sa.Column("frecuencia", sa.Text(), nullable=True),
        sa.Column("owner_rol", sa.Text(), nullable=True),
        sa.Column("severidad", sa.Text(), nullable=True, server_default=sa.text("'media'::text")),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Index("ix_micro_obligacion_regulacion", "regulacion_relacionada"),
        sa.Index("ix_micro_obligacion_activo", "activo"),
    )

    op.create_table(
        "obligacion_micro_obligacion",
        sa.Column("obligacion_id", sa.Integer(), sa.ForeignKey("obligacion_regulatoria.id"), primary_key=True),
        sa.Column("micro_obligacion_id", sa.Integer(), sa.ForeignKey("micro_obligacion.id"), primary_key=True),
        sa.Column("orden", sa.Integer(), nullable=False, default=0),
        sa.Column("evidencia_requerida", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )

    # Seed MiFID II micro-obligaciones
    op.execute("""
        INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad, activo) VALUES
        ('MIFID_SUITABILITY', 'Evaluacion de adecuacion', 'Evaluar si el producto/inversion es adecuado al perfil del cliente (art. 53 LMCV)', 'mifid_ii', 'mercados', 'alta_satisfaccion', 'eventual', 'compliance', 'alta', true),
        ('MIFID_APPROPRIATENESS', 'Evaluacion de conveniencia', 'Evaluar conocimientos y experiencia del cliente (art. 54 LMCV)', 'mifid_ii', 'mercados', 'alta_satisfaccion', 'inicial', 'compliance', 'alta', true),
        ('MIFID_BEST_EXECUTION', 'Ejecucion preferente', 'Obtener resultado mejor posible para cliente (art. 61 LMCV)', 'mifid_ii', 'mercados', 'solicitud_ordenes', 'continua', 'trading', 'alta', true),
        ('MIFID_CONFLICTS', 'Gestion de conflictos de interes', 'Identificar y gestionar conflictos de interes (art. 59 LMCV)', 'mifid_ii', 'mercados', 'continuo', 'continua', 'compliance', 'alta', true),
        ('MIFID_INDUCEMENTS', 'Inducimientos', 'Registrar y gestionar inducements (art. 63 LMCV)', 'mifid_ii', 'mercados', 'recepcion_inducement', 'continua', 'compliance', 'media', true),
        ('MIFID_PRODUCT_GOVERNANCE', 'Gobierno de productos', 'Diseñar y distribuir productos con alcance destino (art. 98 LMCV)', 'mifid_ii', 'mercados', 'diseno_producto', 'continua', 'producto', 'alta', true),
        ('MIFIR_REPORTING', 'Reporte MiFIR', 'Reportar operaciones transaccion en tiempo real (Reg. 1287/2014)', 'mifir', 'mercados', 'ejecucion_orden', 'en_tiempo_real', 'reporting', 'alta', true),
        ('MIFID_INSIDER_LIST', 'Listas de inside', 'Crear y mantener listas de personas con informacion privilegiada (art. 66 LMCV)', 'mifid_ii', 'mercados', 'acceso_info_privilegiada', 'continua', 'compliance', 'alta', true),
        ('MIFID_ORDER_RECORD', 'Registro de ordenes', 'Registrar y archivar ordenes (art. 23 RDM)', 'mifid_ii', 'mercados', 'ejecucion_orden', 'continua', 'operaciones', 'media', true),
        ('MIFID_CLIENT_CATEGORIES', 'Categorias de cliente', 'Clasificar cliente como minorista/profesional/institucional (art. 52 LMCV)', 'mifid_ii', 'mercados', 'alta_satisfaccion', 'inicial', 'compliance', 'alta', true),
        ('MIFID_COMPENSATION', 'Politica de compensacion', 'Implementar politica de compensacion alineada con riesgos (art. 95 LMCV)', 'mifid_ii', 'mercados', 'continuo', 'anual', 'rrhh', 'media', true),
        ('MIFID_MARKET_ABUSE', 'Deteccion abuso mercado', 'Detectar y reportar operaciones sospechosas de abuso (art. 13 MAR)', 'mar', 'mercados', 'operacion_sospechosa', 'continua', 'compliance', 'alta', true)
        ON CONFLICT DO NOTHING
    """)

    # Seed CNMV micro-obligaciones
    op.execute("""
        INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad, activo) VALUES
        ('CNMV_REPORTING_RESERVADO', 'Reporting reservado CNMV', 'Comunicaciones confidenciales a CNMV (Disp Adic 4 LMCV)', 'cnmv_lmcv', 'reporting_regulatorio', 'cambios_internos', 'eventual', 'secretaria', 'alta', true),
        ('CNMV_TRANSPARENCIA', 'Transparencia emisores', 'Publicar informacionperiodica de emisores (RDM)', 'cnmv_lmcv', 'reporting_regulatorio', 'periodicidad', 'trimestral', 'comercial', 'alta', true),
        ('CNMV_GOBIERNO_CORP', 'Gobierno corporativo', 'Cumplir Codigo de Buen Gobierno (recomendaciones)', 'cnmv_lmcv', 'reporting_regulatorio', 'periodicidad', 'anual', 'consejo', 'media', true),
        ('CNMV_OPS_INSTRUMENTOS_PROPIOS', 'Ops con instrumentos propios', 'Cumplir restricciones operaciones con instrumentos propios (art. 116 TRLC)', 'cnmv_lmcv', 'mercados', 'ejecucion_orden', 'continua', 'trading', 'alta', true),
        ('CNMV_COMUNICACION_HECHOS_ESenciales', 'Comunicacion hechos relevantes', 'Comunicacion hechos relevantes en tiempo real (art. 1 RDM)', 'cnmv_lmcv', 'reporting_regulatorio', 'hecho_relevante', 'eventual', 'secretaria', 'alta', true),
        ('CNMV_REGISTRO_OPERACIONES_INSIDER', 'Registro operaciones insider', 'Registrar operaciones de PPI (art. 19 MAR)', 'mar', 'mercados', 'operacion_ppi', 'eventual', 'compliance', 'alta', true),
        ('CNMV_CONCILIACION', 'Conciliacion financiera', 'Conciliacion periodica carteras clientes', 'cnmv_lmcv', 'reporting_regulatorio', 'periodicidad', 'mensual', 'back_office', 'media', true),
        ('CNMV_DOCUMENTOS_INFORMACION', 'Documentos de informacion', 'Elaborar y publicar DI (art. 10 RDM)', 'cnmv_lmcv', 'reporting_regulatorio', 'periodicidad', 'continua', 'comercial', 'alta', true)
        ON CONFLICT DO NOTHING
    """)

    # Seed SEPBLAC micro-obligaciones
    op.execute("""
        INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad, activo) VALUES
        ('SEPBLAC_KYC', 'Deber de diligencia debida', 'Identificacion y verificacion cliente (RD 289/2022 art. 19)', 'pblcft', 'aml_cft', 'onboarding', 'inicial', 'compliance', 'alta', true),
        ('SEPBLAC_MONITORING', 'Monitorizacion continua', 'Monitorizacion continua de operaciones (RD 289/2022 art. 27)', 'pblcft', 'aml_cft', 'operacion', 'continua', 'compliance', 'alta', true),
        ('SEPBLAC_STR', 'Comunicacion de indicios STR', 'Comunicar indicios de LP a SEPBLAC (art. 59 Ley 10/2010)', 'pblcft', 'aml_cft', 'indicio_lp', 'eventual', 'compliance', 'alta', true),
        ('SEPBLAC_SUSPENSION', 'Suspension operacion', 'Suspender operacion si riesgo LP no mitigado (RD 289/2022 art. 23)', 'pblcft', 'aml_cft', 'riesgo_no_mitigado', 'eventual', 'compliance', 'alta', true),
        ('SEPBLAC_PEP_SCREENING', 'Screening PEP', 'Verificar PEP en onboarding y periodicamente (RD 289/2022 art. 25)', 'pblcft', 'aml_cft', 'onboarding', 'inicial', 'compliance', 'alta', true),
        ('SEPBLAC_RECORD_KEEPING', 'Conservacion documentos', 'Conservar documentos identificacion 6 anos (RD 289/2022 art. 42)', 'pblcft', 'aml_cft', 'continuo', 'continua', 'compliance', 'media', true),
        ('SEPBLAC_FORMACION', 'Formacion AML', 'Formacion empleados prevencion LP (art. 7 Ley 10/2010)', 'pblcft', 'aml_cft', 'continuo', 'anual', 'rrhh', 'media', true),
        ('SEPBLAC_GOBIERNO_AML', 'Gobierno AML interno', 'Implementar controles internos prevencion LP (art. 6 Ley 10/2010)', 'pblcft', 'aml_cft', 'continuo', 'continua', 'compliance', 'alta', true),
        ('SEPBLAC_MITIGACION', 'Politica mitigacion riesgos', 'Politica de mitigacion de riesgos LP (art. 5 Ley 10/2010)', 'pblcft', 'aml_cft', 'continuo', 'anual', 'compliance', 'alta', true),
        ('SEPBLAC_REPORTE_ANUAL', 'Reporte anual SEPBLAC', 'Presentar memoria anual de actividades (si aplica)', 'pblcft', 'aml_cft', 'periodicidad', 'anual', 'compliance', 'media', true)
        ON CONFLICT DO NOTHING
    """)

    # Seed mapping: obligacion_regulatoria -> micro_obligacion
    # Mapear por fuente y ambito
    op.execute("""
        INSERT INTO obligacion_micro_obligacion (obligacion_id, micro_obligacion_id, orden, evidencia_requerida)
        SELECT o.id, m.id, 0, NULL
        FROM obligacion_regulatoria o, micro_obligacion m
        WHERE (o.fuente = 'cnmv' AND m.regulacion_relacionada IN ('cnmv_lmcv', 'mar'))
           OR (o.fuente = 'sepblac' AND m.regulacion_relacionada = 'pblcft')
           OR (o.fuente = 'boe' AND m.regulacion_relacionada IN ('mifid_ii', 'mifir', 'mar'))
        ON CONFLICT DO NOTHING
    """)


def downgrade():
    op.drop_table("obligacion_micro_obligacion")
    op.drop_table("micro_obligacion")
