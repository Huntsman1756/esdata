import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
AFFIRMATIVE_CAMPAIGN_RE = re.compile(
    r"\bcampa(?:n|ñ)a\s+(?:activa|vigente|verificada)\s+(?:es\s+)?\d{4}\b",
    re.IGNORECASE,
)


def assert_no_weak_campaign_assertion(payload: dict, rendered_text: str) -> None:
    can_assert = (
        payload.get("campana_safe_to_assert") is True
        and payload.get("campana_afirmable") is not None
        and payload.get("campana_assertion_code") == "ASSERTABLE_DIRECT_OFFICIAL"
    )
    if not can_assert:
        assert not AFFIRMATIVE_CAMPAIGN_RE.search(rendered_text)


def test_web_model_page_never_asserts_persisted_campaign_as_active():
    page = ROOT / "apps" / "web" / "app" / "modelo" / "[codigo]" / "page.tsx"
    source = page.read_text(encoding="utf-8")

    assert "CampaÃ±a {data.campana_activa}" not in source
    assert "data.campana_safe_to_assert" in source
    assert "data.campana_afirmable" in source
    assert 'data.campana_assertion_code === "ASSERTABLE_DIRECT_OFFICIAL"' in source
    assert "no verificada" in source


def test_consulta_ui_labels_model_campaign_as_unverified():
    page = ROOT / "apps" / "web" / "components" / "consulta-client.tsx"
    source = page.read_text(encoding="utf-8")

    assert "<strong>Campana:</strong> {m.campana}" not in source
    assert "Campana no verificada" in source


def test_web_model_type_exposes_assertion_contract_fields():
    types = ROOT / "apps" / "web" / "lib" / "types.ts"
    source = types.read_text(encoding="utf-8")

    assert "campana_persistida: string | null;" in source
    assert "campana_afirmable: string | null;" in source
    assert "campana_safe_to_assert: boolean;" in source
    assert "campana_assertion_code: string;" in source
    assert "campana_assertion_warning: string | null;" in source
    assert "campana_verification_level: string | null;" in source
    assert "campana_user_notice: string | null;" in source


def test_public_schemas_mark_campana_activa_as_deprecated_persisted_only():
    schemas = ROOT / "apps" / "api" / "schemas.py"
    source = schemas.read_text(encoding="utf-8")

    assert source.count("DEPRECATED: campana persistida") >= 3
    assert source.count("campana_safe_to_assert para afirmaciones fiscales") >= 3
    assert "campana_assertion_code" in source
    assert "campana_assertion_warning" in source


def test_mcp_stdio_labels_campaign_metadata_as_unverified():
    stdio = ROOT / "apps" / "api" / "mcp_stdio.py"
    source = stdio.read_text(encoding="utf-8")

    assert "Campaa: {modelo['campana']}" not in source
    assert "Campana interna no verificada" in source


def test_aeat_precision_contract_defines_only_direct_official_assertion_gate():
    contract = ROOT / "docs" / "aeat" / "precision-contract.md"
    source = contract.read_text(encoding="utf-8")

    assert "docs/aeat/curation-rules.md" in source
    assert "`campana_safe_to_assert = true`" in source
    assert "`campana_afirmable != null`" in source
    assert "`campana_assertion_code = ASSERTABLE_DIRECT_OFFICIAL`" in source
    assert "`NOT_ASSERTABLE_INFERRED_INTERNAL`" in source
    assert "`NOT_ASSERTABLE_CONFLICT`" in source
    assert "`INSUFFICIENT_EVIDENCE`" in source
    assert "`STALE_SUSPECTED`" in source
    assert "Never use `campana_activa`, `campana_persistida` or `campana_candidata`" in source


def test_weak_campaign_payload_detector_blocks_affirmative_text():
    weak_payload = {
        "campana_activa": "2025",
        "campana_persistida": "2025",
        "campana_candidata": "2025",
        "campana_afirmable": None,
        "campana_safe_to_assert": False,
        "campana_assertion_code": "NOT_ASSERTABLE_INFERRED_INTERNAL",
    }

    assert_no_weak_campaign_assertion(
        weak_payload,
        "Campana no verificada: dato interno 2025",
    )
    with pytest.raises(AssertionError):
        assert_no_weak_campaign_assertion(weak_payload, "La campana activa es 2025")


def test_strong_campaign_payload_detector_allows_affirmative_text():
    strong_payload = {
        "campana_activa": "2025",
        "campana_persistida": "2025",
        "campana_candidata": "2025",
        "campana_afirmable": "2025",
        "campana_safe_to_assert": True,
        "campana_assertion_code": "ASSERTABLE_DIRECT_OFFICIAL",
    }

    assert_no_weak_campaign_assertion(strong_payload, "La campana verificada 2025")


def test_aeat_curation_rules_reject_heuristic_promotion():
    rules = ROOT / "docs" / "aeat" / "curation-rules.md"
    source = rules.read_text(encoding="utf-8")

    assert "promoted to `resolved_strong` only when there is direct official" in source
    assert "BOE publication date alone is not campaign evidence" in source
    assert "File name, XSD/WSDL" in source
    assert "Never promote campaigns in bulk" in source
    assert "Do not select the latest\nyear automatically" in source
    assert "prefer\n`stale_suspected`" in source
    assert "Do not use total `resolved` count as a fiscal precision KPI" in source
