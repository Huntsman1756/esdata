"""Guardrails for the canonical AEAT seed flow."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_root_seed_scripts_document_the_canonical_aeat_flow():
    seed_modelos = _read("scripts/seed-modelos.py")
    assert "CANONICAL AEAT FLOW - STEP 1 OF 2" in seed_modelos
    assert "python scripts/seed-modelos-v2.py" in seed_modelos

    seed_modelos_v2 = _read("scripts/seed-modelos-v2.py")
    assert "CANONICAL AEAT FLOW - STEP 2 OF 2" in seed_modelos_v2
    assert "python scripts/seed-modelos.py" in seed_modelos_v2


def test_legacy_aeat_seed_paths_are_marked_non_authoritative():
    legacy_paths = [
        "scripts/data/seed_modelos.py",
        "scripts/data/seed_aeat_models.py",
        "scripts/data/seed_modelo_articulo.py",
        "scripts/seed-fiscal-modelos.sql",
    ]

    for relative_path in legacy_paths:
        assert "LEGACY / NO AUTORITATIVO" in _read(relative_path), relative_path


def test_seed_all_warns_that_aeat_is_not_canonical_there():
    seed_all = _read("scripts/data/seed_all.py")
    assert "WARNING: seed_all.py is not the canonical production AEAT flow." in seed_all
    assert "scripts/seed-modelos.py" in seed_all
    assert "scripts/seed-modelos-v2.py" in seed_all
