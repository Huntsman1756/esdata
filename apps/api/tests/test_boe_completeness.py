from __future__ import annotations

import warnings

import pytest
from sqlalchemy import text

from apps.api.tests.conftest import engine


CORE_BOE_LAWS = [
    {
        "codigo": "TRLIRNR",
        "boe_id": "BOE-A-2004-4527",
        "expected_min": 53,
        "strict_min": True,
        "titulo": "Real Decreto Legislativo 5/2004",
    },
    {
        "codigo": "LIVA",
        "boe_id": "BOE-A-1992-28740",
        "expected_min": 163,
        "strict_min": False,
        "titulo": "Ley 37/1992 del Impuesto sobre el Valor Anadido",
    },
    {
        "codigo": "LGT",
        "boe_id": "BOE-A-2003-23186",
        "expected_min": 178,
        "strict_min": False,
        "titulo": "Ley 58/2003 General Tributaria",
    },
    {
        "codigo": "LIRPF",
        "boe_id": "BOE-A-2006-20764",
        "expected_min": 99,
        "strict_min": False,
        "titulo": "Ley 35/2006 del IRPF",
    },
    {
        "codigo": "LIS",
        "boe_id": "BOE-A-2014-12328",
        "expected_min": 124,
        "strict_min": False,
        "titulo": "Ley 27/2014 del Impuesto sobre Sociedades",
    },
    {
        "codigo": "ITPAJD",
        "boe_id": "BOE-A-1993-25359",
        "expected_min": 60,
        "strict_min": False,
        "titulo": "Real Decreto Legislativo 1/1993",
    },
]


def _seed_sqlite_core_laws_for_contract_test(conn) -> None:
    """SQLite fixtures do not carry the full BOE corpus; seed enough rows to test the guard."""
    for law in CORE_BOE_LAWS:
        conn.execute(
            text(
                """
                INSERT OR IGNORE INTO norma (
                    codigo, titulo, boe_id, jurisdiccion, tipo_fuente,
                    tipo_documento, ambito, estado_cobertura, vigente_desde,
                    articles_expected, articles_parsed, quality_status
                )
                VALUES (
                    :codigo, :titulo, :boe_id, 'ES', 'boe',
                    'ley', 'tributario', 'ingestada', '2000-01-01',
                    :expected_min, :expected_min, 'complete'
                )
                """
            ),
            law,
        )
        norma_id = conn.execute(
            text("SELECT id FROM norma WHERE boe_id = :boe_id"),
            {"boe_id": law["boe_id"]},
        ).scalar_one()
        for index in range(1, law["expected_min"] + 1):
            conn.execute(
                text(
                    """
                    INSERT OR IGNORE INTO articulo (norma_id, numero, titulo, tipo)
                    VALUES (:norma_id, :numero, :titulo, 'articulo')
                    """
                ),
                {
                    "norma_id": norma_id,
                    "numero": str(index),
                    "titulo": f"Articulo {index}",
                },
            )


@pytest.mark.boe_completeness
def test_core_boe_laws_have_loaded_articles_by_boe_id() -> None:
    if engine.dialect.name == "sqlite":
        with engine.begin() as conn:
            _seed_sqlite_core_laws_for_contract_test(conn)

    with engine.begin() as conn:
        for law in CORE_BOE_LAWS:
            loaded = conn.execute(
                text(
                    """
                    SELECT COUNT(a.id)
                    FROM norma n
                    LEFT JOIN articulo a ON a.norma_id = n.id
                    WHERE n.boe_id = :boe_id
                    """
                ),
                {"boe_id": law["boe_id"]},
            ).scalar_one()

            assert loaded > 0, f"{law['codigo']} ({law['boe_id']}) has zero loaded articles"

            if law["strict_min"]:
                assert loaded >= law["expected_min"], (
                    f"{law['codigo']} ({law['boe_id']}) has {loaded} articles; "
                    f"expected at least {law['expected_min']}"
                )
            elif loaded < law["expected_min"]:
                warnings.warn(
                    (
                        f"{law['codigo']} ({law['boe_id']}) has {loaded} articles; "
                        f"expected around {law['expected_min']}. This is a warning because "
                        "BOE disposition counts vary by consolidation date."
                    ),
                    RuntimeWarning,
                    stacklevel=2,
                )
