from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from mcp_tools_perfil import calendario_obligaciones_perfil
from routers import perfil as perfil_router


def _make_session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE perfil_entidad (
                    codigo TEXT PRIMARY KEY,
                    nombre TEXT NOT NULL,
                    supervisor TEXT NOT NULL,
                    regimen_primario TEXT,
                    activo BOOLEAN NOT NULL
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE obligacion_perfil (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    perfil_codigo TEXT NOT NULL,
                    obligacion_tipo TEXT NOT NULL,
                    descripcion TEXT NOT NULL,
                    periodicidad TEXT,
                    plazo_descripcion TEXT,
                    modelo_aeat TEXT,
                    norma_codigo TEXT,
                    articulo_referencia TEXT,
                    fuente_secundaria TEXT,
                    verified BOOLEAN NOT NULL,
                    completeness TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    notas TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO perfil_entidad (codigo, nombre, supervisor, regimen_primario, activo)
                VALUES ('sociedad_valores', 'Sociedad de Valores', 'CNMV', 'LIVMC', 1)
                """
            )
        )
        rows = [
            (
                "AUTOLIQUIDACION",
                "Modelo 111 - Retenciones trabajo",
                "mensual",
                "Del 1 al 20 del mes siguiente",
                "111",
            ),
            (
                "AUTOLIQUIDACION",
                "Modelo 115 - Retenciones arrendamientos",
                "trimestral",
                "Del 1 al 20 de enero, abril, julio y octubre",
                "115",
            ),
            (
                "AUTOLIQUIDACION",
                "Modelo 202 - Pago fraccionado IS",
                "trimestral",
                "Del 1 al 20 de abril, octubre y diciembre",
                "202",
            ),
            (
                "AUTOLIQUIDACION",
                "Modelo 303 - IVA autoliquidacion",
                "mensual",
                "mensual o trimestral segun volumen y condiciones AEAT",
                "303",
            ),
            (
                "DECLARACION_INFORMATIVA",
                "Modelo 999 - texto libre que menciona julio y trimestre",
                "ad_hoc",
                "Vencimiento condicionado al hecho imponible",
                "999",
            ),
        ]
        for tipo, descripcion, periodicidad, plazo, modelo in rows:
            conn.execute(
                text(
                    """
                    INSERT INTO obligacion_perfil (
                        perfil_codigo, obligacion_tipo, descripcion, periodicidad,
                        plazo_descripcion, modelo_aeat, norma_codigo,
                        articulo_referencia, fuente_secundaria, verified,
                        completeness, source_url
                    ) VALUES (
                        'sociedad_valores', :tipo, :descripcion, :periodicidad,
                        :plazo, :modelo, 'LIRPF', 'art. 101', NULL, 1,
                        'parcial', 'https://example.test/source'
                    )
                    """
                ),
                {
                    "tipo": tipo,
                    "descripcion": descripcion,
                    "periodicidad": periodicidad,
                    "plazo": plazo,
                    "modelo": modelo,
                },
            )

    return sessionmaker(bind=engine, class_=Session, expire_on_commit=False, future=True)


def _client_with_db(session_factory: sessionmaker[Session], monkeypatch) -> TestClient:
    @contextmanager
    def session_scope() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    monkeypatch.setattr(perfil_router, "db_session", session_scope)
    app = FastAPI()
    app.include_router(perfil_router.router)
    return TestClient(app)


def test_q3_calendar_endpoint_returns_due_models_and_excludes_202(monkeypatch) -> None:
    client = _client_with_db(_make_session_factory(), monkeypatch)

    response = client.get("/v1/perfil/sociedad_valores/obligaciones/calendario/2026-Q3")

    assert response.status_code == 200
    payload = response.json()
    modelos = {item["modelo_aeat"] for item in payload}
    assert {"111", "115", "303"} <= modelos
    assert "202" not in modelos
    assert "999" not in modelos


def test_q3_calendar_endpoint_returns_items_with_plazo(monkeypatch) -> None:
    client = _client_with_db(_make_session_factory(), monkeypatch)

    payload = client.get("/v1/perfil/sociedad_valores/obligaciones/calendario/2026-Q3").json()

    assert payload
    assert all(item["plazo_descripcion"] for item in payload)


def test_mcp_calendar_tool_accepts_quarter_and_returns_structured_result() -> None:
    session_factory = _make_session_factory()
    with session_factory() as db:
        response = calendario_obligaciones_perfil(db, "sociedad_valores", quarter="2026-Q3")

    modelos = {item.modelo_aeat for item in response.obligaciones}
    assert response.quarter == "Q3"
    assert {"111", "115", "303"} <= modelos
    assert "202" not in modelos


def test_quarter_calendar_uses_periodicidad_not_semantic_ranking() -> None:
    session_factory = _make_session_factory()
    with session_factory() as db:
        response = calendario_obligaciones_perfil(db, "sociedad_valores", quarter="Q3")

    modelos = {item.modelo_aeat for item in response.obligaciones}
    assert "999" not in modelos
