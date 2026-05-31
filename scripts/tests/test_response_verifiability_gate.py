from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GATE_PATH = ROOT / "scripts" / "maintenance" / "response_verifiability_gate.py"


def _load_gate_module():
    spec = importlib.util.spec_from_file_location("response_verifiability_gate", GATE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_response_verifiability_gate_passes_current_repo():
    gate = _load_gate_module()

    result = gate.run_gate()

    assert result["ok"] is True
    assert result["issues"] == []


def test_contains_all_reports_missing_markers():
    gate = _load_gate_module()

    missing = gate._contains_all("source_url cited_chunks", ["source_url", "source_hash", "cited_chunks"])

    assert missing == ["source_hash"]
