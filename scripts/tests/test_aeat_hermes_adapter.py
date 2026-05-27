from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXTRACTOR_PATH = ROOT / "scripts" / "maintenance" / "extract_aeat_hermes_json.py"
RENDERER_PATH = ROOT / "scripts" / "maintenance" / "render_aeat_hermes_report.py"
PROMPT_PATH = ROOT / "scripts" / "hermes_curator" / "prompts" / "aeat_model_json.md"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _report() -> dict:
    return {
        "schema_version": "aeat-hermes-curation-output/v1",
        "model_code": "210",
        "decision": "CONFLICT",
        "assertion_gate": {
            "campana_safe_to_assert": False,
            "campana_afirmable": None,
            "campana_assertion_code": "NOT_ASSERTABLE_CONFLICT",
        },
        "mcp_observations": [
            {
                "endpoint_or_tool": "get_modelo_resumen_operativo",
                "field": "campana_resolution_status",
                "value": "conflict",
                "purpose": "system_state",
            }
        ],
        "official_sources": [
            {
                "source_id": "AEAT_GF00",
                "authority": "AEAT",
                "url": "https://sede.agenciatributaria.gob.es/Sede/procedimientoini/GF00.shtml",
                "locator": "Gestiones destacadas",
                "excerpt": "Modelo 210. Devengos 2019 y siguientes. Presentacion",
            }
        ],
        "official_source_claims": [
            {
                "claim": "La pagina AEAT contiene una gestion del modelo 210 para devengos 2019 y siguientes.",
                "source_id": "AEAT_GF00",
                "evidence_kind": "literal_text",
                "proves_campaign": False,
            }
        ],
        "derived_claims": [],
        "system_observed_claims": [
            {
                "claim": "ESData marca el modelo 210 como conflictivo.",
                "mcp_observation_indexes": [0],
                "may_assert_campaign": False,
            }
        ],
        "rejected_claims": [
            {
                "claim": "La campana 2026 esta activa.",
                "reason": "No hay evidencia oficial directa.",
                "blocked_by": "no_direct_official_evidence",
            }
        ],
        "human_review_required": True,
    }


def test_extract_json_block_ignores_runtime_noise():
    module = _load(EXTRACTOR_PATH, "extract_aeat_hermes_json")
    payload = _report()
    raw = (
        "Dropping root privileges\n"
        "BEGIN_AEAT_HERMES_JSON\n"
        f"{json.dumps(payload)}\n"
        "END_AEAT_HERMES_JSON\n"
        "session_id: abc\n"
    )

    assert module.extract_json_block(raw) == payload


def test_extract_json_block_rejects_missing_markers():
    module = _load(EXTRACTOR_PATH, "extract_aeat_hermes_json")

    try:
        module.extract_json_block(json.dumps(_report()))
    except ValueError as exc:
        assert "missing BEGIN_AEAT_HERMES_JSON" in str(exc)
    else:
        raise AssertionError("expected marker failure")


def test_extract_json_block_uses_last_parseable_block_after_diff_noise():
    module = _load(EXTRACTOR_PATH, "extract_aeat_hermes_json")
    payload = _report()
    raw = (
        "review diff\n"
        "+BEGIN_AEAT_HERMES_JSON\n"
        "+{not valid json from diff\n"
        "The lint error is because the file contains markers.\n"
        "BEGIN_AEAT_HERMES_JSON\n"
        f"{json.dumps(payload)}\n"
        "END_AEAT_HERMES_JSON\n"
    )

    assert module.extract_json_block(raw) == payload


def test_extract_json_block_prunes_transactional_sources_and_claims():
    module = _load(EXTRACTOR_PATH, "extract_aeat_hermes_json")
    payload = _report()
    payload["official_sources"].append(
        {
            "source_id": "AEAT_OV16_M113",
            "authority": "AEAT",
            "url": "https://www1.agenciatributaria.gob.es/wlpl/OV16-M113/index.zul",
            "locator": "Formulario transaccional",
            "excerpt": "Formulario Html del modelo 113",
        }
    )
    payload["official_source_claims"].append(
        {
            "claim": "El formulario transaccional del modelo 113 esta disponible.",
            "source_id": "AEAT_OV16_M113",
            "evidence_kind": "literal_text",
            "proves_campaign": False,
        }
    )
    raw = (
        "BEGIN_AEAT_HERMES_JSON\n"
        f"{json.dumps(payload)}\n"
        "END_AEAT_HERMES_JSON\n"
    )

    extracted = module.extract_json_block(raw)

    assert [source["source_id"] for source in extracted["official_sources"]] == [
        "AEAT_GF00"
    ]
    assert [claim["source_id"] for claim in extracted["official_source_claims"]] == [
        "AEAT_GF00"
    ]
    assert extracted["rejected_claims"][-1] == {
        "claim": "El formulario transaccional del modelo 113 esta disponible.",
        "reason": "Transactional AEAT form URLs are not documentary evidence sources.",
        "blocked_by": "insufficient_locator",
    }


def test_extract_json_block_prunes_unreferenced_official_sources():
    module = _load(EXTRACTOR_PATH, "extract_aeat_hermes_json")
    payload = _report()
    payload["official_sources"].append(
        {
            "source_id": "AEAT_UNUSED",
            "authority": "AEAT",
            "url": "https://sede.agenciatributaria.gob.es/Sede/procedimientoini/G614.shtml",
            "locator": "Fuente no usada",
            "excerpt": "Modelo 113",
        }
    )
    raw = (
        "BEGIN_AEAT_HERMES_JSON\n"
        f"{json.dumps(payload)}\n"
        "END_AEAT_HERMES_JSON\n"
    )

    extracted = module.extract_json_block(raw)

    assert [source["source_id"] for source in extracted["official_sources"]] == [
        "AEAT_GF00"
    ]


def test_render_markdown_is_view_not_source_of_truth():
    module = _load(RENDERER_PATH, "render_aeat_hermes_report")

    rendered = module.render_report(_report())

    assert "# Modelo 210 - Hermes AEAT structured curation" in rendered
    assert "This markdown is a rendered view of validated JSON" in rendered
    assert "AEAT_GF00" in rendered
    assert "La campana 2026 esta activa." in rendered


def test_prompt_requires_literal_excerpts_for_html_sources():
    prompt = PROMPT_PATH.read_text(encoding="utf-8")

    assert "excerpt` debe ser texto literal" in prompt
    assert "No resumas, no parafrasees" in prompt
    assert "subcadena que pueda" in prompt
    assert "fuentes binarias oficiales" in prompt


def test_prompt_forbids_unreferenced_official_sources():
    prompt = PROMPT_PATH.read_text(encoding="utf-8")

    assert "official_sources debe contener solo fuentes usadas" in prompt
    assert "No incluyas fuentes oficiales auxiliares" in prompt


def test_prompt_requires_nonassertive_claims_for_official_model_sources():
    prompt = PROMPT_PATH.read_text(encoding="utf-8")

    assert "Si una fuente oficial verifica la identidad del modelo" in prompt
    assert "proves_campaign=false" in prompt
    assert "no dejes `official_source_claims` vacio" in prompt


def test_prompt_forbids_unprovided_boe_or_legal_sources():
    prompt = PROMPT_PATH.read_text(encoding="utf-8")

    assert "No introduzcas BOE, articulos legales o normas" in prompt
    assert "si no aparecen explicitamente" in prompt
    assert "get_modelo_fuentes_oficiales" in prompt


def test_prompt_forbids_transactional_forms_as_official_claim_sources():
    prompt = PROMPT_PATH.read_text(encoding="utf-8")

    assert "No uses formularios transaccionales" in prompt
    assert "www1.agenciatributaria.gob.es/wlpl/OV16" in prompt


def test_prompt_requires_strict_html_excerpt_lines():
    prompt = PROMPT_PATH.read_text(encoding="utf-8")

    assert "Regla estricta de excerpt HTML" in prompt
    assert "Si no puedes señalar exactamente que linea visible del HTML" in prompt
    assert "No uses locators genericos" in prompt
    assert "titulo de pagina" in prompt
    assert "No uses excerpts descriptivos/parafraseados" in prompt
    assert "Si una fuente solo confirma navegacion" in prompt


def test_prompt_requires_specific_locator_text_not_bare_html_tags():
    prompt = PROMPT_PATH.read_text(encoding="utf-8")

    assert "No uses locators desnudos" in prompt
    assert "`<title>` a secas" in prompt
    assert "incluye el texto visible concreto" in prompt
