"""Alembic migration — expansion micro-obligaciones: LECR, SOCIMI, CSDR, CNMV ECR, Doctrina DGT.

Agrega 22 micro-obligaciones nuevas:
- LECR (Ley 22/2014): 6 micro-obligaciones (ECR registration, SGEIC, diversificacion, MiID, conducta, fiscal)
- SOCIMI (Ley 11/2009): 5 micro-obligaciones (activo, distribucion, gravamen, regimen, regla 80/20)
- CSDR (Reglamento 909/2014): 3 micro-obligaciones (settlement T+2/T+1, reporting, fallidos)
- CNMV ECR: 4 micro-obligaciones (reporting estados reservados, XML, listado activo, FAQs)
- Doctrina DGT: 4 micro-obligaciones (gravamenes SOCIMI, distribucion SOCIMI, ETI emisores, exenciones FCR/SCR)

Agrega mapeos N:M para nuevas regulaciones: lecr, socimi, csdr, cnmv_ecr, doctrina_dgt.

No modifica estructura de tablas existentes.
"""

import sqlalchemy as sa

from alembic import op

revision = "20260426_0022_micro_obligaciones_expansion"
down_revision = "20260426_0021_risk_control_matrix"
branch_labels = None
depends_on = None


def upgrade():
    # Seed LECR micro-obligaciones
    op.execute("""
        INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad, activo) VALUES
        ('LECR_ECR_REGISTRATION', 'Registro en ECR', 'Registro en el Registro Central de Representantes de ECR (Ley 22/2014 arts. 1-12)', 'lecr', 'ecr_regulatorio', 'constitucion', 'eventual', 'compliance', 'alta', true),
        ('LECR_SGEIC', 'Autorizacion SGEIC / Autogestion', 'Autorizacion como SGEIC opcional (art. 26 LECR) o contratar SGEIC externo', 'lecr', 'ecr_regulatorio', 'constitucion', 'eventual', 'compliance', 'alta', true),
        ('LECR_DIVERSIFICATION', 'Diversificacion >=50% no cotizados', 'Diversificacion de posiciones: >=50% empresas no cotizadas (art. 26 LECR)', 'lecr', 'ecr_regulatorio', 'periodicidad', 'trimestral', 'compliance', 'alta', true),
        ('LECR_MIID_DIVERSIFICATION', 'Diversificacion MiID >=50%', 'Diversificacion MiID (art. 134 LECR) para fondos de inversion', 'lecr', 'ecr_regulatorio', 'periodicidad', 'trimestral', 'compliance', 'alta', true),
        ('LECR_CONDUCT_RULES', 'Reglas de conducta MiFID II', 'Cumplir reglas de conducta MiFID II (arts. 53-63 LMCV) como ECR', 'lecr', 'ecr_regulatorio', 'continuo', 'continua', 'compliance', 'alta', true),
        ('LECR_FISCAL_NON_RESIDENT', '95% exencion dividendos no residentes', 'Exencion 95% dividendos y plusvalias para no residentes (art. 21 Ley IS + art. 30 Ley 22/2014)', 'lecr', 'tributario', 'periodicidad', 'anual', 'finanzas', 'media', true)
        ON CONFLICT DO NOTHING
    """)

    # Seed SOCIMI micro-obligaciones
    op.execute("""
        INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad, activo) VALUES
        ('SOCIMI_ASSET_COMPOSITION', '>=80% activos inmobiliarios arrendados', 'Mantener >=80% del valor del activo en inmuebles arrendados (art. 3 Ley 11/2009)', 'socimi', 'societario_fiscal', 'periodicidad', 'anual', 'finanzas', 'alta', true),
        ('SOCIMI_DISTRIBUTION', '>=80% distribucion de resultados', 'Distribuir >=80% de los resultados imponibles (art. 12 Ley 11/2009)', 'socimi', 'societario_fiscal', 'periodicidad', 'anual', 'finanzas', 'alta', true),
        ('SOCIMI_TAX_UNDISTRIBUTED', 'Gravamen 15-19% beneficios no distribuidos', 'Gravamen 15-19% sobre beneficios no distribuidos (art. 24 Ley 11/2009)', 'socimi', 'tributario', 'periodicidad', 'anual', 'finanzas', 'media', true),
        ('SOCIMI_TAX_REGIME', 'Regimen fiscal SOCIMI 0% IS', 'Aplicar regimen fiscal SOCIMI con tipo 0% si distribuye >=80% beneficios (art. 23 Ley 11/2009)', 'socimi', 'tributario', 'continuo', 'anual', 'finanzas', 'alta', true),
        ('SOCIMI_80_20_RULE', 'Regla 80/20 SOCIMI', '80% activo inmobiliario arrendado + 20% liquidez maxima (art. 3 Ley 11/2009)', 'socimi', 'societario_fiscal', 'periodicidad', 'anual', 'finanzas', 'alta', true)
        ON CONFLICT DO NOTHING
    """)

    # Seed CSDR micro-obligaciones
    op.execute("""
        INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad, activo) VALUES
        ('CSDR_SETTLEMENT', 'T+2 settlement / T+1 inminente', 'Cumplir T+2 settlement vigente, preparar T+1 (Reglamento 909/2014)', 'csdr', 'infraestructuras_csd', 'ejecucion_orden', 'continua', 'operaciones', 'alta', true),
        ('CSDR_REPORTING', 'Segregacion y reporting CSDR', 'Segregacion de posiciones y reporting a CSD (Reglamento 909/2014)', 'csdr', 'infraestructuras_csd', 'periodicidad', 'mensual', 'reporting', 'alta', true),
        ('CSDR_SETTLEMENT_FAILURE', 'Gestion fallidos de settlement CSDR', 'Gestion de fallidos de settlement y multas CSDR (Reglamento 909/2014)', 'csdr', 'infraestructuras_csd', 'fallido_settlement', 'eventual', 'operaciones', 'alta', true)
        ON CONFLICT DO NOTHING
    """)

    # Seed CNMV ECR micro-obligaciones
    op.execute("""
        INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad, activo) VALUES
        ('CNMV_ECR_REPORTING', 'Reporte estados reservados CNMV ECR', 'Comunicacion de estados reservados a CNMV via ECR (XML requerimientos)', 'cnmv_ecr', 'reporting_cnmv_ecr', 'periodicidad', 'trimestral', 'reporting', 'alta', true),
        ('CNMV_ECR_XML_FORMAT', 'XML formatos ECR CNMV', 'Generar XML segun formatos requeridos por CNMV para ECR', 'cnmv_ecr', 'reporting_cnmv_ecr', 'periodicidad', 'trimestral', 'reporting', 'media', true),
        ('CNMV_ECR_ACTIVE_LIST', 'Listado FCR/SCR activos CNMV', 'Mantener listado actualizado de FCR/SCR inscritos en CNMV', 'cnmv_ecr', 'reporting_cnmv_ecr', 'continuo', 'mensual', 'compliance', 'alta', true),
        ('CNMV_ECR_FAQS', 'FAQs criterios interpretativos CNMV', 'Seguir FAQs y criterios interpretativos de CNMV para ECR', 'cnmv_ecr', 'reporting_cnmv_ecr', 'continuo', 'continua', 'compliance', 'media', true)
        ON CONFLICT DO NOTHING
    """)

    # Seed Doctrina DGT micro-obligaciones
    op.execute("""
        INSERT INTO micro_obligacion (codigo, nombre, descripcion, regulacion_relacionada, ambito, trigger_evento, frecuencia, owner_rol, severidad, activo) VALUES
        ('DGT_SOCIMI_GRAVAMENES', 'Doctrina DGT gravamenes SOCIMI', 'Aplicar doctrina DGT V0992-20 sobre gravamenes a socios >5% en SOCIMI', 'doctrina_dgt', 'doctrina_dgt', 'continuo', 'continua', 'finanzas', 'alta', true),
        ('DGT_SOCIMI_DISTRIBUCION', 'Doctrina DGT distribucion SOCIMI', 'Interpretar doctrina DGT sobre obligacion de distribucion de beneficios en SOCIMI', 'doctrina_dgt', 'doctrina_dgt', 'periodicidad', 'anual', 'finanzas', 'media', true),
        ('DGT_ETI_EMISORES', 'Doctrina DGT ETI emisores MiFID', 'Interpretar doctrina DGT sobre emisores con ETI y folletos MiFID', 'doctrina_dgt', 'doctrina_dgt', 'continuo', 'continua', 'compliance', 'media', true),
        ('DGT_FCR_EXENCIONES', 'Doctrina DGT exenciones FCR/SCR', 'Aplicar doctrina DGT V2424-20 sobre exenciones fiscales similares para FCR/SCR', 'doctrina_dgt', 'doctrina_dgt', 'periodicidad', 'anual', 'finanzas', 'media', true)
        ON CONFLICT DO NOTHING
    """)

    # Seed mapping: obligacion_regulatoria -> micro_obligacion para nuevas regulaciones
    op.execute("""
        INSERT INTO obligacion_micro_obligacion (obligacion_id, micro_obligacion_id, orden, evidencia_requerida)
        SELECT o.id, m.id, 0, NULL
        FROM obligacion_regulatoria o, micro_obligacion m
        WHERE (o.fuente = 'boe' AND m.regulacion_relacionada IN ('lecr', 'socimi', 'csdr', 'doctrina_dgt', 'cnmv_ecr'))
        ON CONFLICT DO NOTHING
    """)
