from __future__ import annotations

import pytest
from mcp_catalog import get_stdio_tool_definitions
from mcp_tools_perfil import (
    PerfilNotFoundError,
    calendario_obligaciones_perfil,
    obtener_obligaciones_perfil,
)
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session


@pytest.fixture()
def perfil_db() -> Session:
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
                CREATE TABLE obligacion_fuente (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    obligacion_id INTEGER NOT NULL,
                    fuente_tipo TEXT NOT NULL,
                    codigo_referencia TEXT,
                    articulo TEXT,
                    descripcion TEXT,
                    source_url TEXT NOT NULL,
                    peso INTEGER
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

        rows = []
        for idx, modelo in enumerate(("111", "115", "193", "198", "200", "216", "296", "303"), start=1):
            rows.append(
                {
                    "tipo": "AUTOLIQUIDACION" if modelo in {"111", "115", "200", "216", "303"} else "DECLARACION_INFORMATIVA",
                    "desc": f"Modelo {modelo}",
                    "periodicidad": "anual" if modelo in {"193", "198", "200", "296"} else "mensual",
                    "modelo": modelo,
                    "norma": "LIS" if modelo == "200" else "LIRPF",
                    "articulo": "art. 124" if modelo == "200" else "art. 101",
                    "verified": 1,
                    "notas": f"Nota operativa Modelo {modelo}",
                }
            )
        for desc in (
            "Identificacion formal y verificacion del cliente",
            "Identificacion del titular real UBO",
            "Comunicacion de operaciones sospechosas al SEPBLAC",
            "Manual de prevencion PBC/FT",
        ):
            rows.append(
                {
                    "tipo": "DILIGENCIA_DEBIDA" if "Identificacion" in desc else "COMUNICACION_INDICIO",
                    "desc": desc,
                    "periodicidad": "continua",
                    "modelo": None,
                    "norma": "LEY10_2010",
                    "articulo": "art. 3",
                    "verified": 1,
                    "notas": f"Nota operativa {desc}",
                }
            )
        for desc in (
            "Informacion financiera periodica a CNMV",
            "MiFIR transaction reporting",
            "Politica de conflictos de interes",
            "Politica de mejor ejecucion",
        ):
            rows.append(
                {
                    "tipo": "REPORTING" if "Politica" not in desc else "CONTROL_INTERNO",
                    "desc": desc,
                    "periodicidad": "anual",
                    "modelo": None,
                    "norma": "LIVMC",
                    "articulo": "art. 228",
                    "verified": 0 if "MiFIR" in desc else 1,
                    "notas": f"Nota operativa {desc}",
                }
            )

        for row in rows:
            result = conn.execute(
                text(
                    """
                    INSERT INTO obligacion_perfil (
                        perfil_codigo, obligacion_tipo, descripcion, periodicidad,
                        modelo_aeat, norma_codigo, articulo_referencia,
                        fuente_secundaria, verified, completeness, source_url, notas
                    ) VALUES (
                        'sociedad_valores', :tipo, :desc, :periodicidad,
                        :modelo, :norma, :articulo, NULL, :verified, 'completa',
                        'https://example.test/source', :notas
                    )
                    """
                ),
                row,
            )
            obligation_id = result.lastrowid
            conn.execute(
                text(
                    """
                    INSERT INTO obligacion_fuente (
                        obligacion_id, fuente_tipo, codigo_referencia,
                        articulo, descripcion, source_url, peso
                    ) VALUES (
                        :id, 'norma_primaria', :norma, :articulo,
                        :desc, 'https://example.test/source', 1
                    )
                    """
                ),
                {**row, "id": obligation_id},
            )

    with Session(engine, future=True) as session:
        yield session


def test_obtener_obligaciones_perfil_returns_profile_obligations(perfil_db: Session) -> None:
    response = obtener_obligaciones_perfil(perfil_db, "sociedad_valores")

    assert response.total >= 15
    assert response.perfil.codigo == "sociedad_valores"
    assert any(item.notas for item in response.obligaciones)


def test_obtener_obligaciones_perfil_pbc_returns_only_pbc_types(perfil_db: Session) -> None:
    response = obtener_obligaciones_perfil(perfil_db, "sociedad_valores", "PBC_FT")

    assert response.total >= 3
    assert {item.obligacion_tipo for item in response.obligaciones} <= {
        "DILIGENCIA_DEBIDA",
        "COMUNICACION_INDICIO",
        "CONTROL_INTERNO",
        "FORMACION",
        "REGISTRO",
    }
    assert {item.norma_codigo for item in response.obligaciones} == {"LEY10_2010"}


def test_obtener_obligaciones_perfil_fiscal_has_model_or_norma(perfil_db: Session) -> None:
    response = obtener_obligaciones_perfil(perfil_db, "sociedad_valores", "FISCAL")

    assert response.total >= 8
    assert all(item.modelo_aeat or item.norma_codigo for item in response.obligaciones)


def test_obtener_obligaciones_perfil_fiscal_fails_closed_without_hash(
    perfil_db: Session,
) -> None:
    response = obtener_obligaciones_perfil(perfil_db, "sociedad_valores", "FISCAL")

    modelo_193 = next(item for item in response.obligaciones if item.modelo_aeat == "193")
    assert modelo_193.verified is False
    assert modelo_193.completeness == "parcial"
    assert modelo_193.evidence_notice == (
        "evidence_limited: falta hash o fecha de captura de la fuente"
    )
    assert response.safe_to_answer is False


def test_obtener_obligaciones_perfil_never_returns_missing_source_url(perfil_db: Session) -> None:
    response = obtener_obligaciones_perfil(perfil_db, "sociedad_valores")

    assert all(item.source_url for item in response.obligaciones)


def test_calendario_groups_obligations(perfil_db: Session) -> None:
    response = calendario_obligaciones_perfil(perfil_db, "sociedad_valores")

    assert response.calendario["anual"]
    assert response.calendario["mensual"]


def test_unknown_profile_raises_404_equivalent(perfil_db: Session) -> None:
    with pytest.raises(PerfilNotFoundError):
        obtener_obligaciones_perfil(perfil_db, "unknown_profile")


def test_profile_tools_are_registered_with_descriptions() -> None:
    tools = {tool["name"]: tool for tool in get_stdio_tool_definitions()}

    for name in (
        "listar_perfiles_entidad",
        "obtener_obligaciones_perfil",
        "calendario_obligaciones_perfil",
    ):
        assert name in tools
        assert len(tools[name]["description"]) > 50
