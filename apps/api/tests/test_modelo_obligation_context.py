from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

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
                    source_url TEXT NOT NULL
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
                    url_instrucciones TEXT,
                    url_normativa TEXT,
                    url_formato TEXT,
                    fecha_publicacion_portal TEXT,
                    fecha_actualizacion_portal TEXT
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
                CREATE TABLE modelo_casilla (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    campana_id INTEGER NOT NULL,
                    codigo TEXT,
                    etiqueta TEXT,
                    descripcion TEXT,
                    tipo_casilla TEXT,
                    pagina INTEGER,
                    orden INTEGER,
                    activa BOOLEAN DEFAULT 1
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
                    tipo TEXT,
                    criterio_aplicacion TEXT,
                    exclusiones TEXT,
                    source_url TEXT,
                    source_hash TEXT,
                    capture_date TEXT,
                    activa BOOLEAN DEFAULT 1
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
                    activa BOOLEAN DEFAULT 1
                )
                """
            )
        )
        for codigo in ("289", "290"):
            model = conn.execute(
                text(
                    """
                    INSERT INTO aeat_modelo (codigo, nombre, periodo, impuesto, url_info, activo)
                    VALUES (:codigo, :nombre, 'anual', 'Informativas', :url_info, 1)
                    """
                ),
                {
                    "codigo": codigo,
                    "nombre": f"Modelo {codigo}",
                    "url_info": f"https://example.test/modelo-{codigo}",
                },
            )
            conn.execute(
                text(
                    """
                    INSERT INTO modelo_campana (
                        modelo_id, campana, activo, estado_publicacion,
                        url_instrucciones, url_normativa, url_formato,
                        fecha_publicacion_portal, fecha_actualizacion_portal
                    )
                    VALUES (
                        :modelo_id, '2025', 1, 'publicada',
                        :url_info, :url_info, NULL, NULL, NULL
                    )
                    """
                ),
                {"modelo_id": model.lastrowid, "url_info": f"https://example.test/modelo-{codigo}"},
            )
            campana_id = model.lastrowid
            actual_campana_id = conn.execute(
                text("SELECT id FROM modelo_campana WHERE modelo_id = :modelo_id"),
                {"modelo_id": model.lastrowid},
            ).scalar_one()
            conn.execute(
                text(
                    """
                    INSERT INTO modelo_campana_operativa (
                        campana_id, estado_metadato, completeness_estado
                    )
                    VALUES (:campana_id, 'oficial', 'parcial')
                    """
                ),
                {"campana_id": actual_campana_id},
            )
            conn.execute(
                text(
                    """
                    INSERT INTO modelo_casilla (
                        campana_id, codigo, etiqueta, descripcion, tipo_casilla, pagina, orden, activa
                    )
                    VALUES (:campana_id, '001', 'Campo 1', 'Campo oficial', 'texto', 1, 1, 1)
                    """
                ),
                {"campana_id": actual_campana_id},
            )
            conn.execute(
                text(
                    """
                    INSERT INTO modelo_instruccion (
                        campana_id, seccion, titulo, contenido, orden, texto, source_url
                    )
                    VALUES (
                        :campana_id, 'general', 'Instrucciones', 'Contenido oficial',
                        1, 'Contenido oficial', :source_url
                    )
                    """
                ),
                {
                    "campana_id": actual_campana_id,
                    "source_url": f"https://example.test/modelo-{codigo}",
                },
            )

        for perfil in ("sociedad_valores", "agencia_valores", "entidad_credito"):
            conn.execute(
                text(
                    """
                    INSERT INTO obligacion_perfil (
                        perfil_codigo, obligacion_tipo, descripcion, periodicidad,
                        plazo_descripcion, modelo_aeat, norma_codigo,
                        articulo_referencia, fuente_secundaria, verified,
                        completeness, source_url
                    ) VALUES (
                        :perfil, 'DECLARACION_INFORMATIVA',
                        'Modelo 289 - CRS/DAC2', 'anual',
                        'Del 1 al 31 de enero del año siguiente',
                        '289', 'LGT', 'DA 22.ª ap. 1',
                        'RD 1021/2015', 1, 'parcial',
                        'https://example.test/289'
                    )
                    """
                ),
                {"perfil": perfil},
            )
        for perfil in ("sociedad_valores", "agencia_valores", "entidad_credito"):
            conn.execute(
                text(
                    """
                    INSERT INTO obligacion_perfil (
                        perfil_codigo, obligacion_tipo, descripcion, periodicidad,
                        plazo_descripcion, modelo_aeat, norma_codigo,
                        articulo_referencia, fuente_secundaria, verified,
                        completeness, source_url
                    ) VALUES (
                        :perfil, 'DECLARACION_INFORMATIVA',
                        'Modelo 290 - FATCA', 'anual',
                        'Declaracion anual FATCA',
                        '290', 'LGT', 'DA 22.ª ap. 8',
                        'Acuerdo FATCA España-EE.UU.', 1, 'parcial',
                        'https://www.boe.es/buscar/act.php?id=BOE-A-2014-6854'
                    )
                    """
                ),
                {"perfil": perfil},
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


def test_modelo_289_has_obligation_context_with_three_profiles(monkeypatch) -> None:
    client = _client_with_db(_make_session_factory(), monkeypatch)

    data = client.get("/v1/modelos/aeat/289").json()

    assert len(data["obligation_context"]) >= 3


def test_each_obligation_context_entry_has_verified_field(monkeypatch) -> None:
    client = _client_with_db(_make_session_factory(), monkeypatch)

    data = client.get("/v1/modelos/aeat/289").json()

    assert all("verified" in entry for entry in data["obligation_context"])


def test_form_completeness_is_independent_of_obligation_verified(monkeypatch) -> None:
    client = _client_with_db(_make_session_factory(), monkeypatch)

    data = client.get("/v1/modelos/aeat/289").json()

    assert data["form_completeness"] == "parcial"
    assert all(entry["verified"] is True for entry in data["obligation_context"])


def test_modelo_290_context_sources_do_not_point_to_lis(monkeypatch) -> None:
    client = _client_with_db(_make_session_factory(), monkeypatch)

    data = client.get("/v1/modelos/aeat/290").json()

    assert data["obligation_context"]
    assert all(
        "BOE-A-2014-12328" not in entry["source_url"]
        for entry in data["obligation_context"]
    )
