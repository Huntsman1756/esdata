"""Tests para constantes regulatorias de PSD2."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from psd2 import PSD2_NORMA


def test_psd2_norma_uses_validated_celex_id():
    assert PSD2_NORMA["boe_id"] == "EUR-CELEX-32015L2366"
