"""Tests for ESMA authorised DLT infrastructure loader."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from worker_esma_dlt import AUTHORISED_DLT_INFRASTRUCTURES, validate_pdf_contains_official_rows


def test_authorised_dlt_dataset_matches_current_official_pdf_rows():
    records = AUTHORISED_DLT_INFRASTRUCTURES

    assert len(records) == 6
    assert {record.pais for record in records} == {"CZE", "DEU", "ESP", "FRA", "LTU"}
    assert any(record.operator == "Securitize Europe Brokerage and Markets SV SA" for record in records)
    assert sum(len(record.exemptions) for record in records) > 50


def test_validate_pdf_contains_official_rows_accepts_expected_text():
    pdf_text = "\n".join(
        f"{record.operator} {record.infrastructure_name} {record.autoridad_competente} {record.source_date_label}"
        for record in AUTHORISED_DLT_INFRASTRUCTURES
    )

    validate_pdf_contains_official_rows(pdf_text, AUTHORISED_DLT_INFRASTRUCTURES)


def test_validate_pdf_contains_official_rows_rejects_changed_pdf():
    with pytest.raises(RuntimeError, match="no longer matches"):
        validate_pdf_contains_official_rows("21X AG only", AUTHORISED_DLT_INFRASTRUCTURES)
