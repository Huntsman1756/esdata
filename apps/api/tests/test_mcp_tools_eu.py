from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from mcp_catalog import get_stdio_tool_definitions
from mcp_tools_eu import buscar_norma_eu


@pytest.fixture()
def eu_norms_db() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE norma (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    codigo TEXT NOT NULL UNIQUE,
                    titulo TEXT NOT NULL,
                    celex TEXT,
                    tipo_norma TEXT,
                    publicacion_doue DATE,
                    url_eurlex TEXT,
                    vigente BOOLEAN,
                    derogada_por TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO norma (
                    codigo, titulo, celex, tipo_norma,
                    publicacion_doue, url_eurlex, vigente, derogada_por
                ) VALUES
                (
                    '32014R0600',
                    'Reglamento (UE) n. 600/2014 relativo a los mercados de instrumentos financieros (MiFIR)',
                    '32014R0600',
                    'reglamento_ue',
                    '2014-06-12',
                    'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32014R0600',
                    1,
                    NULL
                ),
                (
                    '32022R2554',
                    'Reglamento (UE) 2022/2554 sobre resiliencia operativa digital (DORA)',
                    '32022R2554',
                    'reglamento_ue',
                    '2022-12-27',
                    'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32022R2554',
                    1,
                    NULL
                ),
                (
                    '32012R0648',
                    'Reglamento (UE) n. 648/2012 EMIR',
                    '32012R0648',
                    'reglamento_ue',
                    '2012-07-04',
                    'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32012R0648',
                    1,
                    NULL
                ),
                (
                    '32019R0834',
                    'Reglamento (UE) 2019/834 EMIR Refit',
                    '32019R0834',
                    'reglamento_ue',
                    '2019-05-28',
                    'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32019R0834',
                    1,
                    NULL
                ),
                (
                    '32017R0590',
                    'Reglamento Delegado (UE) 2017/590 RTS 22 transaction reporting',
                    '32017R0590',
                    'rts',
                    '2017-03-31',
                    'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32017R0590',
                    1,
                    NULL
                ),
                (
                    'LIVMC',
                    'Ley del Mercado de Valores',
                    NULL,
                    NULL,
                    NULL,
                    NULL,
                    1,
                    NULL
                )
                """
            )
        )

    with Session(engine, future=True) as session:
        yield session


def test_buscar_norma_eu_mifir_returns_celex(eu_norms_db: Session) -> None:
    rows = buscar_norma_eu(eu_norms_db, "MiFIR")

    assert any(row.celex == "32014R0600" for row in rows)


def test_buscar_norma_eu_dora_returns_celex(eu_norms_db: Session) -> None:
    rows = buscar_norma_eu(eu_norms_db, "DORA")

    assert any(row.celex == "32022R2554" for row in rows)


def test_buscar_norma_eu_emir_returns_refit_and_original(eu_norms_db: Session) -> None:
    rows = buscar_norma_eu(eu_norms_db, "EMIR")

    assert {row.celex for row in rows} >= {"32012R0648", "32019R0834"}


def test_buscar_norma_eu_results_have_eurlex_url(eu_norms_db: Session) -> None:
    rows = buscar_norma_eu(eu_norms_db, "MiFIR")

    assert rows
    assert all(row.url_eurlex for row in rows)


def test_buscar_norma_eu_tipo_norma_filter(eu_norms_db: Session) -> None:
    rows = buscar_norma_eu(eu_norms_db, "", "rts")

    assert rows
    assert {row.tipo_norma for row in rows} == {"rts"}


def test_buscar_norma_eu_tool_description_is_registered() -> None:
    tools = {tool["name"]: tool for tool in get_stdio_tool_definitions()}

    assert "buscar_norma_eu" in tools
    assert len(tools["buscar_norma_eu"]["description"]) > 50
