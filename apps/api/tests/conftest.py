import os
import sys
import tempfile
import uuid
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

TESTS_ROOT = Path(__file__).resolve().parent
REPO_ROOT = TESTS_ROOT.parents[3]

# Add repo root to sys.path so `from apps.xxx` imports work when pytest is invoked
# without pyproject.toml pythonpath (e.g. IDE runners, older pytest without importlib)
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from apps.workers import screening as screening_worker
from apps.workers.pgc_dataset import (
    PGC_ACCOUNTS_2021,
    PGC_AEAT_REFERENCES_2021,
    PGC_ESTADOS_FINANCIEROS_2021,
    PGC_MARCO_2021,
    PGC_NORMAS_2021,
    PGC_REFERENCIAS_FISCALES_2021,
)

# Configure test environment BEFORE any module imports that read os.environ
os.environ["APP_ENV"] = "test"
os.environ["ESDATA_API_KEY"] = "test-secret-key"
os.environ["MCP_API_KEY"] = "test-mcp-key"
os.environ["ESDATA_ALLOW_INSECURE_TEST_AUTH"] = "true"

TEST_DB_PATH = Path(tempfile.gettempdir()) / f"esdata_api_tests_{uuid.uuid4().hex}.sqlite3"
REPO_ROOT = Path(__file__).resolve().parents[3]
XBRL_FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "xbrl" / "minimal_filing.xbrl"

XBRL_FIXTURE_CATALOG = {
    "fixture_path": str(XBRL_FIXTURE_PATH),
    "entity_identifier": "ES_TEST_0001",
    "filing": {
        "source_name": XBRL_FIXTURE_PATH.name,
        "source_path": str(XBRL_FIXTURE_PATH.resolve()),
        "entity_identifier": "ES_TEST_0001",
        "period_start": "2025-01-01",
        "period_end": "2025-12-31",
        "filing_type": "xbrl",
    },
    "facts": [
        {
            "concept": "Assets",
            "value_raw": "5000000",
            "value_numeric": Decimal("5000000"),
            "unit": "iso4217:EUR",
            "context_ref": "ctx_2025",
            "period_start": "2025-01-01",
            "period_end": "2025-12-31",
            "entity_identifier": "ES_TEST_0001",
            "decimals": "0",
        },
        {
            "concept": "ProfitLoss",
            "value_raw": "125000",
            "value_numeric": Decimal("125000"),
            "unit": "iso4217:EUR",
            "context_ref": "ctx_2025",
            "period_start": "2025-01-01",
            "period_end": "2025-12-31",
            "entity_identifier": "ES_TEST_0001",
            "decimals": "0",
        },
        {
            "concept": "Revenue",
            "value_raw": "1000000",
            "value_numeric": Decimal("1000000"),
            "unit": "iso4217:EUR",
            "context_ref": "ctx_2025",
            "period_start": "2025-01-01",
            "period_end": "2025-12-31",
            "entity_identifier": "ES_TEST_0001",
            "decimals": "0",
        },
    ],
}

PGC_CATALOG = {
    "marco": PGC_MARCO_2021,
    "accounts": PGC_ACCOUNTS_2021,
    "normas": PGC_NORMAS_2021,
    "estados_financieros": PGC_ESTADOS_FINANCIEROS_2021,
    "referencias_fiscales": PGC_REFERENCIAS_FISCALES_2021,
    "referencias_aeat": PGC_AEAT_REFERENCES_2021,
}

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"

engine = create_engine(
    os.environ["DATABASE_URL"],
    future=True,
    connect_args={"check_same_thread": False},
)

STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS norma (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        titulo TEXT NOT NULL,
        boe_id TEXT UNIQUE NOT NULL,
        eli_uri TEXT UNIQUE,
        jurisdiccion TEXT NOT NULL,
        tipo_fuente TEXT NOT NULL,
        tipo_documento TEXT NOT NULL,
        ambito TEXT NOT NULL,
        regulacion_relacionada TEXT,
        estado_cobertura TEXT NOT NULL,
        vigente_desde TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS articulo (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        norma_id INTEGER NOT NULL REFERENCES norma(id),
        numero TEXT NOT NULL,
        titulo TEXT,
        tipo TEXT NOT NULL,
        UNIQUE (norma_id, numero)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS version_articulo (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        articulo_id INTEGER NOT NULL REFERENCES articulo(id),
        texto TEXT NOT NULL,
        vigente_desde TEXT NOT NULL,
        vigente_hasta TEXT,
        boe_bloque_id TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS documento_interpretativo (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo_documento TEXT NOT NULL,
        organismo_emisor TEXT NOT NULL,
        jurisdiccion TEXT NOT NULL,
        tipo_fuente TEXT NOT NULL,
        ambito TEXT NOT NULL,
        referencia TEXT UNIQUE NOT NULL,
        fecha TEXT NOT NULL,
        titulo TEXT,
        texto TEXT NOT NULL,
        url_fuente TEXT,
        estado_vigencia TEXT,
        numero_circular TEXT,
        fecha_publicacion TEXT,
        referencia_boe TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS empresa (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        nif TEXT,
        domicilio TEXT,
        fuente_inicial TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS obligacion_regulatoria (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        nombre TEXT NOT NULL,
        fuente TEXT NOT NULL,
        organismo_emisor TEXT NOT NULL,
        tipo_obligacion TEXT NOT NULL,
        sujeto_obligado TEXT NOT NULL,
        periodicidad TEXT,
        reporte_modelo TEXT,
        ambito TEXT NOT NULL,
        estado_vigencia TEXT NOT NULL,
        documento_origen_tipo TEXT,
        documento_origen_ref TEXT,
        seccion_origen TEXT,
        anexo_origen TEXT,
        nota TEXT,
        plazo_dias INTEGER,
        frecuencia_presentacion TEXT,
        ventana_presentacion TEXT,
        trigger_presentacion TEXT,
        canal_presentacion TEXT,
        obligados_resumen TEXT,
        sancion_min TEXT,
        sancion_max TEXT,
        recargo_voluntario TEXT,
        recargo_involuntario TEXT,
        interes_demora TEXT,
        prescripcion_anos INTEGER,
        deposito_previo TEXT,
        fuentes_operativas TEXT,
        ultima_actualizacion TEXT,
        origen_metadato TEXT,
        estado_metadato TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS obligacion_documento (
        obligacion_id INTEGER NOT NULL REFERENCES obligacion_regulatoria(id),
        documento_id INTEGER NOT NULL REFERENCES documento_interpretativo(id),
        tipo_relacion TEXT NOT NULL,
        PRIMARY KEY (obligacion_id, documento_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS documento_empresa (
        documento_id INTEGER NOT NULL REFERENCES documento_interpretativo(id),
        empresa_id INTEGER NOT NULL REFERENCES empresa(id),
        rol TEXT NOT NULL,
        confianza_extraccion REAL NOT NULL,
        nota TEXT,
        PRIMARY KEY (documento_id, empresa_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS documento_version (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        documento_referencia TEXT NOT NULL,
        version_num INTEGER NOT NULL,
        texto TEXT NOT NULL,
        cambio_tipo TEXT NOT NULL,
        fecha_version TEXT,
        nota TEXT,
        url_version TEXT,
        UNIQUE(documento_referencia, version_num)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS cnmv_regulation_link (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        documento_referencia TEXT NOT NULL,
        regulacion_id TEXT NOT NULL,
        relacion_tipo TEXT NOT NULL,
        nota TEXT,
        UNIQUE(documento_referencia, regulacion_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS cnmv_obligation_link (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        documento_referencia TEXT NOT NULL,
        tipo_obligacion TEXT NOT NULL,
        nota TEXT,
        UNIQUE(documento_referencia, tipo_obligacion)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS documento_articulo (
        documento_id INTEGER NOT NULL REFERENCES documento_interpretativo(id),
        articulo_id INTEGER NOT NULL REFERENCES articulo(id),
        metodo_enlace TEXT NOT NULL,
        confianza_enlace REAL NOT NULL,
        nota TEXT,
        PRIMARY KEY (documento_id, articulo_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS materia (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug TEXT UNIQUE NOT NULL,
        etiqueta TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS articulo_materia (
        articulo_id INTEGER NOT NULL REFERENCES articulo(id),
        materia_id INTEGER NOT NULL REFERENCES materia(id),
        relevancia INTEGER NOT NULL DEFAULT 1,
        PRIMARY KEY (articulo_id, materia_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sync_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        worker TEXT NOT NULL,
        started_at TEXT NOT NULL,
        finished_at TEXT,
        status TEXT NOT NULL,
        bloques_processed INTEGER,
        articulos_upserted INTEGER,
        documentos_processed INTEGER,
        documentos_upserted INTEGER,
        doctrina_links_created INTEGER,
        rows_processed INTEGER,
        errors INTEGER,
        duration_ms INTEGER,
        error_msg TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS micro_obligacion (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT NOT NULL UNIQUE,
        nombre TEXT NOT NULL,
        descripcion TEXT,
        regulacion_relacionada TEXT NOT NULL,
        ambito TEXT,
        trigger_evento TEXT,
        frecuencia TEXT,
        owner_rol TEXT,
        severidad TEXT,
        activo BOOLEAN NOT NULL DEFAULT 1
    )
    """,
    """
    INSERT INTO micro_obligacion (
        codigo, nombre, descripcion, regulacion_relacionada, ambito,
        trigger_evento, frecuencia, owner_rol, severidad, activo
    ) VALUES (
        'CSDR-SETTLEMENT-001',
        'Control de settlement fail',
        'Monitorizar y gestionar settlement fails bajo CSDR.',
        'csdr',
        'infraestructura_mercados_financieros',
        'settlement_fail',
        'diaria',
        'operaciones',
        'alta',
        1
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS obligacion_regulatoria (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT NOT NULL UNIQUE,
        nombre TEXT NOT NULL,
        fuente TEXT,
        organismo_emisor TEXT,
        tipo_obligacion TEXT,
        sujeto_obligado TEXT,
        periodicidad TEXT,
        reporte_modelo TEXT,
        ambito TEXT,
        estado_vigencia TEXT,
        plazo_dias INTEGER,
        frecuencia_presentacion TEXT,
        ventana_presentacion TEXT,
        trigger_presentacion TEXT,
        sancion_min REAL,
        sancion_max REAL,
        prescripcion_anos INTEGER
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS obligacion_internacional (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT NOT NULL UNIQUE,
        titulo TEXT NOT NULL,
        tipo TEXT NOT NULL,
        jurisdiccion_origen TEXT,
        jurisdiccion_aplicacion TEXT,
        vigente_desde TEXT,
        vigente_hasta TEXT,
        descripcion TEXT,
        estado TEXT NOT NULL,
        creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        actualizado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS obligacion_micro_obligacion (
        obligacion_id INTEGER NOT NULL REFERENCES obligacion_regulatoria(id) ON DELETE CASCADE,
        micro_obligacion_id INTEGER NOT NULL REFERENCES micro_obligacion(id) ON DELETE CASCADE,
        orden INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (obligacion_id, micro_obligacion_id)
    )
    """,
    """
    INSERT INTO micro_obligacion (
        codigo, nombre, descripcion, regulacion_relacionada, ambito,
        trigger_evento, frecuencia, owner_rol, severidad, activo
    ) VALUES
        ('MIFID_SUITABILITY', 'Evaluacion de suitability', 'Evaluar idoneidad del cliente antes de recomendar instrumentos complejos.', 'mifid_ii', 'mercados', 'asesoramiento', 'por_operacion', 'compliance', 'alta', 1),
        ('CNMV_TRANSPARENCIA', 'Reporting de transparencia CNMV', 'Mantener reporting periodico de transparencia y hechos relevantes ante CNMV.', 'cnmv_lmcv', 'reporting_regulatorio', 'evento_relevante', 'diaria', 'compliance', 'alta', 1),
        ('SEPBLAC_KYC', 'Debida diligencia KYC', 'Aplicar medidas de identificacion formal y conocimiento del cliente.', 'pblcft', 'aml_cft', 'alta_cliente', 'continua', 'compliance', 'alta', 1),
        ('MIFIR_REPORTING', 'Transaction reporting MiFIR', 'Reportar operaciones ejecutadas al supervisor con trazabilidad completa.', 'mifir', 'mercados', 'ejecucion_orden', 'continua', 'trading', 'alta', 1),
        ('MIFID_BEST_EXECUTION', 'Best execution', 'Monitorizar la mejor ejecucion y justificar la seleccion de venue.', 'mifid_ii', 'mercados', 'ejecucion_orden', 'continua', 'trading', 'alta', 1),
        ('SEPBLAC_STR', 'Comunicacion de operacion sospechosa', 'Analizar y comunicar sin demora indicios de blanqueo al SEPBLAC.', 'pblcft', 'aml_cft', 'indicio_lp', 'eventual', 'compliance', 'alta', 1),
        ('LECR_ECR_REGISTRATION', 'Registro ECR', 'Mantener la inscripcion y documentacion exigida para entidades de capital-riesgo.', 'lecr', 'ecr_regulatorio', 'alta_entidad', 'continua', 'legal', 'alta', 1),
        ('SOCIMI_ASSET_COMPOSITION', 'Composicion de activos SOCIMI', 'Verificar el cumplimiento de la composicion minima de activos arrendados y participaciones.', 'socimi', 'societario_fiscal', 'cierre_periodo', 'trimestral', 'fiscal', 'alta', 1),
        ('CSDR_SETTLEMENT', 'Settlement discipline', 'Controlar settlement fails y medidas correctoras bajo CSDR.', 'csdr', 'infraestructuras_csd', 'settlement_fail', 'continua', 'operaciones', 'alta', 1),
        ('CNMV_ECR_REPORTING', 'Reporting ECR a CNMV', 'Preparar y remitir reporting periodico de ECR a la CNMV.', 'cnmv_ecr', 'reporting_cnmv_ecr', 'fin_periodo', 'trimestral', 'compliance', 'media', 1),
        ('DGT_SOCIMI_GRAVAMENES', 'Doctrina DGT sobre gravamenes SOCIMI', 'Aplicar criterio doctrinal DGT V0992-20 sobre gravamen especial y distribucion de beneficios.', 'doctrina_dgt', 'doctrina_dgt', 'consulta_fiscal', 'eventual', 'fiscal', 'media', 1)
    """,
    """
    INSERT INTO obligacion_internacional (
        codigo, titulo, tipo, jurisdiccion_origen, jurisdiccion_aplicacion,
        vigente_desde, vigente_hasta, descripcion, estado
    ) VALUES
        ('FATCA', 'Foreign Account Tax Compliance Act (FATCA) — Ley 16/2012 de implementacion', 'ley', 'US', 'ES', '2012-12-28', NULL, 'Ley espanola que implementa FATCA en Espana, requiriendo a instituciones financieras espanolas reportar cuentas de titulares estadounidenses al IRS.', 'activo'),
        ('CRS', 'Common Reporting Standard (CRS) — Estandar OCDE para intercambio automatico de informacion financiera', 'estandar', 'OCDE', 'internacional', '2016-01-01', NULL, 'Estandar internacional para el intercambio automatico de informacion financiera entre jurisdicciones participantes para combatir la evasion fiscal transfronteriza.', 'activo'),
        ('FATCA_IGA_ES', 'Acuerdo Intergubernamental FATCA entre Espana y Estados Unidos — Modelo 1', 'convenio', 'ES-US', 'ES-US', '2013-09-02', NULL, 'Acuerdo intergubernamental Modelo 1 entre Espana y EE.UU. para la implementacion de FATCA. Espana intercambia informacion automaticamente con el IRS.', 'activo'),
        ('DAC6', 'Directiva DAC6 — Reporte obligatorio de arreglos transfronterizos agresivos', 'directiva', 'UE', 'UE', '2018-06-25', NULL, 'Obliga a intermediarios a reportar arreglos transfronterizos que cumplan hallmarks de agresividad fiscal.', 'activo'),
        ('DAC7', 'Directiva DAC7 — Informacion para plataformas digitales', 'directiva', 'UE', 'UE', '2020-12-22', NULL, 'Requiere que las plataformas digitales reporten informacion sobre los vendedores que utilizan sus servicios.', 'activo'),
        ('DAC8', 'Directiva DAC8 — Informacion sobre criptoactivos', 'directiva', 'UE', 'UE', '2023-12-27', NULL, 'Extiende el intercambio automatico de informacion para incluir criptoactivos y cripto-proveedores de servicios.', 'inactivo')
    """,
    """
    WITH RECURSIVE filler(n) AS (
        SELECT 1
        UNION ALL
        SELECT n + 1 FROM filler WHERE n < 41
    )
    INSERT INTO micro_obligacion (
        codigo, nombre, descripcion, regulacion_relacionada, ambito,
        trigger_evento, frecuencia, owner_rol, severidad, activo
    )
    SELECT
        printf('FILLER_%02d', n),
        printf('Micro obligacion filler %02d', n),
        'Registro de soporte para cobertura de taxonomia en tests.',
        CASE n % 5
            WHEN 0 THEN 'mifid_ii'
            WHEN 1 THEN 'pblcft'
            WHEN 2 THEN 'mifir'
            WHEN 3 THEN 'mar'
            ELSE 'cnmv_lmcv'
        END,
        CASE n % 4
            WHEN 0 THEN 'mercados'
            WHEN 1 THEN 'aml_cft'
            WHEN 2 THEN 'reporting_regulatorio'
            ELSE 'operaciones'
        END,
        'evento_control',
        CASE n % 3 WHEN 0 THEN 'diaria' WHEN 1 THEN 'mensual' ELSE 'continua' END,
        CASE n % 3 WHEN 0 THEN 'compliance' WHEN 1 THEN 'operaciones' ELSE 'trading' END,
        CASE n % 3 WHEN 0 THEN 'alta' WHEN 1 THEN 'media' ELSE 'baja' END,
        1
    FROM filler
    """,
    """
    INSERT INTO obligacion_regulatoria (
        codigo, nombre, fuente, organismo_emisor, tipo_obligacion, sujeto_obligado,
        periodicidad, reporte_modelo, ambito, estado_vigencia, plazo_dias,
        frecuencia_presentacion, ventana_presentacion, trigger_presentacion,
        sancion_min, sancion_max, prescripcion_anos
    ) VALUES
        ('CNMV-IR-RESERVADA', 'Informacion reservada CNMV', 'CNMV', 'CNMV', 'reporting', 'sociedad_valores', 'mensual', 'IR-CNMV', 'reporting_regulatorio', 'vigente', 30, 'mensual', 'primeros_30_dias', 'fin_periodo', 3000, 300000, 5),
        ('SEPBLAC-INDICIO-M19', 'Comunicacion por indicio SEPBLAC', 'SEPBLAC', 'SEPBLAC', 'aml_report', 'sujeto_obligado_pbcft', 'eventual', 'M19', 'aml_cft', 'vigente', 1, 'eventual', 'sin_demora', 'indicio_lp', 6000, 1500000, 10)
    """,
    """
    INSERT INTO obligacion_micro_obligacion (obligacion_id, micro_obligacion_id, orden)
    SELECT o.id, m.id, 1
    FROM obligacion_regulatoria o, micro_obligacion m
    WHERE o.codigo = 'CNMV-IR-RESERVADA' AND m.codigo = 'CNMV_TRANSPARENCIA'
    """,
    """
    INSERT INTO obligacion_micro_obligacion (obligacion_id, micro_obligacion_id, orden)
    SELECT o.id, m.id, 2
    FROM obligacion_regulatoria o, micro_obligacion m
    WHERE o.codigo = 'CNMV-IR-RESERVADA' AND m.codigo = 'CNMV_ECR_REPORTING'
    """,
    """
    INSERT INTO obligacion_micro_obligacion (obligacion_id, micro_obligacion_id, orden)
    SELECT o.id, m.id, 1
    FROM obligacion_regulatoria o, micro_obligacion m
    WHERE o.codigo = 'SEPBLAC-INDICIO-M19' AND m.codigo = 'SEPBLAC_STR'
    """,
    """
    INSERT INTO obligacion_micro_obligacion (obligacion_id, micro_obligacion_id, orden)
    SELECT o.id, m.id, 2
    FROM obligacion_regulatoria o, micro_obligacion m
    WHERE o.codigo = 'SEPBLAC-INDICIO-M19' AND m.codigo = 'SEPBLAC_KYC'
    """,
    """
    CREATE TABLE IF NOT EXISTS csrd_entity_report (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER NOT NULL,
        reporting_year INTEGER NOT NULL,
        esap_url TEXT,
        assurance_status TEXT,
        reporting_standard TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS csrd_esg_data_point (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_id INTEGER NOT NULL REFERENCES csrd_entity_report(id) ON DELETE CASCADE,
        topic TEXT NOT NULL,
        indicator_code TEXT NOT NULL,
        value REAL,
        unit TEXT,
        scope INTEGER,
        verification_status TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS csrd_ess (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        standard_code TEXT NOT NULL,
        topic TEXT NOT NULL,
        applicable_from_year INTEGER,
        description TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS csrd_double_materiality (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER NOT NULL,
        impact_materiality TEXT,
        financial_materiality TEXT,
        assessment_date TEXT,
        key_impacts TEXT,
        key_dependencies TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dac_reporting_entity (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tin TEXT NOT NULL,
        entity_type TEXT NOT NULL,
        member_state TEXT NOT NULL,
        dac8_registered BOOLEAN NOT NULL DEFAULT 0,
        dac9_registered BOOLEAN NOT NULL DEFAULT 0,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dac_crypto_report (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER NOT NULL REFERENCES dac_reporting_entity(id) ON DELETE CASCADE,
        reporting_period TEXT NOT NULL,
        submitted_at TEXT,
        status TEXT NOT NULL,
        crypto_transactions_count INTEGER NOT NULL DEFAULT 0,
        wallet_holders_count INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dac_wallet_holder (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_id INTEGER NOT NULL REFERENCES dac_crypto_report(id) ON DELETE CASCADE,
        wallet_address TEXT NOT NULL,
        holder_tin TEXT,
        holder_member_state TEXT,
        holder_type TEXT NOT NULL,
        total_value_eur REAL,
        verification_status TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dora_tic_incident (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER NOT NULL,
        incident_severity TEXT NOT NULL,
        description TEXT,
        impact_scope TEXT,
        detection_date TEXT,
        resolution_date TEXT,
        root_cause TEXT,
        classification TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dora_third_party_provider (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        provider_name TEXT NOT NULL,
        provider_type TEXT NOT NULL,
        criticality_assessment TEXT,
        contract_start TEXT,
        contract_end TEXT,
        eu_supervision_status TEXT,
        exit_strategy TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dora_ict_risk_register (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER NOT NULL,
        risk_description TEXT NOT NULL,
        likelihood TEXT,
        impact TEXT,
        mitigation TEXT,
        owner TEXT,
        review_date TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dora_penetration_test (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER NOT NULL,
        test_type TEXT NOT NULL,
        tester TEXT,
        test_date TEXT,
        findings_count INTEGER,
        critical_findings INTEGER,
        remediation_deadline TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dora_incident_classification_framework (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        framework_version TEXT NOT NULL,
        severity_thresholds TEXT,
        reporting_timelines TEXT,
        effective_date TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS empresa (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        nif TEXT,
        domicilio TEXT,
        fuente_inicial TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS entity_identifiers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER REFERENCES empresa(id),
        lei TEXT NOT NULL UNIQUE,
        nombre_legal TEXT NOT NULL,
        pais TEXT,
        estado TEXT,
        vigencia_desde TEXT,
        vigencia_hasta TEXT,
        vlei_status TEXT,
        vlei_cred_url TEXT,
        fuente_ref TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS entity_aliases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL REFERENCES empresa(id) ON DELETE CASCADE,
        alias TEXT NOT NULL,
        alias_normalizado TEXT NOT NULL,
        fuente TEXT,
        confianza REAL NOT NULL DEFAULT 0.0
    )
    """,
    # --- Fraud / MAR ---
    """
    CREATE TABLE IF NOT EXISTS fraud_prevention_program (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER NOT NULL,
        code_of_conduct BOOLEAN NOT NULL DEFAULT 0,
        internal_reporting_system BOOLEAN NOT NULL DEFAULT 0,
        training_schedule TEXT,
        audit_frequency TEXT,
        compliance_officer_name TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS fraud_risk_assessment (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER NOT NULL,
        assessment_date TEXT NOT NULL,
        risk_areas TEXT,
        mitigation_measures TEXT,
        next_review_date TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS fraud_incident (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER NOT NULL,
        incident_date TEXT NOT NULL,
        description TEXT NOT NULL,
        amount_eur REAL,
        status TEXT NOT NULL,
        resolution_date TEXT,
        regulatory_notification BOOLEAN NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS mar_insider_transaction (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ppi_name TEXT NOT NULL,
        ppi_role TEXT,
        instrument TEXT NOT NULL,
        transaction_type TEXT NOT NULL,
        quantity REAL,
        value_eur REAL,
        price REAL,
        date_time TEXT,
        country TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS mar_suspicious_transaction_report (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER NOT NULL,
        instrument TEXT NOT NULL,
        pattern_description TEXT,
        detection_method TEXT,
        severity TEXT,
        submitted_to_cnmv BOOLEAN NOT NULL DEFAULT 0,
        cnmv_reference TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS mar_market_manipulation_indicator (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pattern_type TEXT NOT NULL,
        instrument TEXT NOT NULL,
        time_window TEXT,
        volume_anomaly_pct REAL,
        price_anomaly_pct REAL,
        confidence_score REAL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS mar_insider_communication (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER NOT NULL,
        receiver_id INTEGER NOT NULL,
        content_summary TEXT,
        timestamp TEXT,
        channel TEXT,
        inside_info_reference TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    # --- MiFID / PBC ---
    """
    CREATE TABLE IF NOT EXISTS mifid_client_category (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER NOT NULL,
        category TEXT NOT NULL,
        assessment_date TEXT NOT NULL,
        knowledge_level TEXT,
        experience_level TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS mifid_suitability_report (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        assessment_date TEXT NOT NULL,
        suitability_score INTEGER,
        recommendation TEXT NOT NULL,
        advisor_id INTEGER,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS mifid_best_execution_record (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        venue TEXT NOT NULL,
        execution_price REAL,
        market_impact REAL,
        speed_ms INTEGER,
        quality_metrics TEXT,
        execution_timestamp TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS mifid_conflict_of_interest_registry (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        department TEXT NOT NULL,
        conflict_type TEXT NOT NULL,
        description TEXT,
        mitigation_measure TEXT,
        identified_date TEXT,
        review_date TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS mifid_product_governance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        target_market TEXT NOT NULL,
        distribution_channels TEXT,
        key_features TEXT,
        risk_level INTEGER,
        review_date TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS mifid_order_record (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER NOT NULL,
        instrument TEXT NOT NULL,
        direction TEXT NOT NULL,
        quantity REAL,
        price REAL,
        timestamp TEXT,
        venue TEXT,
        status TEXT NOT NULL,
        retention_until TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS mifid_insider_list (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        insider_name TEXT NOT NULL,
        insider_tin TEXT,
        entity_id INTEGER NOT NULL,
        inside_information_description TEXT NOT NULL,
        date_created TEXT,
        date_removed TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS mifid_compensation_policy (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER NOT NULL,
        policy_version TEXT NOT NULL,
        alignment_score INTEGER,
        risk_adjustment_applied BOOLEAN,
        approval_date TEXT,
        next_review TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pbc_obligated_subject (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_type TEXT NOT NULL,
        tin TEXT NOT NULL,
        registration_number TEXT NOT NULL,
        supervisory_authority TEXT,
        pbc_license TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pbc_internal_control (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        obligated_subject_id INTEGER NOT NULL REFERENCES pbc_obligated_subject(id) ON DELETE CASCADE,
        risk_assessment_date TEXT,
        compliance_officer TEXT,
        internal_reporting_channel BOOLEAN,
        training_program BOOLEAN,
        audit_trail BOOLEAN,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS suspicious_activity_report (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        obligated_subject_id INTEGER NOT NULL REFERENCES pbc_obligated_subject(id) ON DELETE CASCADE,
        submission_date TEXT,
        description TEXT,
        severity TEXT,
        status TEXT NOT NULL,
        sepblac_reference TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS beneficial_owner_record (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER NOT NULL REFERENCES empresa(id),
        owner_name TEXT NOT NULL,
        ownership_percentage REAL,
        acquisition_date TEXT,
        verification_method TEXT,
        verification_date TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    # --- IRS / DTA ---
    """
    CREATE TABLE IF NOT EXISTS irs_fiscal_norma (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT NOT NULL UNIQUE,
        titulo TEXT NOT NULL,
        tipo TEXT NOT NULL,
        anio_vigencia INTEGER,
        estado TEXT NOT NULL,
        texto TEXT,
        url_fuente TEXT,
        creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        actualizado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS irs_dta_convention (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT NOT NULL UNIQUE,
        pais_origen TEXT NOT NULL,
        pais_destino TEXT NOT NULL,
        titulo TEXT NOT NULL,
        fecha_firma TEXT,
        fecha_vigencia TEXT,
        tipo_acuerdo TEXT,
        boe_referencia TEXT,
        articulos TEXT,
        texto_completo TEXT,
        estado TEXT NOT NULL,
        creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        actualizado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS irs_withholding_rule (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT NOT NULL UNIQUE,
        tipo_renta TEXT NOT NULL,
        tipo_renta_espanol TEXT,
        tipo_retencion_default REAL NOT NULL,
        tipo_retencion_dta REAL,
        pais_aplicable TEXT,
        descripcion TEXT,
        norma_referencia TEXT,
        articulo_referencia TEXT,
        estado TEXT NOT NULL,
        creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        actualizado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS irs_w8_form (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT NOT NULL UNIQUE,
        nombre TEXT NOT NULL,
        descripcion TEXT,
        tipo_sujeto TEXT NOT NULL,
        finalidad TEXT,
        validez_anios INTEGER,
        obligacion_asociada TEXT,
        texto_detalle TEXT,
        estado TEXT NOT NULL,
        partes TEXT,
        creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        actualizado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS irs_tin_reference (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo_pais TEXT NOT NULL UNIQUE,
        pais_nombre TEXT NOT NULL,
        formato_tin TEXT,
        ejemplo_tin TEXT,
        emisor_espana TEXT,
        emisor_pais TEXT,
        es_ocde BOOLEAN NOT NULL DEFAULT 0,
        es_eu_vat BOOLEAN NOT NULL DEFAULT 0,
        creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS giin_registry (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        giin TEXT NOT NULL UNIQUE,
        entidad_nombre TEXT NOT NULL,
        entidad_pais TEXT,
        tipo_entidad TEXT NOT NULL,
        estado_fatca TEXT NOT NULL,
        fecha_registro TEXT,
        fecha_expiracion TEXT,
        es_exempt_beneficial_owner BOOLEAN NOT NULL DEFAULT 0,
        es_sponsored_ffo BOOLEAN NOT NULL DEFAULT 0,
        nota TEXT,
        creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        actualizado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    INSERT INTO irs_fiscal_norma (codigo, titulo, tipo, anio_vigencia, estado, texto, url_fuente) VALUES
        ('FORM_1040', 'U.S. Individual Income Tax Return', 'forma', 2024, 'activo', 'Formulario base para declaracion individual.', 'https://www.irs.gov/forms-pubs/about-form-1040'),
        ('FORM_W8BEN', 'Certificate of Foreign Status of Beneficial Owner', 'forma', 2024, 'activo', 'Formulario para personas fisicas extranjeras.', 'https://www.irs.gov/forms-pubs/about-form-w-8-ben'),
        ('FORM_W8BENE', 'Certificate of Status of Beneficial Owner for United States Tax Withholding and Reporting', 'forma', 2024, 'activo', 'Formulario para entidades extranjeras.', 'https://www.irs.gov/forms-pubs/about-form-w-8-ben-e')
    """,
    """
    INSERT INTO irs_dta_convention (
        codigo, pais_origen, pais_destino, titulo, fecha_firma, fecha_vigencia,
        tipo_acuerdo, boe_referencia, articulos, texto_completo, estado
    ) VALUES
        ('DTA_US_ES', 'US', 'ES', 'Convenio entre Estados Unidos y Espana para evitar la doble imposicion', '1990-02-22', '1990-11-21', 'bilateral', 'BOE-A-1990-12345', '31,32', 'Texto consolidado de prueba del convenio US-ES.', 'vigente'),
        ('ES_US_DTA', 'US', 'ES', 'Convenio bilateral US-ES para pruebas legacy', '1990-02-22', '1990-11-21', 'bilateral', 'BOE-A-1990-12345', '31,32', 'Alias de compatibilidad para endpoints legacy.', 'vigente'),
        ('DTA_US_FR', 'US', 'FR', 'Convenio entre Estados Unidos y Francia para evitar la doble imposicion', '1994-08-31', '1995-12-30', 'bilateral', 'FR-1995-1', '10,11', 'Texto consolidado de prueba del convenio US-FR.', 'vigente')
    """,
    """
    INSERT INTO irs_withholding_rule (
        codigo, tipo_renta, tipo_renta_espanol, tipo_retencion_default,
        tipo_retencion_dta, pais_aplicable, descripcion, norma_referencia,
        articulo_referencia, estado
    ) VALUES
        ('WHT_DIVIDENDS', 'dividends', 'Dividendos', 30.0, 15.0, 'US', 'Retencion general sobre dividendos pagados a no residentes.', 'IRC', '1441', 'activo'),
        ('DIVIDEND', 'dividends', 'Dividendos', 30.0, 15.0, 'US', 'Regla legacy de dividendos para compatibilidad con tests.', 'IRC', '1441', 'activo'),
        ('WHT_INTEREST', 'interest', 'Intereses', 30.0, 10.0, 'US', 'Retencion sobre intereses con posible reduccion por convenio.', 'IRC', '1441', 'activo'),
        ('WHT_ROYALTIES', 'royalties', 'Regalias', 30.0, NULL, 'US', 'Retencion sobre regalias sin reduccion especifica en seed.', 'IRC', '1441', 'activo')
    """,
    """
    INSERT INTO irs_w8_form (
        codigo, nombre, descripcion, tipo_sujeto, finalidad, validez_anios,
        obligacion_asociada, texto_detalle, estado, partes
    ) VALUES
        ('W8BEN', 'Form W-8BEN', 'Formulario para personas fisicas extranjeras.', 'persona_fisica', 'Acreditar condicion de no residente y solicitar beneficios de convenio.', 3, 'withholding', 'Detalle resumido del W-8BEN.', 'activo', 'Part I, Part II, Part III'),
        ('W8BENE', 'Form W-8BEN-E', 'Formulario para entidades extranjeras.', 'persona_juridica', 'Acreditar condicion FATCA y beneficios de convenio para entidades.', 3, 'withholding', 'Detalle resumido del W-8BEN-E.', 'activo', 'Part I, Part III, Part XXIX')
    """,
    """
    INSERT INTO irs_tin_reference (
        codigo_pais, pais_nombre, formato_tin, ejemplo_tin, emisor_espana,
        emisor_pais, es_ocde, es_eu_vat
    ) VALUES
        ('US', 'United States', 'NN-NNNNNNN', '12-3456789', 'AEAT', 'IRS', 1, 0),
        ('ES', 'Spain', '99999999A', '12345678Z', 'AEAT', 'AEAT', 1, 1)
    """,
    """
    INSERT INTO giin_registry (
        giin, entidad_nombre, entidad_pais, tipo_entidad, estado_fatca,
        fecha_registro, fecha_expiracion, es_exempt_beneficial_owner,
        es_sponsored_ffo, nota
    ) VALUES
        ('GIIN123.456.789.001', 'Entidad Financiera Espanola Demo', 'ES', 'FFI', 'activo', '2024-01-01', '2027-12-31', 0, 0, 'Registro GIIN de prueba activo.'),
        ('FAKE_GIIN_001', 'Entidad Extranjera Demo', 'US', 'NFFE', 'activo', '2024-01-01', '2027-12-31', 0, 0, 'Registro GIIN/NFFE de prueba para recomendacion W-8BEN-E.')
    """,
    # --- PRIIPS / LIVMC ---
    """
    CREATE TABLE IF NOT EXISTS priips_kid (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        product_type TEXT NOT NULL,
        currency TEXT,
        risk_scale INTEGER,
        cost_impact TEXT,
        negative_scenario_returns TEXT,
        version TEXT,
        publication_date TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS priips_product (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        issuer_id INTEGER NOT NULL,
        product_name TEXT NOT NULL,
        underlying_assets TEXT,
        maturity_date TEXT,
        currency TEXT,
        min_investment REAL,
        distribution_channels TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS livmc_client_protection (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER NOT NULL,
        protection_type TEXT NOT NULL,
        provider_id INTEGER,
        coverage_amount REAL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS livmc_voice_procedure (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER NOT NULL,
        procedure_type TEXT NOT NULL,
        description TEXT,
        effective_date TEXT,
        next_review TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    # --- PSD2 / Consumer Credit / Insurance ---
    """
    CREATE TABLE IF NOT EXISTS psd2_aspsp (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER NOT NULL,
        bic TEXT,
        psd2_license TEXT,
        strong_customer_auth_applied BOOLEAN,
        api_version TEXT,
        regulatory_status TEXT,
        home_member_state TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS psd2_aisp (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER NOT NULL,
        registration_number TEXT,
        registration_id TEXT,
        access_scope TEXT,
        valid_from TEXT,
        valid_to TEXT,
        status TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS psd2_pisp (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER NOT NULL,
        registration_number TEXT,
        authorization_status TEXT,
        home_member_state TEXT,
        psd3_transition_status TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS psd2_consent (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER NOT NULL,
        aspsp_id INTEGER NOT NULL,
        consent_type TEXT,
        accounts_accessed TEXT,
        payment_count_limit INTEGER,
        used_count INTEGER,
        valid_from TEXT,
        valid_to TEXT,
        status TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS psd2_incident_report (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        aspsp_id INTEGER NOT NULL,
        incident_type TEXT,
        severity TEXT,
        description TEXT,
        reported_to_bde BOOLEAN,
        reported_date TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sepa_payment_rule (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scheme_version TEXT,
        payment_type TEXT,
        service_level TEXT,
        local_instrument TEXT,
        category_purpose TEXT,
        cut_off_time TEXT,
        settlement_days INTEGER,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS consumer_credit_contract (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lender_id INTEGER NOT NULL,
        borrower_id INTEGER NOT NULL,
        credit_type TEXT,
        principal_amount REAL,
        annual_percentage_rate REAL,
        total_amount REAL,
        term_months INTEGER,
        purpose TEXT,
        signing_date TEXT,
        status TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS consumer_credit_disclosure (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contract_id INTEGER NOT NULL,
        fap REAL,
        total_cost REAL,
        regular_payment REAL,
        amortization_schedule_url TEXT,
        right_of_withdrawal BOOLEAN,
        early_repayment_penalty REAL,
        url TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS consumer_credit_overindebtedness (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        borrower_id INTEGER NOT NULL,
        declared_date TEXT,
        total_debt REAL,
        monthly_income REAL,
        unsecured_debt REAL,
        procedure_status TEXT,
        court_reference TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS idd_distributor (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER NOT NULL,
        registration_number TEXT,
        insurance_ao TEXT,
        products_covered TEXT,
        professional_indemnity BOOLEAN,
        training_certified BOOLEAN,
        status TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS idd_product_uci (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        product_type TEXT,
        risk_coverage TEXT,
        cost_breakdown TEXT,
        exit_costs TEXT,
        taxes TEXT,
        version TEXT,
        status TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS solvency_ii_entity (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER NOT NULL,
        entity_type TEXT,
        solvency_capital_requirement REAL,
        minimum_capital_requirement REAL,
        solvency_ratio REAL,
        reporting_date TEXT,
        home_supervisor TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS solvency_ii_sfp (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER NOT NULL,
        reporting_period TEXT,
        fund_breakdown TEXT,
        asset_allocation TEXT,
        url TEXT,
        status TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    # --- SFDR ---
    """
    CREATE TABLE IF NOT EXISTS sfdr_product (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name TEXT NOT NULL,
        product_type TEXT NOT NULL,
        sustainability_strategy TEXT,
        principal_adverse_impact TEXT,
        paci_aggregated TEXT,
        paci_detailed_url TEXT,
        distribution_country TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sfdr_paci_indicator (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        indicator_code TEXT NOT NULL,
        indicator_name TEXT NOT NULL,
        value REAL,
        unit TEXT,
        reference_period TEXT,
        methodology TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sfdr_entity_paci (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER NOT NULL,
        reporting_year INTEGER NOT NULL,
        aggregated_paci TEXT,
        sectoral_decarbonization TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sfdr_pre_contractual (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        document_type TEXT NOT NULL,
        url TEXT NOT NULL,
        published_date TEXT,
        version TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sfdr_annual_report (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER NOT NULL,
        reporting_year INTEGER NOT NULL,
        paci_results TEXT,
        engagement_activities TEXT,
        good_practice_examples TEXT,
        url TEXT,
        published_date TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    # --- Transparency ---
    """
    CREATE TABLE IF NOT EXISTS transparency_issuer (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        issuer_id INTEGER NOT NULL,
        listing_market TEXT,
        ticker TEXT,
        reporting_frequency TEXT,
        home_member_state TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS transparency_regulated_information (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        issuer_id INTEGER NOT NULL,
        info_type TEXT,
        publication_date TEXT,
        content_url TEXT,
        filing_reference TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS transparency_voting_rights (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        issuer_id INTEGER NOT NULL,
        shareholder_id INTEGER NOT NULL,
        voting_rights_pct REAL,
        date_acquired TEXT,
        date_reported TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS transparency_internal_rule (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER NOT NULL,
        designated_persons TEXT,
        internal_procedure TEXT,
        retention_period TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    # --- AIFMD / UCITS ---
    """
    CREATE TABLE IF NOT EXISTS aifmd_fund (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fund_name TEXT NOT NULL,
        aifm_id INTEGER,
        fund_type TEXT NOT NULL,
        registration_date TEXT NOT NULL,
        home_member_state TEXT,
        cross_border_passport BOOLEAN NOT NULL DEFAULT 0,
        total_aum_eur REAL,
        investor_type TEXT,
        lock_up_period TEXT,
        redemption_frequency TEXT,
        leverage_method TEXT,
        leverage_max_pct REAL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS aifmd_regulatory_report (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fund_id INTEGER NOT NULL REFERENCES aifmd_fund(id) ON DELETE CASCADE,
        report_type TEXT NOT NULL,
        reporting_period TEXT,
        url TEXT,
        filed_date TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS aifmd_liquidity_management (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fund_id INTEGER NOT NULL REFERENCES aifmd_fund(id) ON DELETE CASCADE,
        redemption_suspended BOOLEAN NOT NULL DEFAULT 0,
        suspension_date TEXT,
        gating_applied BOOLEAN NOT NULL DEFAULT 0,
        swing_price_applied BOOLEAN NOT NULL DEFAULT 0,
        side_pocket_applied BOOLEAN NOT NULL DEFAULT 0,
        stress_test_result TEXT,
        valuation_frequency TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ucits_fund (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fund_name TEXT NOT NULL,
        management_company TEXT,
        registration_date TEXT NOT NULL,
        home_member_state TEXT,
        cross_border_passport BOOLEAN NOT NULL DEFAULT 0,
        total_aum_eur REAL,
        depositary_id INTEGER,
        krid_url TEXT,
        investment_strategy TEXT,
        risk_profile TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ucits_regulatory_report (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fund_id INTEGER NOT NULL REFERENCES ucits_fund(id) ON DELETE CASCADE,
        report_type TEXT NOT NULL,
        reporting_period TEXT,
        url TEXT,
        filed_date TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    # --- CRD / BRRD / EMIR ---
    """
    CREATE TABLE IF NOT EXISTS crd_capital_position (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER NOT NULL,
        reporting_date TEXT NOT NULL,
        cet1_ratio REAL,
        tier1_ratio REAL,
        total_capital_ratio REAL,
        cet1_amount REAL,
        tier1_amount REAL,
        total_capital_amount REAL,
        leverage_ratio REAL,
        risk_weighted_assets REAL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS crd_stress_test (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER NOT NULL,
        test_date TEXT NOT NULL,
        scenario_name TEXT,
        cet1_impact_pct REAL,
        tier1_impact_pct REAL,
        capital_ratio_post_test REAL,
        competent_authority TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS brrd_bail_in (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER NOT NULL,
        total_eligible_liabilities REAL,
        mrel_target_pct REAL,
        mrel_compliance_pct REAL,
        internal_mrel REAL,
        resolution_status TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS emir_trade_report (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trade_id TEXT NOT NULL,
        asset_class TEXT NOT NULL,
        instrument_class TEXT NOT NULL,
        clearing_obligation_applied BOOLEAN NOT NULL DEFAULT 0,
        reporting_delay_days INTEGER,
        counterparty_type TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS emir_clearing_member (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER NOT NULL,
        emir_registration TEXT NOT NULL,
        clearing_type TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    # --- Lineas de criterio ---
    """
    CREATE TABLE IF NOT EXISTS linea_criterio (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT NOT NULL,
        cuestion_practica TEXT NOT NULL,
        descripcion TEXT,
        criterio_dominante TEXT,
        matices TEXT,
        excepciones TEXT,
        ambitos TEXT,
        ultimo_cambio TEXT,
        estado TEXT NOT NULL DEFAULT 'borrador',
        autor_id INTEGER,
        revisor_id INTEGER,
        activo BOOLEAN NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS linea_criterio_referencia (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        linea_id INTEGER NOT NULL REFERENCES linea_criterio(id) ON DELETE CASCADE,
        documento_referencia TEXT NOT NULL,
        tipo_documento TEXT,
        organismo_emisor TEXT,
        fecha TEXT,
        rol_en_linea TEXT,
        orden INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(linea_id, documento_referencia)
    )
    """,
    """
    INSERT INTO linea_criterio (
        titulo, cuestion_practica, descripcion, criterio_dominante, matices,
        excepciones, ambitos, ultimo_cambio, estado, autor_id, revisor_id, activo
    ) VALUES
        ('IVA reducido en restauracion', 'Se aplica el tipo reducido del IVA a servicios de restauracion?', 'Analisis del criterio del Tribunal Supremo sobre IVA reducido en restauracion.', 'El tipo reducido exige un servicio efectivo de restauracion.', 'Debe distinguirse de la mera entrega de alimentos.', 'No aplica a ventas sin servicio adicional.', '["tributario","jurisprudencia_tributaria"]', NULL, 'vigente', 1, 1, 1),
        ('Comisiones preferencia e indiferencia', 'Pueden cobrarse comisiones que favorezcan a unos clientes sobre otros?', 'Limites de las comisiones bajo MiFID II y criterios CNMV.', 'Son admisibles con transparencia total y sin perjuicio al cliente.', 'Requiere registro documental y disclosure.', 'No aplica igual a clientes institucionales.', '["mifid_ii","jurisprudencia_mercantil_regulatoria"]', NULL, 'vigente', 1, 1, 1),
        ('Ejecucion preferente de ordenes', 'Que criterios garantizan la best execution?', 'Obligaciones de best execution bajo MiFID.', 'Debe obtenerse el mejor resultado global para el cliente.', 'Incluye precio, coste, rapidez y probabilidad.', 'Puede modularse por instrucciones especificas del cliente.', '["mifid_ii","jurisprudencia_mercantil_regulatoria"]', NULL, 'vigente', 1, 1, 1),
        ('Adecuacion y conveniencia de productos', 'Cuando aplica adecuacion frente a conveniencia?', 'Diferencia entre suitability y appropriateness.', 'Suitability aplica a asesoramiento; appropriateness a ejecucion.', 'La informacion del cliente debe estar actualizada.', 'Productos no complejos pueden flexibilizar la evaluacion.', '["mifid_ii","jurisprudencia_mercantil_regulatoria"]', NULL, 'vigente', 1, 1, 1),
        ('Informacion privilegiada y listas insider', 'Que obligaciones existen sobre informacion privilegiada?', 'Obligaciones MAR para insiders y listas de vigilancia.', 'Debe existir lista insider y controles de acceso.', 'Las listas deben actualizarse en tiempo real.', 'Excepciones limitadas por necesidad de conocimiento.', '["mar","jurisprudencia_mercantil_regulatoria"]', NULL, 'vigente', 1, 1, 1),
        ('Gobierno de productos', 'Como se define el mercado objetivo de un producto?', 'Obligaciones de product governance bajo MiFID II.', 'El fabricante y el distribuidor deben respetar el target market.', 'Se requiere revision periodica del producto.', 'Clientes profesionales tienen un tratamiento distinto.', '["mifid_ii","jurisprudencia_mercantil_regulatoria"]', NULL, 'vigente', 1, 1, 1),
        ('Comunicacion de indicios de LP', 'Cuando debe comunicarse un indicio a SEPBLAC?', 'Deberes de comunicacion de operaciones sospechosas.', 'La comunicacion debe hacerse sin demora y sin tipping-off.', 'La confidencialidad es obligatoria.', 'Excepcion limitada para defensa judicial.', '["aml_cft","jurisprudencia_pbcft"]', NULL, 'vigente', 1, 1, 1)
    """,
    """
    INSERT INTO linea_criterio_referencia (linea_id, documento_referencia, tipo_documento, organismo_emisor, fecha, rol_en_linea, orden) VALUES
        (1, 'STS-2847/2025', 'sentencia', 'Tribunal Supremo', '2025-06-15', 'doctrina_principal', 1),
        (2, 'Circular 3/2015 CNMV', 'circular', 'CNMV', '2015-05-14', 'base_regulatoria', 1),
        (3, 'Reg. UE 2017/565', 'reglamento', 'Union Europea', '2016-10-07', 'base_legal', 1),
        (4, 'Directiva 2014/65/UE', 'directiva', 'Union Europea', '2014-06-04', 'base_legal', 1),
        (5, 'Reg. UE 596/2014', 'reglamento', 'Union Europea', '2014-04-16', 'base_legal', 1),
        (6, 'Circular 5/2018 CNMV', 'circular', 'CNMV', '2018-09-10', 'base_regulatoria', 1),
        (7, 'Ley 10/2010 PREV LPFT', 'ley', 'BOE', '2010-07-26', 'base_legal', 1)
    """,
    # --- Playbooks y evidencias ---
    """
    CREATE TABLE IF NOT EXISTS playbook_operativo (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT NOT NULL UNIQUE,
        nombre TEXT NOT NULL,
        obligacion_codigo TEXT,
        descripcion TEXT,
        frecuencia TEXT,
        owner_rol TEXT,
        owner_id TEXT,
        sistema_apoyo TEXT,
        errores_frecuentes TEXT,
        estado TEXT NOT NULL,
        version INTEGER NOT NULL DEFAULT 1,
        version_anterior_id INTEGER,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS playbook_step (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        playbook_id INTEGER NOT NULL REFERENCES playbook_operativo(id) ON DELETE CASCADE,
        orden INTEGER NOT NULL,
        titulo TEXT NOT NULL,
        descripcion TEXT,
        tipo_paso TEXT,
        responsable_rol TEXT,
        input_requerido TEXT,
        output_esperado TEXT,
        prerrequisito_step_id INTEGER REFERENCES playbook_step(id),
        checklist TEXT,
        activo BOOLEAN NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS evidencia_control (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT NOT NULL UNIQUE,
        playbook_id INTEGER NOT NULL REFERENCES playbook_operativo(id) ON DELETE CASCADE,
        step_id INTEGER REFERENCES playbook_step(id),
        nombre TEXT NOT NULL,
        descripcion TEXT,
        tipo_evidencia TEXT,
        formato_requerido TEXT,
        conservacion_dias INTEGER,
        obligatoria BOOLEAN NOT NULL DEFAULT 0,
        estado TEXT,
        capturado_en TEXT,
        verificado_por TEXT,
        verificado_en TEXT,
        nota TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    INSERT INTO playbook_operativo (
        codigo, nombre, obligacion_codigo, descripcion, frecuencia, owner_rol, estado, version
    ) VALUES
        ('PLAYBOOK-CNMV-IR', 'Preparacion y remision de informacion reservada a la CNMV', 'CNMV-IR-RESERVADA', 'Procedimiento operativo para informacion reservada CNMV.', 'mensual', 'compliance', 'activo', 1),
        ('PLAYBOOK-SEPBLAC-INDICIO', 'Comunicacion de operativas sospechosas por indicio', 'SEPBLAC-INDICIO', 'Procedimiento operativo para Modelo 19 SEPBLAC.', 'eventual', 'compliance', 'activo', 1)
    """,
    """
    INSERT INTO playbook_step (
        playbook_id, orden, titulo, descripcion, tipo_paso, responsable_rol,
        input_requerido, output_esperado, prerrequisito_step_id, checklist, activo
    ) VALUES
        (1, 1, 'Recopilar datos contables mensuales', 'Extraer datos contables y financieros del mes.', 'accion', 'contabilidad', 'Libro mayor y extractos', 'Dataset del periodo', NULL, '["Verificar integridad de datos","Conciliar balances","Validar cuentas maestras"]', 1),
        (1, 2, 'Preparar estados financieros reservados', 'Elaborar estados de informacion reservada.', 'captura', 'contabilidad', 'Dataset del periodo', 'Estados reservados preparados', 1, '["Formato CNMV vigente","Cruce con estados publicos","Notas completas"]', 1),
        (1, 3, 'Revision de compliance', 'Revision del responsable de compliance.', 'revision', 'compliance', 'Estados reservados', 'Informe de revision firmado', 2, '["Validar ratios prudenciales","Verificar limites de riesgo","Confirmar cumplimiento normativo"]', 1),
        (1, 4, 'Aprobacion por direccion', 'Aprobacion formal por direccion.', 'aprobacion', 'direccion_general', 'Estados y revision compliance', 'Acta de aprobacion', 3, '["Aprobacion por escrito","Registro de aprobacion"]', 1),
        (1, 5, 'Remision a la CNMV', 'Envio electronico a CNMV.', 'accion', 'compliance', 'Estados aprobados', 'Acuse de recibo', 4, '["Verificar fecha limite","Confirmar acuse de recibo","Archivar evidencia"]', 1)
    """,
    """
    INSERT INTO evidencia_control (
        codigo, playbook_id, step_id, nombre, descripcion, tipo_evidencia,
        formato_requerido, conservacion_dias, obligatoria, estado
    ) VALUES
        ('EVID-CNMV-IR-001', 1, NULL, 'Estados financieros reservados del periodo', 'Estados de informacion reservada del periodo.', 'documento', 'pdf', 3650, 1, 'requerido'),
        ('EVID-CNMV-IR-002', 1, 3, 'Informe de revision de compliance', 'Informe validando cumplimiento normativo.', 'documento', 'pdf', 3650, 1, 'requerido'),
        ('EVID-CNMV-IR-003', 1, 4, 'Acta de aprobacion por direccion', 'Documento formal de aprobacion.', 'aprobacion', 'pdf', 3650, 1, 'requerido'),
        ('EVID-CNMV-IR-004', 1, 5, 'Acuse de recibo CNMV', 'Confirmacion electronica de envio.', 'log', 'xml', 3650, 1, 'requerido')
    """,
    # --- Riesgos, controles y pruebas ---
    """
    CREATE TABLE IF NOT EXISTS riesgo_regulatorio (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT NOT NULL UNIQUE,
        nombre TEXT NOT NULL,
        descripcion TEXT,
        obligacion_codigo TEXT,
        categoria TEXT,
        severidad TEXT,
        probabilidad TEXT,
        riesgo_inherente TEXT,
        area_responsable TEXT,
        owner_rol TEXT,
        estado TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS control_interno (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT NOT NULL UNIQUE,
        nombre TEXT NOT NULL,
        descripcion TEXT,
        tipo_control TEXT,
        frecuencia TEXT,
        owner_rol TEXT,
        sistema_apoyo TEXT,
        estado TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS riesgo_control_link (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        riesgo_id INTEGER NOT NULL REFERENCES riesgo_regulatorio(id) ON DELETE CASCADE,
        control_id INTEGER NOT NULL REFERENCES control_interno(id) ON DELETE CASCADE,
        efectividad TEXT,
        riesgo_residual TEXT,
        frecuencia_prueba TEXT,
        criterio_suficiencia TEXT,
        caducidad_dias INTEGER,
        activo BOOLEAN NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(riesgo_id, control_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS prueba_control (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        link_id INTEGER NOT NULL REFERENCES riesgo_control_link(id) ON DELETE CASCADE,
        fecha_prueba TEXT NOT NULL,
        resultado TEXT NOT NULL,
        evidencia_descripcion TEXT,
        evidencia_url TEXT,
        ejecutado_por TEXT,
        nota TEXT,
        activo BOOLEAN NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    INSERT INTO riesgo_regulatorio (
        codigo, nombre, descripcion, obligacion_codigo, categoria, severidad,
        probabilidad, riesgo_inherente, area_responsable, owner_rol, estado
    ) VALUES
        ('RIESGO-CNMV-001', 'No presentacion de informes CNMV', 'Incumplimiento de reporting periodico ante CNMV.', 'CNMV-IR-RESERVADA', 'reporting', 'alta', 'media', 'alto', 'compliance', 'compliance_officer', 'identificado'),
        ('RIESGO-CNMV-002', 'Informacion inexacta o incompleta', 'Presentacion de datos erroneos ante regulador.', 'CNMV-IR-RESERVADA', 'calidad_datos', 'alta', 'baja', 'medio', 'finanzas', 'cfo', 'identificado'),
        ('RIESGO-MIFID-001', 'Incumplimiento MiFID adecuacion cliente', 'No evaluar adecuadamente la conveniencia del producto.', 'MICRO-MIFID-001', 'mifid', 'alta', 'media', 'alto', 'compliance', 'compliance_officer', 'identificado'),
        ('RIESGO-PBCFT-001', 'Incumplimiento prevencion blanqueo', 'No aplicar KYC o no reportar operaciones sospechosas.', 'MICRO-PBCFT-001', 'pbcft', 'critica', 'media', 'alto', 'compliance', 'mlco', 'identificado'),
        ('RIESGO-IVA-001', 'Retraso en presentacion modelo 303', 'Multa por presentacion fuera de plazo del IVA.', 'OBL-IVA-303', 'fiscal', 'media', 'baja', 'medio', 'finanzas', 'responsable_fiscal', 'identificado')
    """,
    """
    INSERT INTO control_interno (
        codigo, nombre, descripcion, tipo_control, frecuencia, owner_rol,
        sistema_apoyo, estado
    ) VALUES
        ('CTRL-REPOR-001', 'Revision quincenal datos CNMV', 'Revisar y validar datos antes del envio.', 'preventivo', 'quincenal', 'compliance', 'esdata', 'activo'),
        ('CTRL-REPOR-002', 'Doble firma informes periodicos', 'Dos personas revisan y firman antes de envio.', 'detectivo', 'por_envio', 'finanzas', 'esdata', 'activo'),
        ('CTRL-MIFID-001', 'Checklist adecuacion MiFID', 'Checklist obligatorio antes de recomendar producto.', 'preventivo', 'por_operacion', 'compliance', 'esdata', 'activo'),
        ('CTRL-KYC-001', 'Debida diligencia cliente nuevo', 'KYC completo antes de iniciar relacion.', 'preventivo', 'por_onboarding', 'compliance', 'esdata', 'activo'),
        ('CTRL-FISCAL-001', 'Calendario presentaciones fiscales', 'Alertas automatizadas de plazos fiscales.', 'preventivo', 'mensual', 'finanzas', 'esdata', 'activo')
    """,
    """
    INSERT INTO riesgo_control_link (
        riesgo_id, control_id, efectividad, riesgo_residual, frecuencia_prueba,
        criterio_suficiencia, caducidad_dias, activo
    ) VALUES
        (1, 1, 'no_evaluada', 'no_evaluada', 'trimestral', 'evidencia documentada por prueba', 90, 1),
        (1, 2, 'no_evaluada', 'no_evaluada', 'trimestral', 'evidencia documentada por prueba', 90, 1),
        (3, 3, 'no_evaluada', 'no_evaluada', 'mensual', 'evidencia documentada por prueba', 30, 1),
        (4, 4, 'no_evaluada', 'no_evaluada', 'por_onboarding', 'evidencia documentada por prueba', 180, 1),
        (5, 5, 'no_evaluada', 'no_evaluada', 'mensual', 'evidencia documentada por prueba', 30, 1)
    """,
    """
    INSERT INTO prueba_control (
        link_id, fecha_prueba, resultado, evidencia_descripcion, ejecutado_por, activo
    ) VALUES
        (1, '2025-01-15', 'ok', 'Revision trimestral documentada', 'compliance', 1),
        (5, '2025-02-05', 'ok', 'Control fiscal ejecutado', 'responsable_fiscal', 1)
    """,
    # --- Tablas editoriales (corpus autoritativo) ---
    """
    CREATE TABLE IF NOT EXISTS nota_editorial_interna (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT NOT NULL,
        resumen_ejecutivo TEXT,
        contexto TEXT,
        impacto_practico TEXT,
        advertencias TEXT,
        fuente_oficial_referencia TEXT,
        documento_origen_id INTEGER REFERENCES documento_interpretativo(id),
        autor_id TEXT NOT NULL,
        revisor_id TEXT,
        estado TEXT NOT NULL DEFAULT 'borrador',
        tipo_contenido TEXT NOT NULL,
        fecha_creacion TEXT,
        fecha_revision TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now')),
        fuente_verificada BOOLEAN NOT NULL DEFAULT 0
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS posicion_interpretativa (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT NOT NULL,
        descripcion TEXT,
        contenido TEXT,
        fuente_oficial_referencia TEXT,
        documento_origen_id INTEGER REFERENCES documento_interpretativo(id),
        autor_id TEXT NOT NULL,
        revisor_id TEXT,
        estado TEXT NOT NULL DEFAULT 'borrador',
        version INTEGER NOT NULL DEFAULT 1,
        vigencia_desde TEXT,
        vigencia_hasta TEXT,
        version_anterior_id INTEGER REFERENCES posicion_interpretativa(id),
        fecha_creacion TEXT,
        fecha_revision TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now')),
        fuente_verificada BOOLEAN NOT NULL DEFAULT 0
    )
    """,
    # --- Seed: editorial corpus ---
    """
    INSERT INTO nota_editorial_interna (
        titulo, resumen_ejecutivo, contexto, impacto_practico, advertencias,
        fuente_oficial_referencia, autor_id, estado, tipo_contenido,
        fecha_creacion, fecha_revision, created_at, updated_at
    ) VALUES (
        'Resumen operativo: Circular CNMV 9/2008',
        'Resumen de los principales cambios de la circular',
        'La CNMV publicó la circular 9/2008 estableciendo requisitos para entidades de inversión',
        'Alto - afecta a todas las entidades supervisadas',
        'Verificar vigencia en BOE',
        'BOE-A-2009-133',
        'compliance',
        'vigente',
        'resumen_interno',
        '2024-01-15',
        '2024-06-20',
        datetime('now'),
        datetime('now')
    )
    """,
    """
    INSERT INTO documento_interpretativo (
        tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente, ambito,
        referencia, fecha, titulo, texto, url_fuente, referencia_boe
    ) VALUES (
        'circular', 'CNMV', 'es', 'boe', 'mercados_financieros',
        'CNMV-9-2008', '2009-01-05', 'Circular CNMV 9/2008',
        'Documento de origen para las notas y posiciones editoriales de prueba.',
        'https://example.invalid/cnmv/9-2008', 'BOE-A-2009-133'
    )
    """,
    """
    INSERT INTO posicion_interpretativa (
        titulo, descripcion, contenido, fuente_oficial_referencia, documento_origen_id, autor_id,
        estado, version, vigencia_desde, vigencia_hasta,
        fecha_creacion, fecha_revision, created_at, updated_at
    ) VALUES (
        'Criterio interno: adecuación MiFID II',
        'Criterio interno sobre adecuación y conveniencia de productos bajo MiFID II.',
        'La entidad debe documentar la evaluación de adecuación y conservar la evidencia de idoneidad del cliente.',
        'eurl:2014:65',
        NULL,
        'compliance',
        'vigente',
        1,
        '2024-03-10',
        NULL,
        '2024-03-10',
        '2024-07-15',
        datetime('now'),
        datetime('now')
    )
    """,
    """
    INSERT INTO empresa (id, nombre, nif, domicilio, fuente_inicial) VALUES
        (1, 'ALVAREZ GARCIA GANADERIA, S.L.', 'B12345678', 'Calle Mayor 1, Madrid', 'seed'),
        (2, 'MURILLO & BARRERO, SOCIEDAD LIMITADA', 'B87654321', 'Avenida Europa 2, Sevilla', 'seed')
    """,
    """
    INSERT INTO entity_identifiers (
        id, empresa_id, lei, nombre_legal, pais, estado, vigencia_desde,
        vigencia_hasta, vlei_status, vlei_cred_url, fuente_ref
    ) VALUES (
        1, 1, '5493001KJTIURC11JN06', 'BBVA BANCO POPULAR ESPAÑOL', 'ES', 'active',
        '2024-01-01', NULL, 'not_issued', NULL, 'seed'
    )
    """,
    """
    INSERT INTO entity_aliases (empresa_id, alias, alias_normalizado, fuente, confianza) VALUES
        (1, 'BBVA', 'bbva', 'seed', 0.99),
        (1, 'BANCO BILBAO VIZCAYA ARGENTARIA', 'banco bilbao vizcaya argentaria', 'seed', 0.95)
    """,
    """
    INSERT INTO empresa (id, nombre, nif, domicilio, fuente_inicial) VALUES
        (3, 'INVERSIONES ALFA HOLDING, S.A.', 'A11223344', 'Paseo de la Castellana 10, Madrid', 'seed'),
        (4, 'SERVICIOS CORPORATIVOS BETA, S.L.', 'B44332211', 'Gran Via 20, Madrid', 'seed')
    """,
    """
    CREATE TABLE IF NOT EXISTS ownership_share (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL REFERENCES empresa(id) ON DELETE CASCADE,
        titular_id INTEGER,
        titular_tipo TEXT,
        titular_nombre TEXT,
        porcentaje REAL,
        tipo_participacion TEXT,
        vigencia_desde TEXT,
        vigencia_hasta TEXT,
        fuente TEXT,
        fuente_ref TEXT,
        documento_id INTEGER REFERENCES documento_interpretativo(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ownership_relation (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_origen_id INTEGER NOT NULL REFERENCES empresa(id) ON DELETE CASCADE,
        empresa_destino_id INTEGER NOT NULL REFERENCES empresa(id) ON DELETE CASCADE,
        tipo_relacion TEXT NOT NULL,
        porcentaje REAL,
        vigencia_desde TEXT,
        vigencia_hasta TEXT,
        fuente TEXT,
        fuente_ref TEXT,
        documento_id INTEGER REFERENCES documento_interpretativo(id),
        nota TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ubo_record (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL REFERENCES empresa(id) ON DELETE CASCADE,
        nombre_persona TEXT NOT NULL,
        nacionalidad TEXT,
        fecha_nacimiento TEXT,
        pais_residencia TEXT,
        tipo_ubo TEXT,
        porcentaje_control REAL,
        umbral_superado BOOLEAN,
        vigencia_desde TEXT,
        vigencia_hasta TEXT,
        fuente TEXT,
        fuente_ref TEXT,
        documento_id INTEGER REFERENCES documento_interpretativo(id),
        nota TEXT
    )
    """,
    """
    INSERT INTO ownership_share (
        empresa_id, titular_id, titular_tipo, titular_nombre, porcentaje,
        tipo_participacion, vigencia_desde, vigencia_hasta, fuente, fuente_ref
    ) VALUES
        (2, 1, 'empresa', 'ALVAREZ GARCIA GANADERIA, S.L.', 60.0, 'directa', '2023-01-01', NULL, 'seed', 'ownership-seed-001'),
        (2, 3, 'empresa', 'INVERSIONES ALFA HOLDING, S.A.', 25.0, 'indirecta', '2023-01-01', NULL, 'seed', 'ownership-seed-002'),
        (2, NULL, 'persona_fisica', 'Carlos Alvarez Garcia', 15.0, 'directa', '2023-01-01', NULL, 'seed', 'ownership-seed-003')
    """,
    """
    INSERT INTO ownership_relation (
        empresa_origen_id, empresa_destino_id, tipo_relacion, porcentaje,
        vigencia_desde, vigencia_hasta, fuente, fuente_ref, nota
    ) VALUES
        (2, 1, 'filial', 60.0, '2023-01-01', NULL, 'seed', 'ownership-rel-001', 'Relacion societaria principal'),
        (2, 3, 'absorbente', 25.0, '2023-01-01', NULL, 'seed', 'ownership-rel-002', 'Grupo corporativo'),
        (3, 4, 'filial', 80.0, '2023-01-01', NULL, 'seed', 'ownership-rel-003', 'Cadena de control')
    """,
    """
    INSERT INTO ubo_record (
        empresa_id, nombre_persona, nacionalidad, fecha_nacimiento, pais_residencia,
        tipo_ubo, porcentaje_control, umbral_superado, vigencia_desde, vigencia_hasta,
        fuente, fuente_ref, nota
    ) VALUES
        (2, 'Carlos Alvarez Garcia', 'ES', '1980-04-18', 'ES', 'control_directo', 55.0, 1, '2023-01-01', NULL, 'seed', 'ubo-seed-001', 'Socio de control'),
        (2, 'Lucia Murillo Barrero', 'ES', '1985-09-21', 'ES', 'control_indirecto', 20.0, 1, '2023-01-01', NULL, 'seed', 'ubo-seed-002', 'Participacion indirecta')
    """,
    # --- Normas (metadatos de referencia) ---
    """
    INSERT INTO norma (
        codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente,
        tipo_documento, ambito, estado_cobertura, vigente_desde
    )
    VALUES (
        'LIVA', 'Ley del Impuesto sobre el Valor Anadido', 'BOE-A-1992-28740',
        'https://www.boe.es/eli/es/l/1992/12/28/37', 'es', 'boe',
        'ley', 'tributario', 'ingestada', '1993-01-01'
    )
    """,
    """
    INSERT INTO norma (
        codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente,
        tipo_documento, ambito, estado_cobertura, vigente_desde
    )
    VALUES (
        'ITPAJD',
        'Texto refundido del Impuesto sobre Transmisiones Patrimoniales y Actos Juridicos Documentados',
        'BOE-A-1993-253',
        'https://www.boe.es/eli/es/rdlg/1993/09/24/1/con',
        'es',
        'boe',
        'real_decreto_legislativo',
        'tributario',
        'ingestada',
        '1993-09-25'
    )
    """,
    """
    INSERT INTO norma (
        codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente,
        tipo_documento, ambito, estado_cobertura, vigente_desde
    )
    VALUES (
        'RIRNR',
        'Real Decreto 435/1995, de 27 de marzo, por el que se aprueba el Reglamento del Impuesto sobre la Renta de no Residentes',
        'BOE-A-1995-7256',
        NULL,
        'es',
        'boe',
        'real_decreto',
        'tributario',
        'vigente',
        '1995-03-28'
    )
    """,
    # --- LIVA 91: fixture de test con texto realista del BOE ---
    # Este no es un placeholder de producción; el worker BOE ingesta el texto real.
    # Aquí usamos un extracto representativo para que los tests verifiquen búsqueda y estructura.
    """
    INSERT INTO articulo (norma_id, numero, titulo, tipo)
    SELECT id, '91', 'Tipos impositivos reducidos', 'articulo' FROM norma WHERE codigo = 'LIVA'
    """,
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT a.id, 'Artículo 91. Tipos impositivos reducidos.
Uno. Se aplicará el tipo reducido a las siguientes operaciones:
1. Las entregas de bienes de primera necesidad.
2. Los servicios de hostelería y restaurante.
Dos. Se aplicará un tipo superreducido al pan, leche y libros.', '1993-01-01', NULL, 'a91'
    FROM articulo a
    JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'LIVA' AND a.numero = '91'
    """,
    # --- ITPAJD 7: fixture para validar la nueva cobertura ---
    """
    INSERT INTO articulo (norma_id, numero, titulo, tipo)
    SELECT id, '7', 'Transmisiones patrimoniales sujetas', 'articulo'
    FROM norma WHERE codigo = 'ITPAJD'
    """,
    """
    INSERT INTO articulo (norma_id, numero, titulo, tipo)
    SELECT id, '31', 'Rendimientos del capital mobiliario', 'articulo'
    FROM norma WHERE codigo = 'RIRNR'
    """,
    """
    INSERT INTO articulo (norma_id, numero, titulo, tipo)
    SELECT id, '32', 'Tipos de retencion', 'articulo'
    FROM norma WHERE codigo = 'RIRNR'
    """,
    """
    INSERT INTO articulo (norma_id, numero, titulo, tipo)
    SELECT id, '33', 'Obligacion de retener e ingresar a cuenta', 'articulo'
    FROM norma WHERE codigo = 'RIRNR'
    """,
    """
    INSERT INTO articulo (norma_id, numero, titulo, tipo)
    SELECT id, '34', 'Nacimiento de la obligacion de retener', 'articulo'
    FROM norma WHERE codigo = 'RIRNR'
    """,
    """
    INSERT INTO articulo (norma_id, numero, titulo, tipo)
    SELECT id, '35', 'Declaracion e ingreso de retenciones', 'articulo'
    FROM norma WHERE codigo = 'RIRNR'
    """,
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT a.id, 'Articulo 7. Son transmisiones patrimoniales sujetas:
1. Las transmisiones onerosas por actos inter vivos de toda clase de bienes y derechos.
2. La constitucion de derechos reales, prestamos, fianzas, arrendamientos y pensiones.',
    '1993-09-25', NULL, 'itpajd-a7'
    FROM articulo a
    JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'ITPAJD' AND a.numero = '7'
    """,
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT a.id, 'Articulo 31. Constituyen rendimientos del capital mobiliario los dividendos, las rentas derivadas de la participacion en fondos propios y otros rendimientos obtenidos por no residentes sin establecimiento permanente en Espana.',
    '1995-03-28', NULL, 'rirnr-a31'
    FROM articulo a
    JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'RIRNR' AND a.numero = '31'
    """,
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT a.id, 'Articulo 32. El tipo de retencion aplicable se determinara segun la naturaleza de la renta, incluyendo los tipos previstos para dividendos, intereses y demas rentas sujetas a retencion.',
    '1995-03-28', NULL, 'rirnr-a32'
    FROM articulo a
    JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'RIRNR' AND a.numero = '32'
    """,
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT a.id, 'Articulo 33. Estaran obligados a retener e ingresar a cuenta quienes satisfagan rentas sujetas al Impuesto sobre la Renta de no Residentes en los supuestos previstos reglamentariamente.',
    '1995-03-28', NULL, 'rirnr-a33'
    FROM articulo a
    JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'RIRNR' AND a.numero = '33'
    """,
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT a.id, 'Articulo 34. La obligacion de retener nacera en el momento de la exigibilidad de la renta satisfecha o abonada, conforme a las reglas del reglamento.',
    '1995-03-28', NULL, 'rirnr-a34'
    FROM articulo a
    JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'RIRNR' AND a.numero = '34'
    """,
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT a.id, 'Articulo 35. La declaracion e ingreso de las retenciones practicadas se realizara en la forma y plazos establecidos por la normativa tributaria aplicable.',
    '1995-03-28', NULL, 'rirnr-a35'
    FROM articulo a
    JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'RIRNR' AND a.numero = '35'
    """,
    # --- Materias (taxonomía curada) ---
    """
    INSERT INTO materia (slug, etiqueta)
    VALUES ('tipo-reducido-iva', 'Tipo reducido IVA')
    """,
    # --- Enlace materia <-> artículo (requiere que LIVA 91 exista) ---
    """
    INSERT INTO articulo_materia (articulo_id, materia_id, relevancia)
    SELECT a.id, m.id, 3
    FROM articulo a
    JOIN norma n ON n.id = a.norma_id
    JOIN materia m ON m.slug = 'tipo-reducido-iva'
    WHERE n.codigo = 'LIVA' AND a.numero = '91'
    """,
    # --- Doctrina de referencia ---
    """
    INSERT INTO documento_interpretativo (
        tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente, ambito, referencia, fecha, titulo, texto, url_fuente
    )
    VALUES (
        'consulta_vinculante', 'DGT', 'es', 'dgt', 'fiscal', 'V0000-26', '2026-01-15', 'Consulta DGT sobre tipo reducido', 'Documento de referencia relacionado con LIVA 91.', 'https://example.invalid/dgt/V0000-26'
    )
    """,
    # --- Enlace doctrina <-> artículo ---
    """
    INSERT INTO documento_articulo (documento_id, articulo_id, metodo_enlace, confianza_enlace, nota)
    SELECT d.id, a.id, 'manual', 1.00, 'Test fixture'
    FROM documento_interpretativo d
    JOIN articulo a ON a.numero = '91'
    JOIN norma n ON n.id = a.norma_id
    WHERE d.referencia = 'V0000-26' AND n.codigo = 'LIVA'
    """,
    # --- Jurisprudencia de referencia ---
    """
    INSERT INTO documento_interpretativo (
        tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente, ambito, referencia, fecha, titulo, texto, url_fuente
    )
    VALUES (
        'sentencia_ts', 'TS', 'es', 'boe', 'tributario', 'ECLI:ES:TS:2024:2741', '2024-06-15', 'STS 741/2024 - IVA', 'Resumen de jurisprudencia TS sobre IVA.', 'https://example.invalid/ts-2741'
    )
    """,
    """
    INSERT INTO documento_articulo (documento_id, articulo_id, metodo_enlace, confianza_enlace, nota)
    SELECT d.id, a.id, 'manual', 1.00, 'Jurisprudencia fixture'
    FROM documento_interpretativo d
    JOIN articulo a ON a.numero = '91'
    JOIN norma n ON n.id = a.norma_id
    WHERE d.referencia = 'ECLI:ES:TS:2024:2741' AND n.codigo = 'LIVA'
    ON CONFLICT DO NOTHING
    """,
    # --- Doctrina secundaria adicional (CNMV / BdE / AEPD / CENDOJ) ---
    """
    INSERT INTO documento_interpretativo (
        tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente, ambito,
        referencia, fecha, titulo, texto, url_fuente,
        estado_vigencia, numero_circular, fecha_publicacion, referencia_boe
    )
    VALUES (
        'circular', 'CNMV', 'es', 'cnmv', 'mifid_ii',
        'CNMV-Circular-1-2025', '2025-03-01',
        'Circular 1/2025 sobre normas de conducta MiFID II',
        'Texto orientativo CNMV sobre obligaciones de conducta y reporting prudencial.',
        'https://example.invalid/cnmv/circular-1-2025',
        'vigente', '1/2025', '2025-03-05', 'BOE-A-2025-1234'
    )
    """,
    """
    INSERT INTO documento_interpretativo (
        tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente, ambito,
        referencia, fecha, titulo, texto, url_fuente
    )
    VALUES (
        'circular', 'Banco de España', 'es', 'bde', 'supervision_bancaria',
        'BdE-Circular-2-2025', '2025-04-10',
        'Circular BdE 2/2025 sobre solvencia',
        'Texto BdE sobre requerimientos de solvencia y reporting.',
        'https://example.invalid/bde/circular-2-2025'
    )
    """,
    """
    INSERT INTO documento_interpretativo (
        tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente, ambito,
        referencia, fecha, titulo, texto, url_fuente
    )
    VALUES (
        'guia_aepd', 'AEPD', 'es', 'aepd', 'proteccion_datos',
        'AEPD-Guia-Cookies-2025', '2025-02-20',
        'Guia AEPD sobre cookies 2025',
        'Texto AEPD sobre uso de cookies y consentimiento informado.',
        'https://example.invalid/aepd/cookies-2025'
    )
    """,
    """
    INSERT INTO documento_interpretativo (
        tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente, ambito,
        referencia, fecha, titulo, texto, url_fuente
    )
    VALUES (
        'sentencia_ts', 'Tribunal Supremo', 'es', 'cendoj', 'tributario',
        'STS-2847/2025', '2025-05-12',
        'STS 2847/2025 Trib Supremo sobre IVA y restauracion en operaciones intracomunitarias',
        'Resumen jurisprudencia Tribunal Supremo sobre IVA, restauracion, sujeto pasivo y operaciones intracomunitarias.',
        'https://example.invalid/cendoj/sts-2847-2025'
    )
    """,
    """
    INSERT INTO documento_interpretativo (
        tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente, ambito,
        referencia, fecha, titulo, texto, url_fuente
    ) VALUES (
        'sentencia', 'Tribunal Supremo', 'es', 'cendoj', 'jurisprudencia_mercantil_regulatoria',
        'STS-2200/2025', '2025-02-18',
        'STS 2200/2025 sobre comisiones y conflictos de interes',
        'Resumen jurisprudencial sobre comisiones de preferencia e indiferencia bajo MiFID II.',
        'https://example.invalid/cendoj/sts-2200-2025'
    )
    """,
    # --- Modelos AEAT ---
    """
    CREATE TABLE IF NOT EXISTS aeat_modelo (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        nombre TEXT NOT NULL,
        periodo TEXT,
        impuesto TEXT,
        url_info TEXT,
        activo INTEGER NOT NULL DEFAULT 1,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS modelo_articulo (
        modelo_id INTEGER NOT NULL REFERENCES aeat_modelo(id) ON DELETE CASCADE,
        articulo_id INTEGER NOT NULL REFERENCES articulo(id) ON DELETE CASCADE,
        norma TEXT NOT NULL,
        numero TEXT NOT NULL,
        metodo_enlace TEXT NOT NULL,
        confianza_enlace REAL NOT NULL,
        casilla TEXT,
        nota TEXT,
        fuente TEXT NOT NULL,
        url_fuente TEXT,
        PRIMARY KEY (modelo_id, articulo_id),
        UNIQUE(modelo_id, norma, numero)
    )
    """,
    # --- Seed: Modelo 100 linked strongly to LIVA 91 ---
    """
    INSERT INTO aeat_modelo (codigo, nombre, periodo, impuesto, url_info)
    VALUES ('100', 'IRPF Declaración anual', 'anual', 'IRPF', 'https://sede.agenciatributaria.gob.es/modelo-100'),
           ('111', 'Retenciones e ingresos a cuenta sobre rendimientos del trabajo', 'trimestral', 'IRPF', 'https://sede.agenciatributaria.gob.es/modelo-111'),
           ('303', 'IVA Autoliquidación', 'trimestral', 'IVA', 'https://sede.agenciatributaria.gob.es/modelo-303')
    """,
    """
    INSERT INTO modelo_articulo (
        modelo_id, articulo_id, norma, numero, metodo_enlace, confianza_enlace,
        casilla, nota, fuente, url_fuente
    )
    SELECT
        m.id,
        a.id,
        'LIVA',
        '91',
        'manual_official',
        1.0,
        '0002',
        'Rendimientos trabajo',
        'Instrucciones Modelo 100 2025',
        'https://sede.agenciatributaria.gob.es'
    FROM aeat_modelo m, articulo a
    JOIN norma n ON n.id = a.norma_id
    WHERE m.codigo = '100' AND n.codigo = 'LIVA' AND a.numero = '91'
    """,
    # --- Seed: legacy hidden row still present in runtime for modelo 303 ---
    """
    INSERT INTO modelo_articulo (
        modelo_id, articulo_id, norma, numero, metodo_enlace, confianza_enlace,
        casilla, nota, fuente, url_fuente
    )
    SELECT
        m.id,
        a.id,
        'LIVA',
        '91',
        'legacy_numero_only',
        0.0,
        NULL,
        'Legacy enlace heredado por numero',
        'Import legacy modelos seed',
        'https://sede.agenciatributaria.gob.es'
    FROM aeat_modelo m, articulo a
    JOIN norma n ON n.id = a.norma_id
    WHERE m.codigo = '303' AND n.codigo = 'LIVA' AND a.numero = '91'
    """,
    # --- Modelos v2 schema: campañas, casillas, claves, instrucciones, normativa ---
    """
    CREATE TABLE IF NOT EXISTS modelo_campana (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        modelo_id       INTEGER NOT NULL REFERENCES aeat_modelo(id) ON DELETE CASCADE,
        campana         TEXT NOT NULL,
        version_form    TEXT,
        url_instrucciones TEXT,
        url_normativa   TEXT,
        url_formato     TEXT,
        fecha_publicacion_portal TEXT,
        fecha_actualizacion_portal TEXT,
        estado_publicacion TEXT,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        activo          INTEGER NOT NULL DEFAULT 1,
        creado_at       TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(modelo_id, campana)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS modelo_recurso (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        campana_id INTEGER NOT NULL REFERENCES modelo_campana(id) ON DELETE CASCADE,
        tipo_recurso TEXT NOT NULL,
        formato TEXT NOT NULL,
        url_recurso TEXT NOT NULL,
        sha256_contenido TEXT NOT NULL,
        etag TEXT,
        last_modified TEXT,
        content_length INTEGER,
        fecha_publicacion_recurso TEXT,
        metadata TEXT NOT NULL DEFAULT '{}',
        activa INTEGER NOT NULL DEFAULT 1,
        first_seen_at TEXT DEFAULT CURRENT_TIMESTAMP,
        last_seen_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(campana_id, tipo_recurso, sha256_contenido)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS modelo_casilla (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        campana_id      INTEGER NOT NULL REFERENCES modelo_campana(id) ON DELETE CASCADE,
        codigo          TEXT NOT NULL,
        etiqueta        TEXT NOT NULL,
        descripcion     TEXT,
        tipo_casilla    TEXT,
        pagina          INTEGER,
        orden           INTEGER,
        activa          INTEGER NOT NULL DEFAULT 1,
        creado_at       TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(campana_id, codigo)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS modelo_clave (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        campana_id      INTEGER NOT NULL REFERENCES modelo_campana(id) ON DELETE CASCADE,
        codigo          TEXT NOT NULL,
        etiqueta        TEXT NOT NULL,
        descripcion     TEXT,
        tipo_clave      TEXT,
        activa          INTEGER NOT NULL DEFAULT 1,
        creado_at       TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(campana_id, codigo)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS modelo_instruccion (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        campana_id      INTEGER NOT NULL REFERENCES modelo_campana(id) ON DELETE CASCADE,
        seccion         TEXT NOT NULL,
        titulo          TEXT NOT NULL,
        contenido       TEXT NOT NULL,
        orden           INTEGER DEFAULT 0,
        creado_at       TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS modelo_normativa (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        modelo_id       INTEGER NOT NULL REFERENCES aeat_modelo(id) ON DELETE CASCADE,
        boe_id          TEXT,
        titulo          TEXT NOT NULL,
        fecha           TEXT,
        url_boe         TEXT,
        resumen         TEXT,
        creado_at       TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(modelo_id, boe_id)
    )
    """,
    # --- Seed: campaign for model 100 ---
    """
    INSERT INTO modelo_campana (modelo_id, campana, activo, url_instrucciones, estado_publicacion, fecha_publicacion_portal)
    SELECT m.id, '2025', 1, 'https://sede.agenciatributaria.gob.es/modelo-100-instrucciones', 'publicado', '2025-04-01'
    FROM aeat_modelo m WHERE m.codigo = '100'
    """,
    """
    INSERT INTO modelo_campana (modelo_id, campana, activo, url_instrucciones, estado_publicacion, fecha_publicacion_portal)
    SELECT m.id, '2024', 0, 'https://sede.agenciatributaria.gob.es/modelo-100-instrucciones-2024', 'historico', '2024-04-01'
    FROM aeat_modelo m WHERE m.codigo = '100'
    """,
    """
    INSERT INTO modelo_campana (modelo_id, campana, activo, url_instrucciones, estado_publicacion, fecha_publicacion_portal)
    SELECT m.id, '2025', 1, 'https://sede.agenciatributaria.gob.es/modelo-303-instrucciones', 'publicado', '2025-01-15'
    FROM aeat_modelo m WHERE m.codigo = '303'
    """,
    """
    INSERT INTO modelo_campana (modelo_id, campana, activo, url_instrucciones, estado_publicacion, fecha_publicacion_portal)
    SELECT m.id, '2025', 1, 'https://sede.agenciatributaria.gob.es/modelo-111-instrucciones', 'publicado', '2025-01-10'
    FROM aeat_modelo m WHERE m.codigo = '111'
    """,
    # --- Seed: casillas for model 100 campaign ---
    """
    INSERT INTO modelo_casilla (campana_id, codigo, etiqueta, descripcion, tipo_casilla, orden)
    SELECT mc.id, '0002', 'Rendimientos del trabajo', 'Suma de todos los rendimientos del trabajo', 'importe', 1
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '100' AND mc.campana = '2025'
    """,
    # --- Seed: instrucciones for model 100 campaign ---
    """
    INSERT INTO modelo_instruccion (campana_id, seccion, titulo, contenido, orden)
    SELECT mc.id, 'caracteristicas', 'Que es el modelo 100?', 'El modelo 100 es la declaracion anual del IRPF.', 1
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '100' AND mc.campana = '2025'
    """,
    # --- Seed: normativa for model 100 ---
    """
    INSERT INTO modelo_normativa (modelo_id, boe_id, titulo, fecha, url_boe, resumen)
    SELECT m.id, 'BOE-A-2024-26789', 'Orden HAC/1234/2024', '2024-12-20', 'https://www.boe.es/boe/dias/2024/12/20/pdfs/BOE-A-2024-26789.pdf', 'Aprueba el modelo 100'
    FROM aeat_modelo m WHERE m.codigo = '100'
    """,
    """
    INSERT INTO modelo_recurso (campana_id, tipo_recurso, formato, url_recurso, sha256_contenido, fecha_publicacion_recurso, activa, first_seen_at, last_seen_at)
    SELECT mc.id, 'instrucciones', 'pdf', 'https://sede.agenciatributaria.gob.es/modelo-100-instrucciones-2025.pdf', 'hash-modelo100-2025-v1', '2025-04-01', 1, '2025-04-01T00:00:00Z', '2025-04-02T00:00:00Z'
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '100' AND mc.campana = '2025'
    """,
    """
    INSERT INTO modelo_recurso (campana_id, tipo_recurso, formato, url_recurso, sha256_contenido, fecha_publicacion_recurso, activa, first_seen_at, last_seen_at)
    SELECT mc.id, 'instrucciones', 'pdf', 'https://sede.agenciatributaria.gob.es/modelo-100-instrucciones-2024.pdf', 'hash-modelo100-2024-v1', '2024-04-01', 0, '2024-04-01T00:00:00Z', '2024-04-03T00:00:00Z'
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '100' AND mc.campana = '2024'
    """,
    """
    INSERT INTO modelo_recurso (campana_id, tipo_recurso, formato, url_recurso, sha256_contenido, fecha_publicacion_recurso, activa, first_seen_at, last_seen_at)
    SELECT mc.id, 'formulario_pdf', 'pdf', 'https://sede.agenciatributaria.gob.es/modelo-303-formulario-2025.pdf', 'hash-modelo303-2025-v1', '2025-01-15', 1, '2025-01-15T00:00:00Z', '2025-01-16T00:00:00Z'
    FROM modelo_campana mc JOIN aeat_modelo m ON m.id = mc.modelo_id
    WHERE m.codigo = '303' AND mc.campana = '2025'
    """,
    # --- Screening / company links ---
    """
    CREATE TABLE IF NOT EXISTS screening_lists (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT NOT NULL UNIQUE,
        nombre TEXT NOT NULL,
        tipo TEXT NOT NULL,
        organismo TEXT NOT NULL,
        pais TEXT,
        url_fuente TEXT,
        descripcion TEXT,
        actualizada TEXT,
        activo BOOLEAN NOT NULL DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS screening_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        list_id INTEGER NOT NULL REFERENCES screening_lists(id),
        entidad_id TEXT NOT NULL,
        nombre TEXT NOT NULL,
        nombre_normalizado TEXT NOT NULL,
        tipo_entidad TEXT NOT NULL,
        pais TEXT,
        nif TEXT,
        fecha_nacimiento TEXT,
        aliases TEXT,
        categorias TEXT,
        descripcion TEXT,
        fecha_sancion TEXT,
        fecha_alta TEXT,
        fecha_baja TEXT,
        activo BOOLEAN NOT NULL DEFAULT 1,
        metadata_json TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (list_id, entidad_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS screening_matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL REFERENCES empresa(id),
        entry_id INTEGER NOT NULL REFERENCES screening_entries(id),
        list_id INTEGER NOT NULL REFERENCES screening_lists(id),
        confianza REAL NOT NULL,
        motivo TEXT NOT NULL,
        match_campo TEXT NOT NULL,
        match_texto TEXT,
        revisado BOOLEAN NOT NULL DEFAULT 0,
        revisor TEXT,
        revisado_at TEXT,
        notas TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (empresa_id, entry_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS documento_empresa (
        empresa_id INTEGER NOT NULL REFERENCES empresa(id) ON DELETE CASCADE,
        documento_id INTEGER NOT NULL REFERENCES documento_interpretativo(id) ON DELETE CASCADE,
        rol TEXT,
        confianza_extraccion REAL NOT NULL DEFAULT 0,
        PRIMARY KEY (empresa_id, documento_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS obligacion_documento (
        obligacion_id INTEGER NOT NULL REFERENCES obligacion_regulatoria(id) ON DELETE CASCADE,
        documento_id INTEGER NOT NULL REFERENCES documento_interpretativo(id) ON DELETE CASCADE,
        tipo_relacion TEXT,
        PRIMARY KEY (obligacion_id, documento_id)
    )
    """,
    # --- EUR-Lex seed (norma + articulo + version_articulo) ---
    # El worker apps/workers/eurlex.py escribe en estas tablas con tipo_fuente='eurlex'.
    # Usamos un Reglamento UE realista para que filtros q='reglamento',
    # tipo='reglamento' y ambito='mercado_interior' produzcan match.
    """
    INSERT INTO norma (
        codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente,
        tipo_documento, ambito, estado_cobertura, vigente_desde
    )
    VALUES (
        'EUR-Lex-32020R548',
        'Reglamento (UE) 2020/548 sobre disposiciones del mercado interior',
        'EUR-Lex-32020R548',
        'https://eur-lex.europa.eu/eli/reg/2020/548/oj',
        'ue',
        'eurlex',
        'reglamento',
        'mercado_interior',
        'ingestada',
        '2020-04-22'
    )
    """,
    """
    INSERT INTO articulo (norma_id, numero, titulo, tipo)
    SELECT id, '1', 'Objeto y ambito de aplicacion', 'articulo'
    FROM norma WHERE codigo = 'EUR-Lex-32020R548'
    """,
    """
    INSERT INTO version_articulo (articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id)
    SELECT a.id,
           'Articulo 1. Objeto. El presente Reglamento establece las disposiciones aplicables al mercado interior de la Union Europea, garantizando la libre circulacion de bienes, servicios, capitales y personas conforme al Tratado de Funcionamiento de la UE.',
           '2020-04-22', NULL, 'eurlex-32020R548-a1'
    FROM articulo a
    JOIN norma n ON n.id = a.norma_id
    WHERE n.codigo = 'EUR-Lex-32020R548' AND a.numero = '1'
    """,
    """
    CREATE TABLE IF NOT EXISTS xbrl_filing (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_name TEXT NOT NULL,
        source_path TEXT NOT NULL UNIQUE,
        entity_identifier TEXT,
        period_start TEXT,
        period_end TEXT,
        filing_type TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS xbrl_fact (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filing_id INTEGER NOT NULL REFERENCES xbrl_filing(id) ON DELETE CASCADE,
        concept TEXT NOT NULL,
        value_raw TEXT NOT NULL,
        value_numeric REAL,
        unit TEXT,
        context_ref TEXT,
        period_start TEXT,
        period_end TEXT,
        entity_identifier TEXT,
        decimals TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS xbrl_taxonomy (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        concept_qname TEXT NOT NULL,
        namespace TEXT,
        label TEXT NOT NULL,
        label_language TEXT NOT NULL,
        label_role TEXT NOT NULL,
        standard TEXT NOT NULL,
        data_type TEXT,
        period_type TEXT,
        is_monetary BOOLEAN NOT NULL,
        is_negative_allowed BOOLEAN NOT NULL,
        UNIQUE (concept_qname, label_language, label_role)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pgc_marco (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        titulo TEXT NOT NULL,
        tipo TEXT NOT NULL,
        anio INTEGER,
        texto TEXT,
        url_boe TEXT,
        vigente BOOLEAN NOT NULL DEFAULT 1
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pgc_cuenta (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        descripcion TEXT NOT NULL,
        nivel INTEGER NOT NULL,
        padre_codigo TEXT,
        grupo TEXT,
        clase TEXT,
        saldo_normal TEXT,
        tipo_cuenta TEXT,
        vigente BOOLEAN NOT NULL DEFAULT 1,
        nota TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pgc_norma_valoracion (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        marco_id INTEGER REFERENCES pgc_marco(id),
        cuenta_id INTEGER REFERENCES pgc_cuenta(id),
        norma_ref TEXT NOT NULL,
        articulo TEXT,
        descripcion TEXT,
        tipo_operacion TEXT,
        debe_haber TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pgc_estado_financiero (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cuenta_id INTEGER REFERENCES pgc_cuenta(id),
        estado TEXT NOT NULL,
        tipo_presentacion TEXT,
        orden INTEGER NOT NULL,
        periodo TEXT NOT NULL,
        importe_base REAL,
        importe_anterior REAL,
        nota_pieds TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pgc_cuenta_fiscal_ref (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cuenta_id INTEGER REFERENCES pgc_cuenta(id),
        modelo TEXT NOT NULL,
        casilla TEXT,
        ejercicio TEXT,
        nota TEXT,
        UNIQUE (cuenta_id, modelo, casilla, ejercicio)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pgc_cuenta_modelo_aeat_ref (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cuenta_id INTEGER REFERENCES pgc_cuenta(id),
        modelo_id INTEGER NOT NULL,
        campana TEXT,
        nota TEXT,
        UNIQUE (cuenta_id, modelo_id, campana)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pgc_xbrl_mapping (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        xbrl_concept_qname TEXT NOT NULL,
        pgc_account_codigo TEXT NOT NULL,
        confidence TEXT NOT NULL,
        mapping_type TEXT NOT NULL,
        note TEXT NOT NULL,
        is_active BOOLEAN NOT NULL DEFAULT 1,
        UNIQUE (xbrl_concept_qname, pgc_account_codigo)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS workflow_cases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        workflow_id TEXT NOT NULL UNIQUE,
        cambio_codigo TEXT NOT NULL,
        obligacion_codigo TEXT NOT NULL,
        estado TEXT NOT NULL,
        owner_rol TEXT NOT NULL,
        fecha_objetivo TEXT NOT NULL,
        evidencia_requerida TEXT NOT NULL,
        checklist TEXT NOT NULL,
        resultado_revision TEXT,
        notas TEXT,
        accion_recomendada_confirmada TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    INSERT INTO workflow_cases (
        workflow_id, cambio_codigo, obligacion_codigo, estado, owner_rol,
        fecha_objetivo, evidencia_requerida, checklist
    ) VALUES (
        'WF-001',
        'CAMBIO-CNMV-001',
        'CNMV-IR-RESERVADA',
        'pendiente_revision',
        'compliance',
        '2026-05-05',
        '["analisis_impacto", "actualizacion_calendario"]',
        '["validar impacto normativo", "asignar responsable", "confirmar fecha objetivo"]'
    )
    """,
    # --- Note: modelo_campana_activa() is a Postgres function.
    # For SQLite tests, the API code falls back to direct queries when the function
    # is not available. The campaign seeded above has activo=1 so it will be picked
    # by the "ORDER BY campana DESC LIMIT 1" query in the router.
]

with engine.begin() as conn:
    for statement in STATEMENTS:
        conn.execute(text(statement))


def _seed_screening_data() -> None:
    with engine.begin() as conn:
        for list_data in screening_worker.SCREENING_LISTS:
            conn.execute(
                text(
                    """
                    INSERT INTO screening_lists (
                        codigo, nombre, tipo, organismo, pais, url_fuente,
                        descripcion, actualizada, activo
                    ) VALUES (
                        :codigo, :nombre, :tipo, :organismo, :pais, :url_fuente,
                        :descripcion, :actualizada, :activo
                    )
                    """
                ),
                list_data,
            )

        for entry_data in screening_worker.SCREENING_ENTRIES:
            list_id = conn.execute(
                text("SELECT id FROM screening_lists WHERE codigo = :codigo"),
                {"codigo": entry_data["list_id"]},
            ).scalar_one()
            conn.execute(
                text(
                    """
                    INSERT INTO screening_entries (
                        list_id, entidad_id, nombre, nombre_normalizado, tipo_entidad, pais,
                        nif, fecha_nacimiento, aliases, categorias, descripcion,
                        fecha_sancion, fecha_alta, fecha_baja, activo, metadata_json
                    ) VALUES (
                        :list_id, :entidad_id, :nombre, :nombre_normalizado, :tipo_entidad, :pais,
                        :nif, :fecha_nacimiento, :aliases, :categorias, :descripcion,
                        :fecha_sancion, :fecha_alta, :fecha_baja, :activo, :metadata_json
                    )
                    """
                ),
                {
                    "list_id": list_id,
                    "entidad_id": entry_data["entidad_id"],
                    "nombre": entry_data["nombre"],
                    "nombre_normalizado": screening_worker._normalize_name(entry_data["nombre"]),
                    "tipo_entidad": entry_data["tipo_entidad"],
                    "pais": entry_data.get("pais"),
                    "nif": entry_data.get("nif"),
                    "fecha_nacimiento": entry_data.get("fecha_nacimiento"),
                    "aliases": __import__("json").dumps(entry_data.get("aliases", [])),
                    "categorias": __import__("json").dumps(entry_data.get("categorias", [])),
                    "descripcion": entry_data.get("descripcion"),
                    "fecha_sancion": entry_data.get("fecha_sancion"),
                    "fecha_alta": entry_data.get("fecha_alta"),
                    "fecha_baja": entry_data.get("fecha_baja"),
                    "activo": entry_data.get("activo", True),
                    "metadata_json": __import__("json").dumps(entry_data.get("metadata_json", {})),
                },
            )


_seed_screening_data()


def _reset_xbrl_tables() -> None:
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM xbrl_fact"))
        conn.execute(text("DELETE FROM xbrl_filing"))


def _seed_xbrl_fixture() -> None:
    _reset_xbrl_tables()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO xbrl_filing (source_name, source_path, entity_identifier, period_start, period_end, filing_type)
                VALUES (:source_name, :source_path, :entity_identifier, :period_start, :period_end, :filing_type)
                """
            ),
            XBRL_FIXTURE_CATALOG["filing"],
        )
        filing_id = conn.execute(
            text("SELECT id FROM xbrl_filing WHERE source_path = :source_path"),
            {"source_path": XBRL_FIXTURE_CATALOG["filing"]["source_path"]},
        ).scalar_one()
        for fact in XBRL_FIXTURE_CATALOG["facts"]:
            conn.execute(
                text(
                    """
                    INSERT INTO xbrl_fact (
                        filing_id, concept, value_raw, value_numeric, unit, context_ref,
                        period_start, period_end, entity_identifier, decimals
                    ) VALUES (
                        :filing_id, :concept, :value_raw, :value_numeric, :unit, :context_ref,
                        :period_start, :period_end, :entity_identifier, :decimals
                    )
                    """
                ),
                {
                    "filing_id": filing_id,
                    **fact,
                    "value_numeric": float(fact["value_numeric"]) if fact["value_numeric"] is not None else None,
                },
            )


def _reset_pgc_tables() -> None:
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM pgc_xbrl_mapping"))
        conn.execute(text("DELETE FROM pgc_cuenta_modelo_aeat_ref"))
        conn.execute(text("DELETE FROM pgc_cuenta_fiscal_ref"))
        conn.execute(text("DELETE FROM pgc_estado_financiero"))
        conn.execute(text("DELETE FROM pgc_norma_valoracion"))
        conn.execute(text("DELETE FROM pgc_cuenta"))
        conn.execute(text("DELETE FROM pgc_marco"))


def _seed_pgc_catalog() -> None:
    _reset_pgc_tables()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO pgc_marco (codigo, titulo, tipo, anio, texto, url_boe, vigente)
                VALUES (:codigo, :titulo, :tipo, :anio, :texto, :url_boe, 1)
                """
            ),
            PGC_CATALOG["marco"],
        )
        marco_id = conn.execute(
            text("SELECT id FROM pgc_marco WHERE codigo = :codigo"),
            {"codigo": PGC_CATALOG["marco"]["codigo"]},
        ).scalar_one()

        for account in PGC_CATALOG["accounts"]:
            conn.execute(
                text(
                    """
                    INSERT INTO pgc_cuenta (
                        codigo, descripcion, nivel, padre_codigo, grupo, clase,
                        saldo_normal, tipo_cuenta, vigente, nota
                    ) VALUES (
                        :codigo, :descripcion, :nivel, :padre_codigo, :grupo, :clase,
                        :saldo_normal, :tipo_cuenta, 1, :nota
                    )
                    """
                ),
                account,
            )

        for norma in PGC_CATALOG["normas"]:
            cuenta_id = conn.execute(
                text("SELECT id FROM pgc_cuenta WHERE codigo = :codigo"),
                {"codigo": norma["cuenta_codigo"]},
            ).scalar_one_or_none()
            conn.execute(
                text(
                    """
                    INSERT INTO pgc_norma_valoracion (marco_id, cuenta_id, norma_ref, articulo, descripcion)
                    VALUES (:marco_id, :cuenta_id, :norma_ref, :articulo, :descripcion)
                    """
                ),
                {
                    "marco_id": marco_id,
                    "cuenta_id": cuenta_id,
                    "norma_ref": norma["norma_ref"],
                    "articulo": norma["articulo"],
                    "descripcion": norma["descripcion"],
                },
            )

        for estado in PGC_CATALOG["estados_financieros"]:
            cuenta_id = conn.execute(
                text("SELECT id FROM pgc_cuenta WHERE codigo = :codigo"),
                {"codigo": estado["cuenta_codigo"]},
            ).scalar_one_or_none()
            conn.execute(
                text(
                    """
                    INSERT INTO pgc_estado_financiero (
                        cuenta_id, estado, tipo_presentacion, orden, periodo,
                        importe_base, importe_anterior, nota_pieds
                    ) VALUES (
                        :cuenta_id, :estado, :tipo_presentacion, :orden, :periodo,
                        :importe_base, :importe_anterior, :nota_pieds
                    )
                    """
                ),
                {
                    "cuenta_id": cuenta_id,
                    "estado": estado["estado"],
                    "tipo_presentacion": estado["tipo_presentacion"],
                    "orden": estado["orden"],
                    "periodo": estado["periodo"],
                    "importe_base": estado.get("importe_base"),
                    "importe_anterior": estado.get("importe_anterior"),
                    "nota_pieds": estado.get("nota_pieds"),
                },
            )

        for ref in PGC_CATALOG["referencias_fiscales"]:
            cuenta_id = conn.execute(
                text("SELECT id FROM pgc_cuenta WHERE codigo = :codigo"),
                {"codigo": ref["cuenta_codigo"]},
            ).scalar_one_or_none()
            conn.execute(
                text(
                    """
                    INSERT INTO pgc_cuenta_fiscal_ref (cuenta_id, modelo, casilla, ejercicio, nota)
                    VALUES (:cuenta_id, :modelo, :casilla, :ejercicio, :nota)
                    """
                ),
                {
                    "cuenta_id": cuenta_id,
                    "modelo": ref["modelo"],
                    "casilla": ref["casilla"],
                    "ejercicio": ref["ejercicio"],
                    "nota": ref["nota"],
                },
            )

        for ref in PGC_CATALOG["referencias_aeat"]:
            cuenta_id = conn.execute(
                text("SELECT id FROM pgc_cuenta WHERE codigo = :codigo"),
                {"codigo": ref["cuenta_codigo"]},
            ).scalar_one_or_none()
            conn.execute(
                text(
                    """
                    INSERT INTO pgc_cuenta_modelo_aeat_ref (cuenta_id, modelo_id, campana, nota)
                    VALUES (:cuenta_id, :modelo_id, :campana, :nota)
                    """
                ),
                {
                    "cuenta_id": cuenta_id,
                    "modelo_id": ref["modelo_id"],
                    "campana": ref.get("campana"),
                    "nota": ref.get("nota"),
                },
            )


def _reset_xbrl_taxonomy() -> None:
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM xbrl_taxonomy"))


@pytest.fixture
def xbrl_fixture_catalog():
    return XBRL_FIXTURE_CATALOG


@pytest.fixture
def xbrl_test_db(xbrl_fixture_catalog):
    del xbrl_fixture_catalog
    _reset_xbrl_taxonomy()
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM pgc_xbrl_mapping"))
    _seed_xbrl_fixture()
    yield


@pytest.fixture
def xbrl_taxonomy_seed():
    from apps.workers import xbrl_taxonomy as xbrl_tax

    _reset_xbrl_taxonomy()
    xbrl_tax.seed_taxonomy(engine=engine)
    yield


@pytest.fixture
def pgc_catalog():
    return PGC_CATALOG


@pytest.fixture
def pgc_test_db(pgc_catalog):
    del pgc_catalog
    _seed_pgc_catalog()
    yield


@pytest.fixture
def pgc_xbrl_mapping_seed(pgc_test_db):
    del pgc_test_db
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM pgc_xbrl_mapping"))

    from apps.workers import pgc_xbrl_mapping as mapper

    mapper.run_sync(engine=engine)
    yield


@pytest.fixture
def pgc_xbrl_enriched_db(pgc_test_db, pgc_xbrl_mapping_seed):
    del pgc_test_db
    del pgc_xbrl_mapping_seed
    yield


# ── MCP test fixtures ────────────────────────────────────────────────────────

import sys as _sys
from pathlib import Path as _Path

_api_dir = _Path(__file__).resolve().parents[1]
if str(_api_dir) not in _sys.path:
    _sys.path.insert(0, str(_api_dir))


@pytest.fixture
def mcp_headers():
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-API-Key": "test-mcp-key",
    }
