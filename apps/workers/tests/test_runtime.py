import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import runtime
from sqlalchemy.exc import OperationalError


def test_sleep_with_heartbeat_touches_before_each_sleep_chunk(monkeypatch):
    touched = []
    slept = []

    class FakeHeartbeatPath:
        def __init__(self, value: str):
            self.value = value

        def touch(self):
            touched.append(self.value)

    monkeypatch.setattr(runtime, "Path", FakeHeartbeatPath)
    monkeypatch.setattr(runtime.time, "sleep", slept.append)

    runtime.sleep_with_heartbeat(125, chunk_seconds=60, heartbeat_path="/tmp/test-heartbeat")

    assert touched == ["/tmp/test-heartbeat", "/tmp/test-heartbeat", "/tmp/test-heartbeat"]
    assert slept == [60, 60, 5]


def test_sleep_with_heartbeat_skips_non_positive_intervals(monkeypatch):
    touched = []
    slept = []

    class FakeHeartbeatPath:
        def __init__(self, value: str):
            self.value = value

        def touch(self):
            touched.append(self.value)

    monkeypatch.setattr(runtime, "Path", FakeHeartbeatPath)
    monkeypatch.setattr(runtime.time, "sleep", slept.append)

    runtime.sleep_with_heartbeat(0)

    assert touched == []
    assert slept == []


def test_sleep_with_heartbeat_uses_custom_touch_function(monkeypatch):
    touched = []
    slept = []

    monkeypatch.setattr(runtime.time, "sleep", slept.append)

    runtime.sleep_with_heartbeat(125, chunk_seconds=60, touch_fn=lambda: touched.append("touch"))

    assert touched == ["touch", "touch", "touch"]
    assert slept == [60, 60, 5]


def test_ensure_database_connection_retries_dns_and_connect(monkeypatch):
    attempts = []
    sleep_calls = []
    log_messages = []
    dns_calls = []

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, statement):
            attempts.append(str(statement))

    class FakeEngine:
        def __init__(self):
            self.url = type("URL", (), {"host": "postgres", "port": 5432})()
            self.connect_calls = 0

        def connect(self):
            self.connect_calls += 1
            if self.connect_calls == 1:
                raise OperationalError("SELECT 1", {}, OSError("dns down"))
            return FakeConnection()

    class FakeLogger:
        def info(self, message, *args):
            log_messages.append(("info", message % args if args else message))

        def warning(self, message, *args):
            log_messages.append(("warning", message % args if args else message))

    def fake_getaddrinfo(host, port, *args, **kwargs):
        dns_calls.append((host, port))
        if len(dns_calls) == 1:
            raise socket.gaierror(-3, "Temporary failure in name resolution")
        return [(None, None, None, None, ("172.19.0.5", port))]

    import socket

    monkeypatch.setattr(runtime.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(runtime.time, "sleep", sleep_calls.append)

    engine = FakeEngine()
    runtime.ensure_database_connection(engine, logger=FakeLogger())

    assert engine.connect_calls == 2
    assert dns_calls == [("postgres", 5432), ("postgres", 5432), ("postgres", 5432)]
    assert attempts == ["SELECT 1"]
    assert sleep_calls == [2, 4]
    assert log_messages == [
        ("warning", "DNS probe failed for postgres:5432: [Errno -3] Temporary failure in name resolution"),
        ("warning", "DB connection attempt 1/5 failed: [Errno -3] Temporary failure in name resolution"),
        ("info", "DB DNS resolved: postgres -> 172.19.0.5"),
        ("warning", "DB connection attempt 2/5 failed: (builtins.OSError) dns down\n[SQL: SELECT 1]\n(Background on this error at: https://sqlalche.me/e/20/e3q8)"),
        ("info", "DB DNS resolved: postgres -> 172.19.0.5"),
        ("info", "DB connection established"),
    ]
