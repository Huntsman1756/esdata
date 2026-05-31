from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GATE_PATH = ROOT / "scripts" / "maintenance" / "source_assurance_gate.py"


def _load_gate():
    spec = importlib.util.spec_from_file_location("source_assurance_gate", GATE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_source_assurance_gate_passes_current_repo():
    gate = _load_gate()

    result = gate.run_gate()

    assert result["ok"], result["issues"]


def test_dangerous_positive_claim_is_detected():
    gate = _load_gate()

    assert any(pattern.search("List all AEAT tax form models") for pattern in gate.DANGEROUS_PATTERNS)
    assert not gate._is_negated("List all AEAT tax form models")


def test_negated_complete_coverage_warning_is_allowed():
    gate = _load_gate()

    assert gate._is_negated("Do not claim complete coverage of ESMA.")
