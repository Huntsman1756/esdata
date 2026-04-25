"""Tests para search_legislacion con soporte de chunks."""

import pytest
from pathlib import Path
from sqlalchemy import text
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.search import search_legislacion, _chunk_rank_boost


class TestChunkRankBoost:
    def test_boost_applies_when_has_chunks(self):
        rank = _chunk_rank_boost(True, 0.5)
        assert rank == pytest.approx(0.55)

    def test_no_boost_when_no_chunks(self):
        rank = _chunk_rank_boost(False, 0.5)
        assert rank == pytest.approx(0.5)

    def test_zero_rank_unchanged(self):
        rank = _chunk_rank_boost(True, 0.0)
        assert rank == pytest.approx(0.0)


class TestSearchLegislacionSmoke:
    """Smoke test: search_legislacion returns expected keys and doesn't crash."""

    @pytest.fixture
    def db_url(self):
        import os
        return os.environ.get("DATABASE_URL", "sqlite:///test_esdata.sqlite3")

    def test_returns_q_and_resultados(self, db_url):
        import os
        os.environ["DATABASE_URL"] = db_url

        result = search_legislacion("pan")

        assert "q" in result
        assert result["q"] == "pan"
        assert "resultados" in result
        assert isinstance(result["resultados"], list)

    def test_each_result_has_required_keys(self, db_url):
        import os
        os.environ["DATABASE_URL"] = db_url

        result = search_legislacion("pan")

        if result["resultados"]:
            row = result["resultados"][0]
            required = [
                "tipo", "norma", "numero", "texto", "fragmento",
                "vigente_desde", "vigente_hasta", "rank",
                "fuente_norma", "source_url", "motivo_ranking", "confianza",
            ]
            for key in required:
                assert key in row, f"Missing key: {key}"

    def test_fragmento_is_string(self, db_url):
        import os
        os.environ["DATABASE_URL"] = db_url

        result = search_legislacion("pan")

        for row in result["resultados"]:
            assert isinstance(row["fragmento"], str)

    def test_vigente_en_filter(self, db_url):
        import os
        os.environ["DATABASE_URL"] = db_url

        result = search_legislacion("pan", vigente_en="2024-01-01")

        assert "q" in result
        assert "resultados" in result
        assert isinstance(result["resultados"], list)

    def test_norma_filter(self, db_url):
        import os
        os.environ["DATABASE_URL"] = db_url

        result = search_legislacion("pan", norma="LIVA")

        assert "q" in result
        assert "resultados" in result
        assert isinstance(result["resultados"], list)

    def test_empty_query_returns_list(self, db_url):
        import os
        os.environ["DATABASE_URL"] = db_url

        result = search_legislacion("")

        assert "q" in result
        assert result["q"] == ""
        assert "resultados" in result
        assert isinstance(result["resultados"], list)
