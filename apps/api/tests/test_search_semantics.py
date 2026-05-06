import os
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from conftest import engine
from services.search import _search_legislacion_pg, search_legislacion
from sqlalchemy import text


def _seed_source_pair(
    conn,
    *,
    boe_codigo: str,
    boe_id: str,
    autonomica_codigo: str,
    autonomica_id: str,
    numero: str,
    texto: str,
) -> None:
    conn.execute(
        text(
            "DELETE FROM version_articulo "
            "WHERE articulo_id IN (SELECT id FROM articulo WHERE numero = :numero)"
        ),
        {"numero": numero},
    )
    conn.execute(text("DELETE FROM articulo WHERE numero = :numero"), {"numero": numero})
    conn.execute(
        text("DELETE FROM norma WHERE codigo IN (:boe_codigo, :autonomica_codigo)"),
        {"boe_codigo": boe_codigo, "autonomica_codigo": autonomica_codigo},
    )
    conn.execute(
        text(
            """
            INSERT INTO norma (
                codigo, titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente,
                tipo_documento, ambito, estado_cobertura, vigente_desde
            )
            VALUES
                (:boe_codigo, 'Norma BOE semantica', :boe_id, :boe_url,
                 'es', 'boe', 'ley', 'tributario', 'ingestada', '2025-01-01'),
                (:autonomica_codigo, 'Norma autonomica semantica', :autonomica_id,
                 :autonomica_url, 'es', 'autonomica', 'ley', 'tributario',
                 'ingestada', '2025-01-01')
            """
        ),
        {
            "boe_codigo": boe_codigo,
            "boe_id": boe_id,
            "boe_url": f"https://example.invalid/{boe_id.lower()}",
            "autonomica_codigo": autonomica_codigo,
            "autonomica_id": autonomica_id,
            "autonomica_url": f"https://example.invalid/{autonomica_id.lower()}",
        },
    )
    conn.execute(
        text(
            """
            INSERT INTO articulo (norma_id, numero, titulo, tipo)
            SELECT id, :numero, 'Articulo aislamiento fuente', 'articulo'
            FROM norma WHERE codigo IN (:boe_codigo, :autonomica_codigo)
            """
        ),
        {"numero": numero, "boe_codigo": boe_codigo, "autonomica_codigo": autonomica_codigo},
    )
    conn.execute(
        text(
            """
            INSERT INTO version_articulo (
                articulo_id, texto, vigente_desde, vigente_hasta, boe_bloque_id
            )
            SELECT a.id, :texto, '2025-01-01', NULL, 'sem'
            FROM articulo a WHERE a.numero = :numero
            """
        ),
        {"texto": texto, "numero": numero},
    )


class TestSourceIsolation:
    @pytest.fixture
    def db_url(self):
        return os.environ.get("DATABASE_URL", "sqlite:///test_esdata.sqlite3")

    def test_boe_source_search_does_not_return_autonomica_rows(self, db_url):
        os.environ["DATABASE_URL"] = db_url
        with engine.begin() as conn:
            _seed_source_pair(
                conn,
                boe_codigo="SEMBOE",
                boe_id="SEM-BOE",
                autonomica_codigo="SEMAUT",
                autonomica_id="SEM-AUT",
                numero="SEM-BOE-AUT",
                texto="terminoaislado contenido comun para prueba de fuente",
            )

        result = search_legislacion("terminoaislado", fuente="boe")

        assert result["resultados"]
        assert all(row["norma"] != "SEMAUT" for row in result["resultados"])

    def test_autonomica_source_search_does_not_return_boe_rows(self, db_url):
        os.environ["DATABASE_URL"] = db_url
        with engine.begin() as conn:
            _seed_source_pair(
                conn,
                boe_codigo="SEMBOE2",
                boe_id="SEM-BOE2",
                autonomica_codigo="SEMAUT2",
                autonomica_id="SEM-AUT2",
                numero="SEM-AUT-BOE",
                texto="terminoautonomico contenido comun para prueba de fuente",
            )

        result = search_legislacion("terminoautonomico", fuente="autonomica")

        assert result["resultados"]
        assert all(row["norma"] != "SEMBOE2" for row in result["resultados"])


def test_chunk_fallback_preserves_restrictive_filters(monkeypatch):
    db = Mock()
    db.bind.dialect.name = "postgresql"
    db.execute.return_value.mappings.return_value = []
    fallback = Mock(return_value=[])
    monkeypatch.setattr("services.search._search_version_articulo_pg", fallback)

    _search_legislacion_pg(
        db,
        "unknown-term-that-has-no-chunks",
        norma="LIVA",
        fuente="boe",
        ambito="tributario",
        tipo="articulo",
        vigente_en="2026-05-06",
    )

    fallback.assert_called_once()
    assert fallback.call_args.args[2:7] == (
        "LIVA",
        "boe",
        "tributario",
        "articulo",
        "2026-05-06",
    )
