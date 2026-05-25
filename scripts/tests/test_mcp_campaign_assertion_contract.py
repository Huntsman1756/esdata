from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_web_model_page_never_asserts_persisted_campaign_as_active():
    page = ROOT / "apps" / "web" / "app" / "modelo" / "[codigo]" / "page.tsx"
    source = page.read_text(encoding="utf-8")

    assert "CampaÃ±a {data.campana_activa}" not in source
    assert "data.campana_safe_to_assert" in source
    assert "data.campana_afirmable" in source
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
