from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from mcp_catalog import get_stdio_tool_definitions
from mcp_tools_aeat_catalogo import buscar_modelos_aeat_catalogo
from mcp_tools_perfil import obtener_obligaciones_perfil


def _make_db() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
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
                    activo BOOLEAN
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
                    etiqueta TEXT
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
                    titulo TEXT,
                    contenido TEXT
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
                    decision TEXT
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
        for codigo, nombre in (
            ("123", "Modelo 123. Retenciones capital mobiliario"),
            ("124", "Modelo 124. Rentas transmision activos"),
            ("202", "Modelo 202. Pago fraccionado IS"),
        ):
            result = conn.execute(
                text(
                    """
                    INSERT INTO aeat_modelo (codigo, nombre, periodo, impuesto, url_info, activo)
                    VALUES (:codigo, :nombre, 'trimestral', 'AEAT', :url, 1)
                    """
                ),
                {
                    "codigo": codigo,
                    "nombre": nombre,
                    "url": f"https://example.test/modelo-{codigo}",
                },
            )
            campana = conn.execute(
                text(
                    """
                    INSERT INTO modelo_campana (modelo_id, campana, activo)
                    VALUES (:modelo_id, '2026', 1)
                    """
                ),
                {"modelo_id": result.lastrowid},
            )
            conn.execute(
                text(
                    """
                    INSERT INTO modelo_instruccion (campana_id, titulo, contenido)
                    VALUES (:campana_id, 'Instrucciones', 'Texto oficial')
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
                    'sociedad_valores', 'AUTOLIQUIDACION',
                    'Modelo 202 - Pago fraccionado IS', 'trimestral',
                    'Del 1 al 20 de abril, octubre y diciembre',
                    '202', 'LIS', 'art. 40', NULL, 1, 'parcial',
                    'https://example.test/modelo-202'
                )
                """
            )
        )
    return Session(engine, future=True)


def test_profile_obligations_do_not_include_catalog_only_models() -> None:
    with _make_db() as db:
        response = obtener_obligaciones_perfil(db, "sociedad_valores", "FISCAL")

    modelos = {item.modelo_aeat for item in response.obligaciones}
    assert "202" in modelos
    assert "123" not in modelos
    assert "124" not in modelos


def test_catalog_search_returns_catalog_only_model_without_evidence_fields() -> None:
    with _make_db() as db:
        items = buscar_modelos_aeat_catalogo(db, codigo="123")

    assert len(items) == 1
    payload = items[0].model_dump()
    assert payload["codigo"] == "123"
    assert payload["instrucciones_count"] == 1
    assert payload["reglas_inclusion_count"] == 0
    assert "verified" not in payload
    assert "evidence_notice" not in payload
    assert "obligation_context" not in payload


def test_catalog_tool_is_registered_with_layer_separation_description() -> None:
    tools = {tool["name"]: tool for tool in get_stdio_tool_definitions()}

    assert "buscar_modelos_aeat_catalogo" in tools
    description = tools["buscar_modelos_aeat_catalogo"]["description"]
    assert "NO indica" in description
    assert "obtener_obligaciones_perfil" in description
