import sys
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import entrypoint


def test_main_runs_worker_cmd_without_shell(monkeypatch):
    run = Mock(return_value=type("Completed", (), {"returncode": 0})())

    monkeypatch.setenv("WORKER_CMD", "python boe.py --run-once")
    monkeypatch.delenv("HEALTHCHECKS_PING_URL", raising=False)
    monkeypatch.setattr(entrypoint.subprocess, "run", run)

    assert entrypoint.main() == 0
    run.assert_called_once_with(["python", "boe.py", "--run-once"], shell=False)


def test_main_preserves_quoted_worker_cmd_arguments(monkeypatch):
    run = Mock(return_value=type("Completed", (), {"returncode": 0})())

    monkeypatch.setenv("WORKER_CMD", 'python worker.py --name "hello world"')
    monkeypatch.delenv("HEALTHCHECKS_PING_URL", raising=False)
    monkeypatch.setattr(entrypoint.subprocess, "run", run)

    assert entrypoint.main() == 0
    run.assert_called_once_with(["python", "worker.py", "--name", "hello world"], shell=False)
