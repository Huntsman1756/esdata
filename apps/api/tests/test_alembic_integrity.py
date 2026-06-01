from __future__ import annotations

import importlib.util
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ALEMBIC_VERSIONS = REPO_ROOT / "alembic" / "versions"
ALEMBIC_ENV = REPO_ROOT / "alembic" / "env.py"


def _load_revision_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_alembic_versions_define_revision_metadata_and_import_cleanly():
    revision_files = sorted(ALEMBIC_VERSIONS.glob("*.py"))
    assert revision_files, "expected Alembic revision files"

    missing_metadata: list[str] = []

    for path in revision_files:
        module = _load_revision_module(path)
        if not hasattr(module, "revision") or not hasattr(module, "down_revision"):
            missing_metadata.append(path.name)

    assert not missing_metadata, (
        "Alembic revisions must import cleanly and define revision/down_revision: "
        + ", ".join(missing_metadata)
    )


def test_criterio_relacion_runtime_api_rls_is_migrated_in_revision_0084():
    revision_path = (
        ALEMBIC_VERSIONS / "20260521_0084_criterio_relacion_api_rls.py"
    )
    contents = revision_path.read_text(encoding="utf-8")

    for fragment in (
        "GRANT SELECT ON criterio_relacion TO esdata_api",
        "CREATE POLICY esdata_api_select ON criterio_relacion",
        "FOR SELECT TO esdata_api",
    ):
        assert fragment in contents


def test_doctrina_partial_pilot_relations_are_seeded_in_revision_0085():
    revision_path = (
        ALEMBIC_VERSIONS / "20260522_0085_doctrina_partial_pilot_relations.py"
    )
    contents = revision_path.read_text(encoding="utf-8")

    for fragment in (
        "D-03",
        "V0144-26",
        "LIS",
        "18",
        "articulo_supuesto",
        "D-04",
        "V0138-24",
        "289",
        "modelo_supuesto",
        "'partial'",
    ):
        assert fragment in contents


def test_doctrina_d02_intracomunitaria_is_seeded_in_revision_0086():
    revision_path = (
        ALEMBIC_VERSIONS / "20260523_0086_doctrina_d02_intracomunitaria.py"
    )
    contents = revision_path.read_text(encoding="utf-8")

    for fragment in (
        "V0963-25",
        "D-02",
        "LIVA",
        "13",
        "349",
        "adquisicion_intracomunitaria_bienes",
        "'complete'",
        "documento_articulo",
        "manual_official",
    ):
        assert fragment in contents


def test_doctrina_d04_crs_fatca_is_seeded_in_revision_0087():
    revision_path = ALEMBIC_VERSIONS / "20260523_0087_doctrina_d04_crs_fatca.py"
    contents = revision_path.read_text(encoding="utf-8")

    for fragment in (
        "V0138-24",
        "D-04",
        "LGT",
        "vigésimo segunda",
        "289",
        "crs_fatca",
        "'complete'",
        "documento_articulo",
        "manual_official",
        "Real Decreto 1021/2015",
    ):
        assert fragment in contents


def test_aeat_irnr_income_type_rules_are_seeded_in_revision_0089():
    revision_path = ALEMBIC_VERSIONS / "20260524_0089_aeat_irnr_income_type_rules.py"
    contents = revision_path.read_text(encoding="utf-8")

    for fragment in (
        "tipo_renta_dividendos_irnr_296",
        "tipo_renta_intereses_irnr_296",
        "Modelo 296, clave de renta 1",
        "Modelo 296, clave de renta 2",
        "source_hash IS NOT NULL",
        "capture_date IS NOT NULL",
        "CONDICIONAL",
    ):
        assert fragment in contents


def test_aeat_193_income_type_rules_are_seeded_in_revision_0090():
    revision_path = ALEMBIC_VERSIONS / "20260524_0090_aeat_193_income_type_rules.py"
    contents = revision_path.read_text(encoding="utf-8")

    for fragment in (
        "tipo_renta_dividendos_residentes_193",
        "tipo_renta_intereses_residentes_193",
        "PERCEPCION_A",
        "NAT_A_02",
        "PERCEPCION_B",
        "NAT_BD_01",
        "source_hash IS NOT NULL",
        "capture_date IS NOT NULL",
        "CONDICIONAL",
    ):
        assert fragment in contents


def test_aeat_193_domestic_applicability_fails_closed_in_revision_0091():
    revision_path = (
        ALEMBIC_VERSIONS
        / "20260524_0091_aeat_193_domestic_applicability_fail_closed.py"
    )
    contents = revision_path.read_text(encoding="utf-8")

    for fragment in (
        "codigo = '193'",
        "periodo = 'anual'",
        "modelo_aeat = '193'",
        "verified = false",
        "safe_to_answer = false",
        "completeness = 'parcial'",
        "source_hash IS NULL",
        "capture_date IS NULL",
        "hash/captura normalizada",
    ):
        assert fragment in contents


def test_aeat_123_124_capital_mobiliario_rules_are_seeded_in_revision_0092():
    revision_path = (
        ALEMBIC_VERSIONS
        / "20260524_0092_aeat_capital_mobiliario_123_124_rules.py"
    )
    contents = revision_path.read_text(encoding="utf-8")

    for fragment in (
        "codigo = '124'",
        "IRPF/IS/IRNR",
        "capital_mobiliario_general_123",
        "activos_financieros_124",
        "activos_financieros_no_generico_124",
        "GH04.shtml",
        "GH05.shtml",
        "sha256_contenido IS NOT NULL",
        "last_seen_at IS NOT NULL",
        "CONDICIONAL",
        "EXCLUIR",
    ):
        assert fragment in contents


def test_aeat_187_198_valores_contract_is_seeded_in_revision_0093():
    revision_path = (
        ALEMBIC_VERSIONS
        / "20260524_0093_aeat_valores_187_198_contract.py"
    )
    contents = revision_path.read_text(encoding="utf-8")

    for fragment in (
        "codigo IN ('187', '198')",
        "modelo_aeat IN ('187', '198')",
        "safe_to_answer = false",
        "verified = false",
        "completeness = 'parcial'",
        "source_hash IS NULL",
        "capture_date IS NULL",
        "iic_transmisiones_reembolsos_187",
        "activos_financieros_valores_mobiliarios_198",
        "sha256_contenido IS NOT NULL",
        "last_seen_at IS NOT NULL",
        "CONDICIONAL",
        "EVIDENCE_LIMITED",
    ):
        assert fragment in contents


def test_aeat_200_202_303_legacy_obligations_fail_closed_in_revision_0094():
    revision_path = (
        ALEMBIC_VERSIONS
        / "20260524_0094_aeat_fail_close_200_202_303_obligations.py"
    )
    contents = revision_path.read_text(encoding="utf-8")

    for fragment in (
        "modelo_aeat IN ('200', '202', '303')",
        "safe_to_answer = false",
        "verified = false",
        "completeness = 'parcial'",
        "source_hash IS NULL",
        "capture_date IS NULL",
        "200/202/303 legacy profile obligation without normalized evidence",
    ):
        assert fragment in contents


def test_obligacion_perfil_global_fail_closed_in_revision_0095():
    revision_path = (
        ALEMBIC_VERSIONS
        / "20260524_0095_obligacion_perfil_global_fail_closed.py"
    )
    contents = revision_path.read_text(encoding="utf-8")

    for fragment in (
        "UPDATE obligacion_perfil",
        "safe_to_answer = false",
        "verified = false",
        "completeness = 'parcial'",
        "source_hash IS NULL",
        "capture_date IS NULL",
        "global profile obligation without normalized evidence",
    ):
        assert fragment in contents


def test_obligacion_perfil_111_115_recovery_uses_unique_source_revision_in_0096():
    revision_path = (
        ALEMBIC_VERSIONS
        / "20260524_0096_obligacion_perfil_recover_111_115.py"
    )
    contents = revision_path.read_text(encoding="utf-8")

    for fragment in (
        "source_entity_id IN ('AEAT-MODELO-111', 'AEAT-MODELO-115')",
        "COUNT(DISTINCT content_hash_sha256) = 1",
        "modelo_aeat IN ('111', '115')",
        "source_hash = ur.source_hash",
        "capture_date = COALESCE(op.capture_date, ur.capture_date)",
        "verified = true",
        "completeness = 'completa'",
        "safe_to_answer = true",
        "111/115 profile obligation recovered from unique source_revision evidence",
    ):
        assert fragment in contents

    for forbidden in (
        "modelo_aeat IN ('196', '290')",
        "AEAT-MODELO-196",
        "FATCA",
    ):
        assert forbidden not in contents


def test_aeat_289_auxiliary_metadata_evidence_is_normalized_in_0097():
    revision_path = (
        ALEMBIC_VERSIONS / "20260524_0097_aeat_289_metadata_evidence.py"
    )
    contents = revision_path.read_text(encoding="utf-8")

    for fragment in (
        "codigo = '289'",
        "modelo_regla_inclusion",
        "modelo_instruccion",
        "https://www.boe.es/buscar/doc.php?id=BOE-A-2015-12399",
        "423708790f64e673977e020d223ee8af89e99bea7970d793c998264e0fbc7b75",
        "https://sede.agenciatributaria.gob.es/Sede/procedimientoini/GI42.shtml",
        "c73351f50935086f4fbeda39d5123563587a6964e2aaa8d254a4ba7b38b4b9a1",
        "https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimiento_ayuda/GI42/Ayuda/CRS_Presentac_289_SWeb_2.6.pdf",
        "ce76a21a629125961efe6a1ed9800262f4d253ab55c72a7f04e358936a448be3",
        "2026-05-24",
        "source_hash IS NULL",
        "capture_date IS NULL",
    ):
        assert fragment in contents

    for forbidden in (
        "UPDATE obligacion_perfil",
        "safe_to_answer = true",
        "verified = true",
        "completeness = 'completa'",
        "INSERT INTO modelo_clave",
    ):
        assert forbidden not in contents


def test_aeat_289_documental_source_refresh_is_scoped_in_0098():
    revision_path = (
        ALEMBIC_VERSIONS
        / "20260524_0098_aeat_289_documental_source_refresh.py"
    )
    contents = revision_path.read_text(encoding="utf-8")

    for fragment in (
        "codigo = '289'",
        "BOE-A-2016-9834",
        "502a67740152eb23bdf66a59c1a2a69d0a34d8e4054b26191bb7dcfef7d05794",
        "https://sede.agenciatributaria.gob.es/Sede/procedimientoini/GI42.shtml",
        "1c00efed01d8d917591907c134abdc8dde84d87e51a6b69ca5a6acf830a26e1c",
        "https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimiento_ayuda/GI42/Ayuda/XSD_WSDL/289_XSD_2.0_WSDL_2.0.1.zip",
        "6948eec877d04ca637b099f59fa944996aa878c8d68181dfffde87fd056a048d",
        "normativa_hap_1695",
        "procedimiento_gi42",
        "xsd_wsdl",
        "XSD:MessageSpec/SendingCompanyIN",
        "XSD:AccountReport/Payment/PaymentAmnt",
    ):
        assert fragment in contents

    for forbidden in (
        "UPDATE obligacion_perfil",
        "safe_to_answer = true",
        "verified = true",
        "completeness = 'completa'",
        "completeness_estado = 'completa'",
        "INSERT INTO modelo_clave",
    ):
        assert forbidden not in contents


def test_aeat_289_campaign_duality_revision_is_scoped_in_0106():
    revision_path = (
        ALEMBIC_VERSIONS
        / "20260601_0106_aeat_289_campaign_duality.py"
    )
    contents = revision_path.read_text(encoding="utf-8")

    for fragment in (
        "ejercicio_declarado",
        "anio_presentacion",
        "campana-declaraciones-informativas-2025/normativa/modelo-289.html",
        "codigo = '289'",
        "campana = '2025'",
        "url_instrucciones",
    ):
        assert fragment in contents

    for forbidden in (
        "UPDATE obligacion_perfil",
        "safe_to_answer = true",
        "verified = true",
        "completeness = 'completa'",
        "completeness_estado = 'completa'",
    ):
        assert forbidden not in contents


def test_aeat_190_campaign_evidence_revision_is_scoped_in_0108():
    revision_path = (
        ALEMBIC_VERSIONS
        / "20260601_0108_aeat_190_campaign_evidence.py"
    )
    contents = revision_path.read_text(encoding="utf-8")

    for fragment in (
        "codigo = '190'",
        "campana = '2025'",
        "tipo_recurso = 'instrucciones'",
        "modelo-190.html",
        "Modelo 190. Ejercicio 2025. Gestiones activas en AEAT Sede.",
        "b154ea65d4a7679774842767de2e643f76c194e037237052647f43962073f205",
        "capture_date",
        "aeat_campaign_operational_evidence",
        "SET activa = false",
        "mr.url_recurso <> :url_instrucciones",
        "row_completeness = 'complete'",
        "row_provenance = 'official_exact'",
    ):
        assert fragment in contents

    for forbidden in (
        "CAMPAIGN_BEARING_RESOURCE_TYPES",
        "UPDATE obligacion_perfil",
        "INSERT INTO modelo_clave",
        "INSERT INTO modelo_instruccion",
        "safe_to_answer = true",
        "verified = true",
        "completeness = 'completa'",
        "completeness_estado = 'completa'",
    ):
        assert forbidden not in contents


def test_obligacion_perfil_200_recovery_uses_unique_source_revision_in_0099():
    revision_path = (
        ALEMBIC_VERSIONS
        / "20260525_0099_obligacion_perfil_recover_200.py"
    )
    contents = revision_path.read_text(encoding="utf-8")

    for fragment in (
        "source_entity_id = 'AEAT-MODELO-200'",
        "COUNT(DISTINCT content_hash_sha256) = 1",
        "op.modelo_aeat = '200'",
        "source_hash = ur.source_hash",
        "capture_date = COALESCE(op.capture_date, ur.capture_date)",
        "verified = true",
        "completeness = 'completa'",
        "safe_to_answer = true",
        "200 profile obligation recovered from unique source_revision evidence",
    ):
        assert fragment in contents

    for forbidden in (
        "AEAT-MODELO-202",
        "AEAT-MODELO-303",
        "source_entity_id = 'FATCA'",
        "source_entity_id = 'FATCA_IGA_ES'",
        "op.modelo_aeat = '303'",
        "op.modelo_aeat IN ('200', '303')",
    ):
        assert forbidden not in contents


def test_aeat_290_current_docs_migration_is_scoped_in_0100():
    revision_path = (
        ALEMBIC_VERSIONS
        / "20260525_0100_aeat_290_current_docs_2025.py"
    )
    contents = revision_path.read_text(encoding="utf-8")

    for fragment in (
        "mc.campana = :campaign",
        "reported_financial_year",
        "2026-01-01/2026-06-01",
        "290_XSD_2.0_WSDL_2.1.1.zip",
        "b816f86d4778b858b87ac63a6926297b9170d91473af3285d513b8389bf20a59",
        "FATCA-Presentac_290_SWeb_2.16.pdf",
        "91033373633a7e6e3e9aa65e6081fe8cd53abdfb0d2b95303a8a27e57d049431",
        "WS_consulta_errores_290.zip",
        "completeness_estado",
        "aeat_gi38_current_docs",
        "UPDATE modelo_campana mc",
    ):
        assert fragment in contents

    for forbidden in (
        "UPDATE obligacion_perfil",
        "safe_to_answer = true",
        "op.modelo_aeat",
    ):
        assert forbidden not in contents


def test_aeat_290_legacy_field_cleanup_in_0101():
    revision_path = (
        ALEMBIC_VERSIONS
        / "20260525_0101_aeat_290_remove_legacy_fields.py"
    )
    contents = revision_path.read_text(encoding="utf-8")

    for fragment in (
        "am.codigo = '290'",
        "mc.campana = '2025'",
        "cs.activa = true",
        "cs.tipo_casilla <> 'diseno_registro_xsd_campo'",
        "SET activa = false",
    ):
        assert fragment in contents

    for forbidden in (
        "UPDATE obligacion_perfil",
        "DELETE FROM modelo_casilla",
        "safe_to_answer = true",
    ):
        assert forbidden not in contents


def test_aeat_290_reference_sources_migration_is_scoped_in_0102():
    revision_path = (
        ALEMBIC_VERSIONS
        / "20260525_0102_aeat_290_fatca_reference_sources.py"
    )
    contents = revision_path.read_text(encoding="utf-8")

    for fragment in (
        "modelo_290_fatca_reference_sources",
        "validaciones_tin_eeuu",
        "acuerdo_autoridades_competentes_fatca",
        "ficha_procedimiento_gi38",
        "normativa_acuerdo_espana_eeuu_fatca",
        "normativa_orden_hap_1136_2014",
        "normativa_orden_hap_1695_2016",
        "BOE-A-2014-6854",
        "BOE-A-2014-6922",
        "row_provenance = 'official_exact'",
        "mc.campana = :campaign",
    ):
        assert fragment in contents

    for forbidden in (
        "UPDATE obligacion_perfil",
        "safe_to_answer = true",
        "verified = true",
    ):
        assert forbidden not in contents


def test_aeat_172_173_current_docs_migration_is_scoped_in_0103():
    revision_path = (
        ALEMBIC_VERSIONS
        / "20260525_0103_aeat_172_173_current_docs_2025.py"
    )
    contents = revision_path.read_text(encoding="utf-8")

    for fragment in (
        "GI53.shtml",
        "GI54.shtml",
        "Esquemas_WSDL_servicios_web.zip",
        "Esquemas172.zip",
        "Esquemas173.zip",
        "2026-01-01/2026-02-02",
        "modelo_172_173_current_docs",
        "xsd_fields_verified",
        "reported_financial_year",
        "mc.campana = :campaign",
        "mc.campana <> :campaign",
    ):
        assert fragment in contents

    for forbidden in (
        "UPDATE obligacion_perfil",
        "safe_to_answer = true",
        "DELETE FROM modelo_casilla",
    ):
        assert forbidden not in contents


def test_alembic_versions_do_not_use_exec_driver_sql():
    revision_files = sorted(ALEMBIC_VERSIONS.glob("*.py"))
    assert revision_files, "expected Alembic revision files"

    offenders = []
    for path in revision_files:
        contents = path.read_text(encoding="utf-8")
        if "op.exec_driver_sql(" in contents:
            offenders.append(path.name)

    assert not offenders, (
        "Alembic revisions must use op.execute(sa.text(...)) instead of op.exec_driver_sql(...): "
        + ", ".join(offenders)
    )


def test_alembic_env_version_table_width_covers_revision_ids():
    revision_files = sorted(ALEMBIC_VERSIONS.glob("*.py"))
    assert revision_files, "expected Alembic revision files"

    max_revision_len = 0
    for path in revision_files:
        module = _load_revision_module(path)
        if hasattr(module, "revision"):
            max_revision_len = max(max_revision_len, len(module.revision))

    env_text = ALEMBIC_ENV.read_text(encoding="utf-8")
    match = re.search(r"ALEMBIC_VERSION_NUM_LENGTH\s*=\s*(\d+)", env_text)
    assert match, "alembic/env.py must declare ALEMBIC_VERSION_NUM_LENGTH"

    assert int(match.group(1)) >= max_revision_len, (
        "alembic/env.py version table width must cover the longest revision id"
    )


def test_alembic_env_widens_existing_version_table_before_migration():
    env_text = ALEMBIC_ENV.read_text(encoding="utf-8")

    assert "ALTER TABLE IF EXISTS alembic_version" in env_text
    assert "ALTER COLUMN version_num TYPE VARCHAR" in env_text


def test_query_audit_contract_columns_are_migrated_in_revision_0055():
    revision_path = (
        ALEMBIC_VERSIONS / "20260503_0055_query_audit_response_payload.py"
    )
    contents = revision_path.read_text(encoding="utf-8")

    for fragment in (
        "ADD COLUMN IF NOT EXISTS tool_name",
        "ADD COLUMN IF NOT EXISTS sources",
        "ADD COLUMN IF NOT EXISTS confidence",
        "ADD COLUMN IF NOT EXISTS completeness",
        "ADD COLUMN IF NOT EXISTS verified",
        "ADD COLUMN IF NOT EXISTS response_payload",
    ):
        assert fragment in contents


def test_modelo_articulo_provenance_columns_are_migrated_in_revision_0056():
    revision_path = (
        ALEMBIC_VERSIONS / "20260504_0056_modelo_articulo_provenance.py"
    )
    contents = revision_path.read_text(encoding="utf-8")

    for fragment in (
        "ADD COLUMN IF NOT EXISTS norma TEXT",
        "ADD COLUMN IF NOT EXISTS numero TEXT",
        "ADD COLUMN IF NOT EXISTS metodo_enlace TEXT",
        "ADD COLUMN IF NOT EXISTS confianza_enlace NUMERIC(3,2)",
        "UPDATE modelo_articulo ma",
        "legacy_numero_only",
        "ALTER TABLE modelo_articulo ALTER COLUMN norma SET NOT NULL",
        "ALTER TABLE modelo_articulo ALTER COLUMN numero SET NOT NULL",
        "ALTER TABLE modelo_articulo ALTER COLUMN metodo_enlace SET NOT NULL",
        "ALTER TABLE modelo_articulo ALTER COLUMN confianza_enlace SET NOT NULL",
        "ck_modelo_articulo_confianza_enlace_range",
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_modelo_articulo_modelo_norma_numero",
    ):
        assert fragment in contents


def test_dgt_queue_split_is_migrated_in_revision_0057():
    revision_path = ALEMBIC_VERSIONS / "20260504_0057_dgt_queue_split.py"
    contents = revision_path.read_text(encoding="utf-8")

    for fragment in (
        "CREATE TABLE IF NOT EXISTS dgt_queue",
        "ADD CONSTRAINT ck_dgt_queue_status",
        "CREATE INDEX IF NOT EXISTS idx_dgt_queue_pending",
        "INSERT INTO dgt_queue",
        "FROM source_revision",
        "DELETE FROM source_revision",
        "content_hash_sha256 !~ '^[0-9a-f]{64}$'",
    ):
        assert fragment in contents


def test_row_quality_columns_are_migrated_in_revision_0058():
    revision_path = (
        ALEMBIC_VERSIONS / "20260504_0058_row_completeness_provenance.py"
    )
    contents = revision_path.read_text(encoding="utf-8")

    for fragment in (
        "ADD COLUMN IF NOT EXISTS row_completeness TEXT DEFAULT 'complete'",
        "ADD COLUMN IF NOT EXISTS row_provenance TEXT DEFAULT 'official_exact'",
        "ADD COLUMN IF NOT EXISTS row_completeness TEXT DEFAULT 'partial'",
        "ADD COLUMN IF NOT EXISTS row_provenance TEXT DEFAULT 'official_best_effort'",
        "UPDATE modelo_recurso",
        "official_exact",
        "WHERE row_completeness IS NULL OR row_provenance IS NULL",
        "UPDATE documento_interpretativo",
        "official_best_effort",
        "WHERE row_completeness IS NULL OR row_provenance IS NULL",
        "ALTER TABLE modelo_recurso ALTER COLUMN row_completeness SET DEFAULT 'complete'",
        "ALTER TABLE modelo_recurso ALTER COLUMN row_provenance SET DEFAULT 'official_exact'",
        "ALTER TABLE documento_interpretativo ALTER COLUMN row_completeness SET DEFAULT 'partial'",
        "ALTER TABLE documento_interpretativo ALTER COLUMN row_provenance SET DEFAULT 'official_best_effort'",
        "ALTER TABLE modelo_recurso ALTER COLUMN row_completeness SET NOT NULL",
        "ALTER TABLE modelo_recurso ALTER COLUMN row_provenance SET NOT NULL",
        "ALTER TABLE documento_interpretativo ALTER COLUMN row_completeness SET NOT NULL",
        "ALTER TABLE documento_interpretativo ALTER COLUMN row_provenance SET NOT NULL",
        "ck_modelo_recurso_row_completeness",
        "ck_modelo_recurso_row_provenance",
        "ck_documento_interpretativo_row_completeness",
        "ck_documento_interpretativo_row_provenance",
        "DROP CONSTRAINT IF EXISTS ck_documento_interpretativo_row_provenance",
        "DROP CONSTRAINT IF EXISTS ck_documento_interpretativo_row_completeness",
        "DROP CONSTRAINT IF EXISTS ck_modelo_recurso_row_provenance",
        "DROP CONSTRAINT IF EXISTS ck_modelo_recurso_row_completeness",
        "DROP COLUMN IF EXISTS row_provenance",
        "DROP COLUMN IF EXISTS row_completeness",
    ):
        assert fragment in contents


def test_security_closure_is_migrated_in_revision_0064():
    revision_path = ALEMBIC_VERSIONS / "20260510_0064_security_closure.py"
    contents = revision_path.read_text(encoding="utf-8")

    for table_name in (
        "data_freshness_alerts",
        "dgt_queue",
        "source_freshness_snapshot",
    ):
        assert table_name in contents

    for fragment in (
        "ALTER TABLE IF EXISTS {table_name} ENABLE ROW LEVEL SECURITY",
        "CREATE POLICY esdata_all ON {table_name}",
        "CREATE POLICY service_role_all ON {table_name}",
    ):
        assert fragment in contents

    for function_name in (
        "query_audit_log_append_only",
        "set_updated_at",
    ):
        assert function_name in contents

    for fragment in (
        "REVOKE ALL ON FUNCTION {function_name}() FROM PUBLIC",
        "GRANT EXECUTE ON FUNCTION {function_name}() TO esdata",
        "GRANT EXECUTE ON FUNCTION {function_name}() TO service_role",
    ):
        assert fragment in contents


def test_monitoring_rls_closure_is_migrated_in_revision_0067():
    revision_path = ALEMBIC_VERSIONS / "20260510_0067_monitoring_rls_closure.py"
    contents = revision_path.read_text(encoding="utf-8")

    assert 'down_revision = "20260510_0066_cdi_country_unique"' in contents

    for table_name in (
        "data_freshness_alerts",
        "source_freshness_snapshot",
        "sync_dead_letter",
    ):
        assert table_name in contents

    for fragment in (
        "ALTER TABLE IF EXISTS {table_name} ENABLE ROW LEVEL SECURITY",
        "CREATE POLICY esdata_all ON {table_name}",
        "CREATE POLICY service_role_all ON {table_name}",
        "DROP POLICY IF EXISTS esdata_all ON {table_name}",
        "DROP POLICY IF EXISTS service_role_all ON {table_name}",
    ):
        assert fragment in contents


def test_freshness_tables_are_owned_by_alembic_revision_0068():
    revision_path = ALEMBIC_VERSIONS / "20260511_0068_freshness_tables_schema.py"
    contents = revision_path.read_text(encoding="utf-8")

    assert 'down_revision = "20260510_0067_monitoring_rls_closure"' in contents
    for table_name in ("source_freshness_snapshot", "data_freshness_alerts"):
        assert f'"{table_name}"' in contents
        assert "ALTER TABLE IF EXISTS {table_name} ENABLE ROW LEVEL SECURITY" in contents

    for fragment in (
        "op.create_table(",
        "idx_source_snapshot_source",
        "idx_freshness_alerts_source",
        "CREATE POLICY esdata_all",
        "CREATE POLICY service_role_all",
    ):
        assert fragment in contents
