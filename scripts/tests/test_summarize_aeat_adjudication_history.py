from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "maintenance" / "summarize_aeat_adjudication_history.py"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "summarize_aeat_adjudication_history", MODULE_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_history(
    path: Path,
    *,
    generated_at: str,
    ratios: dict[str, float],
    metrics: dict | None = None,
) -> None:
    payload = {
        "run_metadata": {
            "generated_at": generated_at,
            "git_head": f"head-{path.stem}",
            "adjudicator_version": "aeat-hermes-batch-adjudicator/v1",
        },
        "metrics": {
            "reports_total": 3,
            "ratios": ratios,
            **(metrics or {}),
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_summarize_history_reports_latest_run_and_deltas(tmp_path):
    module = _load_module()
    _write_history(
        tmp_path / "20260527T100000Z.json",
        generated_at="2026-05-27T10:00:00+00:00",
        ratios={
            "repaired_excerpt_ratio": 1.5,
            "rewrite_ratio": 0.2,
            "blocking_error_ratio": 0.0,
            "unused_source_warning_ratio": 0.1,
            "assertable_candidate_ratio": 0.0,
        },
    )
    _write_history(
        tmp_path / "20260527T110000Z.json",
        generated_at="2026-05-27T11:00:00+00:00",
        ratios={
            "repaired_excerpt_ratio": 1.0,
            "rewrite_ratio": 0.0,
            "blocking_error_ratio": 0.0,
            "unused_source_warning_ratio": 0.3,
            "assertable_candidate_ratio": 0.0,
        },
    )

    summary = module.summarize_history(tmp_path)

    assert summary["runs_total"] == 2
    assert summary["latest"]["generated_at"] == "2026-05-27T11:00:00+00:00"
    assert summary["latest"]["git_head"] == "head-20260527T110000Z"
    assert summary["deltas_vs_previous"] == {
        "repaired_excerpt_ratio": -0.5,
        "rewrite_ratio": -0.2,
        "blocking_error_ratio": 0.0,
        "unused_source_warning_ratio": 0.2,
        "assertable_candidate_ratio": 0.0,
    }


def test_summarize_history_emits_threshold_alerts(tmp_path):
    module = _load_module()
    _write_history(
        tmp_path / "20260527T120000Z.json",
        generated_at="2026-05-27T12:00:00+00:00",
        ratios={
            "repaired_excerpt_ratio": 2.0,
            "rewrite_ratio": 0.0,
            "blocking_error_ratio": 0.1,
            "unused_source_warning_ratio": 0.333333,
            "assertable_candidate_ratio": 0.0,
        },
    )

    summary = module.summarize_history(tmp_path)

    assert summary["alerts"] == [
        {
            "metric": "blocking_error_ratio",
            "value": 0.1,
            "threshold": 0.0,
            "severity": "critical",
        },
        {
            "metric": "repaired_excerpt_ratio",
            "value": 2.0,
            "threshold": 1.0,
            "severity": "warning",
        },
        {
            "metric": "unused_source_warning_ratio",
            "value": 0.333333,
            "threshold": 0.2,
            "severity": "warning",
        },
    ]


def test_summarize_history_falls_back_to_top_level_metrics(tmp_path):
    module = _load_module()
    _write_history(
        tmp_path / "20260527T130000Z.json",
        generated_at="2026-05-27T13:00:00+00:00",
        ratios={},
        metrics={"blocking_error_ratio": 0.0},
    )

    summary = module.summarize_history(tmp_path)

    assert summary["runs_total"] == 1
    assert summary["deltas_vs_previous"]["blocking_error_ratio"] is None
    assert summary["alerts"] == []


def test_summarize_history_handles_empty_directory(tmp_path):
    module = _load_module()

    summary = module.summarize_history(tmp_path)

    assert summary["runs_total"] == 0
    assert summary["latest"] is None
    assert summary["alerts"] == []
    assert all(value is None for value in summary["deltas_vs_previous"].values())
