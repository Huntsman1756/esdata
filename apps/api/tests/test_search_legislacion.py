"""Tests para search_legislacion con soporte de chunks."""

import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
from sqlalchemy.exc import ProgrammingError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "workers"))

from services.search import _chunk_rank_boost, _search_legislacion_pg, search_legislacion


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
                "chunk_id", "source_hash",
            ]
            for key in required:
                assert key in row, f"Missing key: {key}"

    def test_result_exposes_chunk_grounding_when_available(self, db_url):
        import os

        os.environ["DATABASE_URL"] = db_url

        result = search_legislacion("tipo reducido", norma="LIVA")

        assert result["resultados"]
        row = result["resultados"][0]
        assert row["source_hash"]
        assert len(row["source_hash"]) == 64
        assert "chunk_id" in row

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

    def test_search_legislacion_returns_cc_after_legalize_seed(self, db_url):
        import os
        from sqlalchemy import create_engine, text
        from legalize_es import run_sync

        os.environ["DATABASE_URL"] = db_url
        engine = create_engine(db_url, future=True)

        fixture = Path(__file__).resolve().parents[2] / "workers" / "tests" / "fixtures" / "legalize_es" / "cc.md"

        with engine.begin() as conn:
            conn.execute(text("DELETE FROM version_articulo WHERE articulo_id IN (SELECT id FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'CC'))"))
            conn.execute(text("DELETE FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'CC')"))
            conn.execute(text("DELETE FROM norma WHERE codigo = 'CC'"))

        run_sync(engine, fixture_paths=[fixture])
        result = search_legislacion("ordenamiento", norma="CC")

        assert result["resultados"]
        assert any(row["norma"] == "CC" for row in result["resultados"])

    def test_search_legislacion_returns_lec_after_legalize_seed(self, db_url):
        import os
        from sqlalchemy import create_engine, text
        from legalize_es import run_sync

        os.environ["DATABASE_URL"] = db_url
        engine = create_engine(db_url, future=True)

        fixture = Path(__file__).resolve().parents[2] / "workers" / "tests" / "fixtures" / "legalize_es" / "lec.md"

        with engine.begin() as conn:
            conn.execute(text("DELETE FROM version_articulo WHERE articulo_id IN (SELECT id FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'LEC'))"))
            conn.execute(text("DELETE FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'LEC')"))
            conn.execute(text("DELETE FROM norma WHERE codigo = 'LEC'"))

        run_sync(engine, fixture_paths=[fixture])
        result = search_legislacion("ley", norma="LEC")

        assert result["resultados"]
        assert any(row["norma"] == "LEC" for row in result["resultados"])

    def test_search_legislacion_returns_et_after_legalize_seed(self, db_url):
        import os
        from sqlalchemy import create_engine, text
        from legalize_es import run_sync

        os.environ["DATABASE_URL"] = db_url
        engine = create_engine(db_url, future=True)

        fixture = Path(__file__).resolve().parents[2] / "workers" / "tests" / "fixtures" / "legalize_es" / "et.md"

        with engine.begin() as conn:
            conn.execute(text("DELETE FROM version_articulo WHERE articulo_id IN (SELECT id FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'ET'))"))
            conn.execute(text("DELETE FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'ET')"))
            conn.execute(text("DELETE FROM norma WHERE codigo = 'ET'"))

        run_sync(engine, fixture_paths=[fixture])
        result = search_legislacion("estatuto", norma="ET")

        assert result["resultados"]
        assert any(row["norma"] == "ET" for row in result["resultados"])

    def test_search_legislacion_vigente_en_filter_lec(self, db_url):
        import os
        from sqlalchemy import create_engine, text
        from legalize_es import run_sync

        os.environ["DATABASE_URL"] = db_url
        engine = create_engine(db_url, future=True)

        fixture = Path(__file__).resolve().parents[2] / "workers" / "tests" / "fixtures" / "legalize_es" / "lec.md"

        with engine.begin() as conn:
            conn.execute(text("DELETE FROM version_articulo WHERE articulo_id IN (SELECT id FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'LEC'))"))
            conn.execute(text("DELETE FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'LEC')"))
            conn.execute(text("DELETE FROM norma WHERE codigo = 'LEC'"))

        run_sync(engine, fixture_paths=[fixture])
        result = search_legislacion("ley", norma="LEC", vigente_en="2025-01-01")

        assert result["resultados"]
        assert all(row["norma"] == "LEC" for row in result["resultados"])

    def test_search_legislacion_returns_lsc_after_legalize_seed(self, db_url):
        import os
        from sqlalchemy import create_engine, text
        from legalize_es import run_sync

        os.environ["DATABASE_URL"] = db_url
        engine = create_engine(db_url, future=True)

        fixture = Path(__file__).resolve().parents[2] / "workers" / "tests" / "fixtures" / "legalize_es" / "lsc.md"

        with engine.begin() as conn:
            conn.execute(text("DELETE FROM version_articulo WHERE articulo_id IN (SELECT id FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'LSC'))"))
            conn.execute(text("DELETE FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'LSC')"))
            conn.execute(text("DELETE FROM norma WHERE codigo = 'LSC'"))

        run_sync(engine, fixture_paths=[fixture])
        result = search_legislacion("sociedades", norma="LSC")

        assert result["resultados"]
        assert any(row["norma"] == "LSC" for row in result["resultados"])

    def test_search_legislacion_returns_lc_after_legalize_seed(self, db_url):
        import os
        from sqlalchemy import create_engine, text
        from legalize_es import run_sync

        os.environ["DATABASE_URL"] = db_url
        engine = create_engine(db_url, future=True)

        fixture = Path(__file__).resolve().parents[2] / "workers" / "tests" / "fixtures" / "legalize_es" / "lc.md"

        with engine.begin() as conn:
            conn.execute(text("DELETE FROM version_articulo WHERE articulo_id IN (SELECT id FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'LC'))"))
            conn.execute(text("DELETE FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'LC')"))
            conn.execute(text("DELETE FROM norma WHERE codigo = 'LC'"))

        run_sync(engine, fixture_paths=[fixture])
        result = search_legislacion("concurso", norma="LC")

        assert result["resultados"]
        assert any(row["norma"] == "LC" for row in result["resultados"])

    def test_search_legislacion_returns_irpf_after_legalize_seed(self, db_url):
        import os
        from sqlalchemy import create_engine, text
        from legalize_es import run_sync

        os.environ["DATABASE_URL"] = db_url
        engine = create_engine(db_url, future=True)

        fixture = Path(__file__).resolve().parents[2] / "workers" / "tests" / "fixtures" / "legalize_es" / "irpf.md"

        with engine.begin() as conn:
            conn.execute(text("DELETE FROM version_articulo WHERE articulo_id IN (SELECT id FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'IRPF'))"))
            conn.execute(text("DELETE FROM articulo WHERE norma_id IN (SELECT id FROM norma WHERE codigo = 'IRPF')"))
            conn.execute(text("DELETE FROM norma WHERE codigo = 'IRPF'"))

        run_sync(engine, fixture_paths=[fixture])
        result = search_legislacion("renta", norma="LIRPF")

        assert result["resultados"]
        assert any(row["norma"] == "LIRPF" for row in result["resultados"])

    def test_search_legislacion_falls_back_when_documento_fragmento_missing(self, monkeypatch):
        db = Mock()
        db.bind.dialect.name = "postgresql"
        db.execute.side_effect = ProgrammingError("SELECT ... FROM documento_fragmento", {}, Exception("relation does not exist"))

        fallback_result = [{"norma": "LIVA", "numero": "91", "tipo": "articulo"}]
        fallback = Mock(return_value=fallback_result)
        monkeypatch.setattr("services.search._search_version_articulo_pg", fallback)

        result = _search_legislacion_pg(db, "tipo reducido IVA", None, None, None, None, None)

        assert result["resultados"] == fallback_result
        fallback.assert_called_once()
