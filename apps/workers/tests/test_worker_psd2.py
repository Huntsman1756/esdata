"""Tests para constantes regulatorias de PSD2."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from psd2 import PSD2_NORMA
import psd2_eba


def test_psd2_norma_uses_validated_celex_id():
    assert PSD2_NORMA["boe_id"] == "EUR-CELEX-32015L2366"


def test_psd2_eba_checks_database_connection_before_sync(monkeypatch):
    calls = []

    class FakeConnection:
        def execute(self, *_args, **_kwargs):
            calls.append("execute")

    class FakeTransaction:
        def __enter__(self):
            return FakeConnection()

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeEngine:
        def begin(self):
            return FakeTransaction()

    fake_engine = FakeEngine()

    monkeypatch.setattr(psd2_eba, "create_engine", lambda *_args, **_kwargs: fake_engine)
    monkeypatch.setattr(psd2_eba, "_try_fetch_eba_direct", lambda: [])
    monkeypatch.setattr(
        psd2_eba,
        "ensure_database_connection",
        lambda engine, logger=None: calls.append(("ensure", engine)),
    )

    result = psd2_eba.run_sync()

    assert calls[0] == ("ensure", fake_engine)
    assert result["rows_processed"] == 0
