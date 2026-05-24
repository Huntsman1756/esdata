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
