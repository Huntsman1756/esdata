import sys
from pathlib import Path

from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import regulatory_watch
from change_detection import ensure_source_revision_table


def test_insert_changes_uses_source_revision_idempotently():
    engine = create_engine("sqlite:///:memory:", future=True)
    regulatory_watch.engine = engine

    with engine.begin() as conn:
        ensure_source_revision_table(conn)

    change = regulatory_watch.RegulatoryChange(
        source="dgt",
        norma="DGT consultas vinculantes",
        change_type="amendment",
        description="Pagina actualizada: DGT consultas vinculantes",
    )

    assert regulatory_watch.insert_changes([change]) == 1
    assert regulatory_watch.insert_changes([change]) == 0

    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT worker_name, source_entity_tipo, count(*)
                FROM source_revision
                GROUP BY worker_name, source_entity_tipo
                """
            )
        ).fetchall()

    assert rows == [("reg-watch", "regulatory_change", 1)]


def test_liva_rate_detection_skips_missing_optional_iva_rates_table():
    engine = create_engine("sqlite:///:memory:", future=True)

    with engine.begin() as conn:
        changes = regulatory_watch._detect_rate_changes_in_boe(
            conn,
            "LIVA",
            "El tipo impositivo general sera del 21 por 100.",
            "2026-05-29T00:00:00+00:00",
        )

    assert changes == []
