#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

DEFAULT_THRESHOLDS = {
    "blocking_error_ratio": 0.0,
    "rewrite_ratio": 0.10,
    "repaired_excerpt_ratio": 1.0,
    "unused_source_warning_ratio": 0.20,
    "assertable_candidate_ratio": 0.0,
}


def _load_history_file(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: root must be object")
    return payload


def load_history(history_dir: Path) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    for path in sorted(history_dir.glob("*.json")):
        payload = _load_history_file(path)
        metadata = payload.get("run_metadata", {})
        metrics = payload.get("metrics", {})
        if not isinstance(metadata, dict) or not isinstance(metrics, dict):
            continue
        runs.append(
            {
                "path": str(path),
                "generated_at": metadata.get("generated_at"),
                "git_head": metadata.get("git_head"),
                "adjudicator_version": metadata.get("adjudicator_version"),
                "metrics": metrics,
            }
        )
    return runs


def _metric(run: dict[str, Any], name: str, default: float = 0.0) -> float:
    metrics = run.get("metrics", {})
    ratios = metrics.get("ratios", {}) if isinstance(metrics, dict) else {}
    if isinstance(ratios, dict) and name in ratios:
        return float(ratios[name])
    if isinstance(metrics, dict) and name in metrics:
        return float(metrics[name])
    return default


def _trend_delta(runs: list[dict[str, Any]], metric: str) -> float | None:
    if len(runs) < 2:
        return None
    return round(_metric(runs[-1], metric) - _metric(runs[-2], metric), 6)


def _alerts(latest: dict[str, Any], thresholds: dict[str, float]) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    for metric, threshold in thresholds.items():
        value = _metric(latest, metric)
        if value > threshold:
            alerts.append(
                {
                    "metric": metric,
                    "value": value,
                    "threshold": threshold,
                    "severity": "critical" if metric == "blocking_error_ratio" else "warning",
                }
            )
    return alerts


def summarize_history(
    history_dir: Path,
    *,
    thresholds: dict[str, float] | None = None,
) -> dict[str, Any]:
    thresholds = thresholds or DEFAULT_THRESHOLDS
    runs = load_history(history_dir)
    latest = runs[-1] if runs else None
    trend_metrics = [
        "repaired_excerpt_ratio",
        "rewrite_ratio",
        "blocking_error_ratio",
        "unused_source_warning_ratio",
        "assertable_candidate_ratio",
    ]
    return {
        "history_dir": str(history_dir),
        "runs_total": len(runs),
        "latest": latest,
        "deltas_vs_previous": {
            metric: _trend_delta(runs, metric) for metric in trend_metrics
        },
        "alerts": _alerts(latest, thresholds) if latest else [],
        "thresholds": thresholds,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize AEAT Hermes adjudication history trends."
    )
    parser.add_argument("history_dir", type=Path)
    parser.add_argument(
        "--fail-on-alert",
        action="store_true",
        help="Exit non-zero if any threshold alert is present.",
    )
    args = parser.parse_args()

    summary = summarize_history(args.history_dir)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.fail_on_alert and summary["alerts"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
