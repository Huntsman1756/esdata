import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import runtime


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
