from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_json_batch_runner_uses_json_adapter_as_only_model_executor():
    source = (
        ROOT / "scripts" / "hermes_curator" / "bin" / "run-aeat-modelos-json.sh"
    ).read_text(encoding="utf-8")

    assert "run-aeat-model-json.sh" in source
    assert "modelo,status,json_file,markdown_file,raw_file" in source
    assert "Actua como auditor semantico senior" not in source
    assert "Formato markdown" not in source


def test_json_daily_summary_ignores_legacy_campaign_summary_as_source():
    source = (
        ROOT / "scripts" / "hermes_curator" / "bin" / "run-writer-summary-json.sh"
    ).read_text(encoding="utf-8")

    assert "mode: deterministic-json" in source
    assert "Campaign JSON summary" in source
    assert "Campaign legacy summary" in source
    assert "IGNORED" in source
    assert "JSON_ERRORS" in source
    assert "validated JSON is the primary artifact" in source


def test_single_model_json_runner_publishes_only_validated_json():
    source = (
        ROOT / "scripts" / "hermes_curator" / "bin" / "run-aeat-model-json.sh"
    ).read_text(encoding="utf-8")

    assert 'json_tmp="${json_file}.tmp"' in source
    assert '"$json_tmp"' in source
    assert 'mv "$json_tmp" "$json_file"' in source
    assert 'rm -f "$json_tmp"' in source
