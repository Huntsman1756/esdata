from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from routers import norma as norma_router
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


@pytest.fixture()
def norma_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE norma (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    codigo TEXT NOT NULL UNIQUE,
                    titulo TEXT NOT NULL,
                    boe_id TEXT,
                    eli_uri TEXT,
                    jurisdiccion TEXT,
                    tipo_fuente TEXT,
                    tipo_documento TEXT,
                    ambito TEXT,
                    estado_cobertura TEXT,
                    vigente_desde DATE,
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
                CREATE TABLE obligacion_perfil (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    perfil_codigo TEXT,
                    obligacion_tipo TEXT,
                    descripcion TEXT,
                    periodicidad TEXT,
                    norma_codigo TEXT,
                    articulo_referencia TEXT,
                    verified BOOLEAN,
                    completeness TEXT,
                    source_url TEXT,
                    source_hash TEXT,
                    capture_date TEXT,
                    notas TEXT
                )
                """
            )
        )

        norms = [
            ("32014R0600", "MiFIR", "reglamento_ue", "2014-06-12"),
            ("32022R2554", "DORA", "reglamento_ue", "2022-12-27"),
            ("32012R0648", "EMIR", "reglamento_ue", "2012-07-04"),
            ("32019R0834", "EMIR Refit", "reglamento_ue", "2019-05-28"),
            ("32015R2365", "SFTR", "reglamento_ue", "2015-12-23"),
            ("32013R0575", "CRR", "reglamento_ue", "2013-06-27"),
            ("32009L0065", "UCITS IV", "directiva_ue", "2009-11-17"),
            ("32011L0061", "AIFMD", "directiva_ue", "2011-07-01"),
            ("32013R0231", "AIFMR", "reglamento_ue", "2013-03-22"),
            ("32017R0590", "RTS 22", "rts", "2017-03-31"),
            ("32017R0565", "MiFID II delegated regulation", "rts", "2017-03-31"),
        ]
        for codigo, titulo, tipo_norma, pub in norms:
            conn.execute(
                text(
                    """
                    INSERT INTO norma (
                        codigo, titulo, boe_id, eli_uri, jurisdiccion,
                        tipo_fuente, tipo_documento, ambito, estado_cobertura,
                        vigente_desde, celex, tipo_norma, publicacion_doue,
                        url_eurlex, vigente, derogada_por
                    ) VALUES (
                        :codigo, :titulo, 'EUR-CELEX-' || :codigo,
                        'http://data.europa.eu/eli/test', 'ue', 'eurlex',
                        :tipo_norma, 'mercados_financieros_ue',
                        'metadata_official', :pub, :codigo, :tipo_norma,
                        :pub,
                        'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:' || :codigo,
                        1, NULL
                    )
                    """
                ),
                {"codigo": codigo, "titulo": titulo, "tipo_norma": tipo_norma, "pub": pub},
            )
        conn.execute(
            text(
                """
                INSERT INTO obligacion_perfil (
                    perfil_codigo, obligacion_tipo, descripcion, periodicidad,
                    norma_codigo, articulo_referencia, verified, completeness, source_url
                ) VALUES (
                    'sociedad_valores', 'REPORTING', 'MiFIR transaction reporting',
                    'diaria', '32014R0600', 'art. 26', 1, 'completa',
                    'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32014R0600'
                )
                """
            )
        )

    session = Session(engine, future=True)

    @contextmanager
    def session_scope() -> Iterator[Session]:
        yield session

    monkeypatch.setattr(norma_router, "db_session", session_scope)
    app = FastAPI()
    app.include_router(norma_router.router)
    return TestClient(app)


def test_get_norma_eu_returns_loaded_eu_norms(norma_client: TestClient) -> None:
    response = norma_client.get("/v1/norma/eu")

    assert response.status_code == 200
    assert len(response.json()) >= 10


def test_get_norma_eu_filters_rts(norma_client: TestClient) -> None:
    response = norma_client.get("/v1/norma/eu?tipo_norma=rts")

    assert response.status_code == 200
    assert response.json()
    assert {item["tipo_norma"] for item in response.json()} == {"rts"}


def test_get_norma_detail_returns_mifir(norma_client: TestClient) -> None:
    response = norma_client.get("/v1/norma/32014R0600")

    assert response.status_code == 200
    assert response.json()["celex"] == "32014R0600"
    assert "MiFIR" in response.json()["titulo"]


def test_get_norma_detail_includes_referenced_obligations(norma_client: TestClient) -> None:
    response = norma_client.get("/v1/norma/32014R0600")

    assert response.status_code == 200
    assert response.json()["obligaciones_referenciadas"]


def test_get_norma_detail_fails_closed_for_referenced_obligation_without_hash(
    norma_client: TestClient,
) -> None:
    response = norma_client.get("/v1/norma/32014R0600")

    assert response.status_code == 200
    obligation = response.json()["obligaciones_referenciadas"][0]
    assert obligation["verified"] is False
    assert obligation["completeness"] == "parcial"
    assert obligation["source_hash"] is None
    assert obligation["capture_date"] is None
    assert obligation["review_required"] is True


def test_get_norma_unknown_returns_404(norma_client: TestClient) -> None:
    response = norma_client.get("/v1/norma/unknown")

    assert response.status_code == 404
