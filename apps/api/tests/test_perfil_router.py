from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from routers import perfil as perfil_router


@pytest.fixture()
def perfil_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE perfil_entidad (codigo TEXT PRIMARY KEY, nombre TEXT, supervisor TEXT, regimen_primario TEXT, activo BOOLEAN)"))
        conn.execute(
            text(
                """
                CREATE TABLE obligacion_perfil (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    perfil_codigo TEXT,
                    obligacion_tipo TEXT,
                    descripcion TEXT,
                    periodicidad TEXT,
                    plazo_descripcion TEXT,
                    modelo_aeat TEXT,
                    norma_codigo TEXT,
                    articulo_referencia TEXT,
                    fuente_secundaria TEXT,
                    verified BOOLEAN,
                    completeness TEXT,
                    source_url TEXT
                )
                """
            )
        )
        conn.execute(text("CREATE TABLE obligacion_fuente (id INTEGER PRIMARY KEY AUTOINCREMENT, obligacion_id INTEGER, fuente_tipo TEXT, codigo_referencia TEXT, articulo TEXT, descripcion TEXT, source_url TEXT, peso INTEGER)"))
        conn.execute(text("INSERT INTO perfil_entidad VALUES ('sociedad_valores','Sociedad de Valores','CNMV','LIVMC',1)"))
        conn.execute(text("INSERT INTO perfil_entidad VALUES ('agencia_valores','Agencia de Valores','CNMV','LIVMC',1)"))
        conn.execute(text("INSERT INTO perfil_entidad VALUES ('sgiic','Sociedad Gestora IIC','CNMV','RD_1082_2012',1)"))
        for idx in range(16):
            tipo = "DILIGENCIA_DEBIDA" if idx < 4 else "AUTOLIQUIDACION" if idx < 10 else "REPORTING"
            norma = "LEY10_2010" if idx < 4 else "LIRPF" if idx < 10 else "LIVMC"
            periodicidad = "continua" if idx < 4 else "anual"
            conn.execute(
                text(
                    """
                    INSERT INTO obligacion_perfil (
                        perfil_codigo, obligacion_tipo, descripcion, periodicidad,
                        plazo_descripcion, modelo_aeat, norma_codigo, articulo_referencia,
                        fuente_secundaria, verified, completeness, source_url
                    ) VALUES (
                        'sociedad_valores', :tipo, :desc, :periodicidad,
                        NULL, :modelo, :norma, 'art. 1', NULL, 1, 'completa',
                        'https://example.test/source'
                    )
                    """
                ),
                {
                    "tipo": tipo,
                    "desc": f"Obligacion {idx}",
                    "periodicidad": periodicidad,
                    "modelo": "200" if tipo == "AUTOLIQUIDACION" else None,
                    "norma": norma,
                },
            )

    session = Session(engine, future=True)

    @contextmanager
    def session_scope() -> Iterator[Session]:
        yield session

    monkeypatch.setattr(perfil_router, "db_session", session_scope)
    app = FastAPI()
    app.include_router(perfil_router.router)
    return TestClient(app)


def test_list_perfil_returns_profiles(perfil_client: TestClient) -> None:
    response = perfil_client.get("/v1/perfil")

    assert response.status_code == 200
    assert len(response.json()) >= 3


def test_get_sociedad_valores_returns_profile(perfil_client: TestClient) -> None:
    response = perfil_client.get("/v1/perfil/sociedad_valores")

    assert response.status_code == 200
    data = response.json()
    assert data["codigo"] == "sociedad_valores"
    assert data["obligaciones_por_tipo"]["DILIGENCIA_DEBIDA"] == 4


def test_obligaciones_endpoint_returns_response(perfil_client: TestClient) -> None:
    response = perfil_client.get("/v1/perfil/sociedad_valores/obligaciones")

    assert response.status_code == 200
    assert response.json()["total"] >= 15


def test_obligaciones_endpoint_filters_pbc(perfil_client: TestClient) -> None:
    response = perfil_client.get("/v1/perfil/sociedad_valores/obligaciones?dominio=PBC_FT")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 4
    assert {item["norma_codigo"] for item in data["obligaciones"]} == {"LEY10_2010"}


def test_calendario_endpoint_groups_obligations(perfil_client: TestClient) -> None:
    response = perfil_client.get("/v1/perfil/sociedad_valores/obligaciones/calendario")

    assert response.status_code == 200
    data = response.json()["calendario"]
    assert data["anual"]
    assert data["continua"]


def test_unknown_profile_returns_404(perfil_client: TestClient) -> None:
    response = perfil_client.get("/v1/perfil/unknown_profile")

    assert response.status_code == 404
