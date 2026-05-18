from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from mcp_tools_perfil import obtener_obligaciones_perfil
from routers import modelos as modelos_router


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
                CREATE TABLE aeat_modelo (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    codigo TEXT NOT NULL,
                    nombre TEXT NOT NULL,
                    periodo TEXT,
                    impuesto TEXT,
                    url_info TEXT,
                    activo BOOLEAN
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE modelo_campana (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    modelo_id INTEGER NOT NULL,
                    campana TEXT,
                    activo BOOLEAN,
                    estado_publicacion TEXT,
                    fecha_publicacion_portal TEXT,
                    fecha_actualizacion_portal TEXT,
                    url_instrucciones TEXT,
                    url_normativa TEXT,
                    url_formato TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE modelo_recurso (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    campana_id INTEGER NOT NULL,
                    tipo_recurso TEXT,
                    formato TEXT,
                    url_recurso TEXT,
                    sha256_contenido TEXT,
                    fecha_publicacion_recurso TEXT,
                    first_seen_at TEXT,
                    last_seen_at TEXT,
                    activa BOOLEAN
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE modelo_casilla (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    campana_id INTEGER NOT NULL,
                    codigo TEXT,
                    etiqueta TEXT,
                    descripcion TEXT,
                    tipo_casilla TEXT,
                    pagina INTEGER,
                    orden INTEGER,
                    activa BOOLEAN
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE modelo_clave (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    campana_id INTEGER NOT NULL,
                    codigo TEXT,
                    etiqueta TEXT,
                    descripcion TEXT,
                    tipo_clave TEXT,
                    activa BOOLEAN,
                    tipo TEXT,
                    criterio_aplicacion TEXT,
                    exclusiones TEXT,
                    source_url TEXT,
                    source_hash TEXT,
                    capture_date TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE modelo_instruccion (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    campana_id INTEGER NOT NULL,
                    seccion TEXT,
                    titulo TEXT,
                    contenido TEXT,
                    orden INTEGER,
                    texto TEXT,
                    casilla_referencia TEXT,
                    source_url TEXT,
                    source_hash TEXT,
                    capture_date TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE modelo_regla_inclusion (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    campana_id INTEGER NOT NULL,
                    supuesto TEXT,
                    decision TEXT,
                    condicion TEXT,
                    umbral TEXT,
                    fuente_normativa TEXT,
                    source_url TEXT,
                    source_hash TEXT,
                    capture_date TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE modelo_campana_operativa (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    campana_id INTEGER NOT NULL,
                    categoria_obligado TEXT,
                    frecuencia_presentacion TEXT,
                    ventana_presentacion TEXT,
                    canal_presentacion TEXT,
                    obligados_resumen TEXT,
                    plazo_resumen TEXT,
                    presentacion_resumen TEXT,
                    norma_base TEXT,
                    nota TEXT,
                    origen_metadato TEXT,
                    estado_metadato TEXT,
                    completeness_estado TEXT
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
        modelo = conn.execute(
            text(
                """
                INSERT INTO aeat_modelo (codigo, nombre, periodo, impuesto, url_info, activo)
                VALUES ('289', 'Modelo 289. CRS/DAC2', 'anual', 'CRS', 'https://example.test/289', 1)
                """
            )
        )
        campana = conn.execute(
            text(
                """
                INSERT INTO modelo_campana (
                    modelo_id, campana, activo, estado_publicacion, url_instrucciones
                ) VALUES (:modelo_id, '2026', 1, 'publicado', 'https://example.test/289')
                """
            ),
            {"modelo_id": modelo.lastrowid},
        )
        conn.execute(
            text(
                """
                INSERT INTO modelo_instruccion (
                    campana_id, seccion, titulo, contenido, orden, texto, source_url
                ) VALUES (
                    :campana_id, 'cabecera', 'Cabecera', 'Campos de cabecera', 1,
                    'Campos de cabecera', 'https://example.test/289'
                )
                """
            ),
            {"campana_id": campana.lastrowid},
        )
        conn.execute(
            text(
                """
                INSERT INTO modelo_campana_operativa (
                    campana_id, estado_metadato, completeness_estado
                ) VALUES (:campana_id, 'oficial', 'parcial')
                """
            ),
            {"campana_id": campana.lastrowid},
        )
        conn.execute(
            text(
                """
                INSERT INTO obligacion_perfil (
                    perfil_codigo, obligacion_tipo, descripcion, periodicidad,
                    plazo_descripcion, modelo_aeat, norma_codigo,
                    articulo_referencia, fuente_secundaria, verified,
                    completeness, source_url
                ) VALUES (
                    'sociedad_valores', 'DECLARACION_INFORMATIVA',
                    'Modelo 289 - CRS/DAC2', 'anual',
                    'Del 1 al 31 de enero del año siguiente',
                    '289', 'LGT', 'DA 22.ª ap. 1',
                    'RD 1021/2015', 1, 'parcial',
                    'https://example.test/289'
                )
                """
            )
        )

    return sessionmaker(bind=engine, class_=Session, expire_on_commit=False, future=True)


def _client_with_db(session_factory: sessionmaker[Session], monkeypatch) -> TestClient:
    @contextmanager
    def session_scope() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    monkeypatch.setattr(modelos_router, "db_session", session_scope)
    app = FastAPI()
    app.include_router(modelos_router.router)
    return TestClient(app)


def test_modelo_289_response_separates_form_and_obligation_context(monkeypatch) -> None:
    client = _client_with_db(_make_session_factory(), monkeypatch)

    response = client.get("/v1/modelos/aeat/289")

    assert response.status_code == 200
    data = response.json()
    assert data["form_completeness"] == "parcial"
    assert "obligation_context" in data
    context = data["obligation_context"]
    assert context[0]["perfil_codigo"] == "sociedad_valores"
    assert context[0]["verified"] is True
    assert context[0]["norma_codigo"] == "LGT"
    assert context[0]["articulo_referencia"] == "DA 22.ª ap. 1"
    assert "Verificado contra LGT DA 22.ª ap. 1 (condicional)" == context[0][
        "obligation_evidence_notice"
    ]


def test_form_completeness_is_independent_from_obligation_verified(monkeypatch) -> None:
    client = _client_with_db(_make_session_factory(), monkeypatch)

    data = client.get("/v1/modelos/aeat/289").json()

    assert data["form_completeness"] == "parcial"
    assert "Evidencia limitada" in data["form_evidence_notice"]
    assert data["obligation_context"][0]["verified"] is True
    assert "evidence_limited" not in data["obligation_context"][0]["obligation_evidence_notice"]


def test_profile_obligation_289_uses_profile_evidence_notice() -> None:
    session_factory = _make_session_factory()
    with session_factory() as db:
        response = obtener_obligaciones_perfil(db, "sociedad_valores")

    item = next(ob for ob in response.obligaciones if ob.modelo_aeat == "289")
    assert item.verified is True
    assert "Verificado" in item.evidence_notice
    assert "evidence_limited" not in item.evidence_notice
