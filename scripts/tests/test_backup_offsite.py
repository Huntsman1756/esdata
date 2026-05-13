import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "backup-offsite.sh"
SCRIPT_ARG = "scripts/backup-offsite.sh"


def test_backup_offsite_script_has_valid_bash_syntax():
    result = subprocess.run(
        ["bash", "-n", SCRIPT_ARG],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_backup_offsite_script_requires_remote_configuration():
    env = os.environ.copy()
    env.pop("ESDATA_BACKUP_REMOTE", None)

    result = subprocess.run(
        ["bash", SCRIPT_ARG, "--check-config"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "ESDATA_BACKUP_REMOTE is required" in result.stdout


def test_backup_offsite_script_does_not_embed_provider_secrets():
    text = SCRIPT.read_text(encoding="utf-8")

    forbidden_tokens = [
        "AWS" + "_SECRET",
        "B2" + "_KEY",
        "ACCESS" + "_KEY",
        "SECRET" + "_ACCESS",
        "S3" + "_SECRET",
        "RCLONE" + "_CONFIG" + "_PASS",
    ]

    assert not any(token in text for token in forbidden_tokens)
