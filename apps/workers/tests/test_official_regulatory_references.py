import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from official_regulatory_references import (
    CSRD_ESRS_ROWS,
    CSRD_SOURCE_URL,
    DORA_REPORTING_SOURCE_URL,
    PBC_OBLIGATED_SUBJECT_ROWS,
    PBC_SOURCE_URL,
    IRS_FISCAL_NORMA_ROWS,
    IRS_MODELO_ROWS,
    IRS_TIN_REFERENCE_ROWS,
    IRS_WITHHOLDING_RULE_ROWS,
    AEAT_OBLIGATION_MODELS,
    SCREENING_LIST_ROWS,
    SEPA_RULE_ROWS,
    _hash_payload,
)


def test_csrd_esrs_catalog_is_complete_and_official():
    codes = [code for code, _topic in CSRD_ESRS_ROWS]

    assert codes == [
        "ESRS 1",
        "ESRS 2",
        "ESRS E1",
        "ESRS E2",
        "ESRS E3",
        "ESRS E4",
        "ESRS E5",
        "ESRS S1",
        "ESRS S2",
        "ESRS S3",
        "ESRS S4",
        "ESRS G1",
    ]
    assert CSRD_SOURCE_URL.startswith("https://eur-lex.europa.eu/")
    assert "32023R2772" in CSRD_SOURCE_URL


def test_dora_reporting_source_is_current_eurlex_rts():
    assert DORA_REPORTING_SOURCE_URL.startswith("https://eur-lex.europa.eu/")
    assert "32025R0301" in DORA_REPORTING_SOURCE_URL


def test_sepa_rows_are_reference_metadata_not_fixtures():
    assert len(SEPA_RULE_ROWS) == 2
    assert {row["payment_type"] for row in SEPA_RULE_ROWS} == {
        "credit_transfer",
        "instant_credit_transfer",
    }
    assert all(row["source_url"].startswith("https://eur-lex.europa.eu/") for row in SEPA_RULE_ROWS)
    assert all(row["category_purpose"] is None for row in SEPA_RULE_ROWS)


def test_reference_hash_is_deterministic():
    left = {"b": 2, "a": 1}
    right = {"a": 1, "b": 2}

    assert _hash_payload(left) == _hash_payload(right)


def test_pbc_obligated_subjects_are_category_metadata():
    assert len(PBC_OBLIGATED_SUBJECT_ROWS) >= 5
    assert PBC_SOURCE_URL.startswith("https://www.boe.es/")
    assert "BOE-A-2010-6737" in PBC_SOURCE_URL


def test_screening_lists_are_official_list_metadata_only():
    codes = {row["codigo"] for row in SCREENING_LIST_ROWS}

    assert codes == {"EU_SANCTIONS", "SEPBLAC"}
    assert all(row["url_fuente"].startswith(("https://finance.ec.europa.eu/", "https://www.sepblac.es/")) for row in SCREENING_LIST_ROWS)
    assert all("Entries require" in row["descripcion"] for row in SCREENING_LIST_ROWS)


def test_irs_reference_rows_use_official_sources_and_are_minimal():
    assert all(row["url_fuente"].startswith("https://www.irs.gov/") for row in IRS_FISCAL_NORMA_ROWS)
    assert {row[0] for row in IRS_MODELO_ROWS} >= {"W-8BEN", "W-8BEN-E"}
    assert all(row[2].startswith("https://www.irs.gov/") for row in IRS_MODELO_ROWS)
    assert {row["codigo_pais"] for row in IRS_TIN_REFERENCE_ROWS} == {"ES", "US"}
    assert all(row["source_url"].startswith(("https://www.oecd.org/", "https://www.irs.gov/")) for row in IRS_TIN_REFERENCE_ROWS)
    assert IRS_WITHHOLDING_RULE_ROWS[0]["tipo_retencion_default"] == 30.0
    assert IRS_WITHHOLDING_RULE_ROWS[0]["source_url"].startswith("https://www.irs.gov/")


def test_aeat_obligation_models_are_explicit_allowlist():
    assert {"100", "200", "303", "390"}.issubset(set(AEAT_OBLIGATION_MODELS))
    assert all(code.isdigit() for code in AEAT_OBLIGATION_MODELS)
