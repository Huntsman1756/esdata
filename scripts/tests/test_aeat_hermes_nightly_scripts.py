from __future__ import annotations

import shutil
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_json_batch_runner_uses_json_adapter_as_only_model_executor():
    source = (
        ROOT / "scripts" / "hermes_curator" / "bin" / "run-aeat-modelos-json.sh"
    ).read_text(encoding="utf-8")

    assert "run-aeat-model-json.sh" in source
    assert "modelo,status,json_file,markdown_file,raw_file" in source
    assert "Actua como auditor semantico senior" not in source
    assert "Formato markdown" not in source
    assert "failures=0" in source
    assert "exit 1" in source


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


def test_daily_run_wrapper_propagates_segment_failures(tmp_path):
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("bash is not available")

    try:
        probe = subprocess.run(
            [bash, "--version"],
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )
    except subprocess.TimeoutExpired:
        pytest.skip("bash is present but not usable in this environment")
    if probe.returncode != 0:
        pytest.skip("bash is present but not usable in this environment")

    root = tmp_path / "hermes-curator"
    bin_dir = root / "bin"
    reports_dir = root / "reports"
    bin_dir.mkdir(parents=True)
    reports_dir.mkdir()

    common = bin_dir / "common.sh"
    common.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                'ROOT="${HERMES_ESDATA_ROOT}"',
                'REPORTS="${ROOT}/reports"',
                "ts() { echo 20260528-000000; }",
                "iso() { echo 2026-05-28T00:00:00+02:00; }",
                "",
            ]
        ),
        encoding="utf-8",
        newline="\n",
    )

    for name in [
        "run-legal-sources.sh",
        "run-ops-health.sh",
        "run-qa-review.sh",
        "run-writer-summary.sh",
    ]:
        script = bin_dir / name
        script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8", newline="\n")
        script.chmod(script.stat().st_mode | stat.S_IEXEC)

    failing_script = bin_dir / "run-aeat-modelos.sh"
    failing_script.write_text("#!/usr/bin/env bash\nexit 42\n", encoding="utf-8", newline="\n")
    failing_script.chmod(failing_script.stat().st_mode | stat.S_IEXEC)

    wrapper = ROOT / "scripts" / "hermes_curator" / "bin" / "run-once.sh"
    result = subprocess.run(
        [bash, str(wrapper)],
        env={"HERMES_ESDATA_ROOT": str(root)},
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "ERROR aeat-modelos" in result.stdout
    assert "FAILED" in result.stdout
    assert "DONE" not in result.stdout
