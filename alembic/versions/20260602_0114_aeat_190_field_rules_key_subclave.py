"""add modelo 190 key/subkey field rules

Revision ID: 20260602_0114_aeat_190_field_rules_key_subclave
Revises: 20260602_0113_aeat_190_subclaves_percepcion
Create Date: 2026-06-02

Revision 0113 loaded the official 190 subclave catalogue. This revision adds
only a small, traceable first block of field-level instructions and inclusion
rules for positions 78 and 79-80. It does not change campaign assertion,
profile obligations, main keys, or subclave rows.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260602_0114_aeat_190_field_rules_key_subclave"
down_revision = "20260602_0113_aeat_190_subclaves_percepcion"
branch_labels = None
depends_on = None


CAPTURE_DATE = "2026-06-01"
DR_190_2025_URL = (
    "https://sede.agenciatributaria.gob.es/static_files/Sede/Disenyo_registro/"
    "DR_100_199/archivos_25/DISENOS_LOGICOS_190_2025.pdf"
)
DR_190_2025_HASH = "a7d1092f78620431812354e560a5146a3ae244e0aed69d9d58c353370ba0134d"
DR_190_2025_LENGTH = 1110488

RULE_PREFIX = "Modelo 190 campo"
INSTRUCTION_SECTIONS = (
    "campo_190_clave_pos_78",
    "campo_190_subclave_pos_79_80_obligatoria",
    "campo_190_subclave_pos_79_80_no_cumplimentar",
)

FIELD_RULES = [
    {
        "seccion": "campo_190_clave_pos_78",
        "titulo": "Clave de percepcion posicion 78 obligatoria",
        "contenido": (
            "En la posicion 78 del registro de tipo 2 debe consignarse la clave "
            "alfabetica de percepcion del Modelo 190."
        ),
        "casilla_referencia": "78",
        "supuesto": "Modelo 190 campo posicion 78 clave_percepcion_pos_78_obligatoria",
        "decision": "INCLUIR",
        "condicion": (
            "La posicion 78 identifica la clave de percepcion y debe "
            "cumplimentarse con una de las claves principales A-L."
        ),
        "fuente_normativa": "AEAT diseno logico Modelo 190 2025, posicion 78.",
        "orden": 40,
    },
    {
        "seccion": "campo_190_subclave_pos_79_80_obligatoria",
        "titulo": "Subclave posiciones 79-80 obligatoria",
        "contenido": (
            "Las posiciones 79-80 deben cumplimentarse con subclave cuando la "
            "clave de percepcion sea B, C, E, F, G, H, I, K y L."
        ),
        "casilla_referencia": "79-80",
        "supuesto": (
            "Modelo 190 campo posiciones 79-80 "
            "subclave_pos_79_80_obligatoria_b_c_e_f_g_h_i_k_l"
        ),
        "decision": "CONDICIONAL",
        "condicion": (
            "La subclave de las posiciones 79-80 es obligatoria solo para "
            "percepciones con clave B, C, E, F, G, H, I, K y L."
        ),
        "fuente_normativa": (
            "AEAT diseno logico Modelo 190 2025, posiciones 79-80."
        ),
        "orden": 50,
    },
    {
        "seccion": "campo_190_subclave_pos_79_80_no_cumplimentar",
        "titulo": "Subclave posiciones 79-80 no cumplimentar",
        "contenido": (
            "Las posiciones 79-80 no deben cumplimentarse cuando la clave de "
            "percepcion sea A, D y J."
        ),
        "casilla_referencia": "79-80",
        "supuesto": (
            "Modelo 190 campo posiciones 79-80 "
            "subclave_pos_79_80_no_cumplimentar_a_d_j"
        ),
        "decision": "EXCLUIR",
        "condicion": (
            "La subclave de las posiciones 79-80 no se cumplimenta para el "
            "resto de claves principales sin catalogo de subclaves en el "
            "diseno 2025: A, D y J."
        ),
        "fuente_normativa": (
            "AEAT diseno logico Modelo 190 2025, posiciones 79-80."
        ),
        "orden": 60,
    },
]


def _campaign_id(bind) -> int:
    campana_id = bind.execute(
        sa.text(
            """
            SELECT mc.id
            FROM modelo_campana mc
            JOIN aeat_modelo am ON am.id = mc.modelo_id
            WHERE am.codigo = '190'
              AND mc.campana = '2025'
              AND mc.activo = true
            """
        )
    ).scalar()
    if campana_id is None:
        raise RuntimeError("Active Modelo 190 campaign 2025 not found")
    return int(campana_id)


def _common(campana_id: int) -> dict[str, object]:
    return {
        "campana_id": campana_id,
        "source_url": DR_190_2025_URL,
        "source_hash": DR_190_2025_HASH,
        "capture_date": CAPTURE_DATE,
    }


def _delete_field_rules(bind, common: dict[str, object]) -> None:
    bind.execute(
        sa.text(
            """
            DELETE FROM modelo_regla_inclusion
            WHERE campana_id = :campana_id
              AND supuesto LIKE 'Modelo 190 campo%'
              AND source_url = :source_url
              AND source_hash = :source_hash
            """
        ),
        common,
    )
    bind.execute(
        sa.text(
            """
            DELETE FROM modelo_instruccion
            WHERE campana_id = :campana_id
              AND seccion IN (
                'campo_190_clave_pos_78',
                'campo_190_subclave_pos_79_80_obligatoria',
                'campo_190_subclave_pos_79_80_no_cumplimentar'
              )
              AND source_url = :source_url
              AND source_hash = :source_hash
            """
        ),
        common,
    )


def upgrade() -> None:
    bind = op.get_bind()
    campana_id = _campaign_id(bind)
    common = _common(campana_id)

    bind.execute(
        sa.text(
            """
            UPDATE modelo_recurso
            SET content_length = COALESCE(content_length, :content_length),
                metadata = COALESCE(metadata, '{}'::jsonb)
                    || jsonb_build_object(
                        'capture_date', CAST(:capture_date AS text),
                        'evidence_scope_field_rules', 'modelo_190_key_subclave_positions_78_80'
                    )
            WHERE campana_id = :campana_id
              AND tipo_recurso = 'diseno_registro'
              AND url_recurso = :source_url
              AND sha256_contenido = :source_hash
            """
        ),
        {**common, "content_length": DR_190_2025_LENGTH},
    )

    _delete_field_rules(bind, common)

    for rule in FIELD_RULES:
        bind.execute(
            sa.text(
                """
                INSERT INTO modelo_instruccion (
                    campana_id, seccion, titulo, contenido, orden, texto,
                    casilla_referencia, source_url, source_hash, capture_date
                )
                VALUES (
                    :campana_id, :seccion, :titulo, :contenido, :orden,
                    :contenido, :casilla_referencia,
                    :source_url, :source_hash, :capture_date
                )
                """
            ),
            {**common, **rule},
        )
        bind.execute(
            sa.text(
                """
                INSERT INTO modelo_regla_inclusion (
                    campana_id, supuesto, decision, condicion, fuente_normativa,
                    source_url, source_hash, capture_date
                )
                VALUES (
                    :campana_id, :supuesto, :decision, :condicion,
                    :fuente_normativa, :source_url, :source_hash, :capture_date
                )
                """
            ),
            {**common, **rule},
        )

    loaded = bind.execute(
        sa.text(
            """
            WITH field_instructions AS (
                SELECT seccion, casilla_referencia, source_url, source_hash, capture_date
                FROM modelo_instruccion
                WHERE campana_id = :campana_id
                  AND seccion IN (
                    'campo_190_clave_pos_78',
                    'campo_190_subclave_pos_79_80_obligatoria',
                    'campo_190_subclave_pos_79_80_no_cumplimentar'
                  )
            ),
            field_rules AS (
                SELECT supuesto, decision, condicion, source_url, source_hash, capture_date
                FROM modelo_regla_inclusion
                WHERE campana_id = :campana_id
                  AND (
                    supuesto LIKE '%clave_percepcion_pos_78_obligatoria%'
                    OR supuesto LIKE '%subclave_pos_79_80_obligatoria_b_c_e_f_g_h_i_k_l%'
                    OR supuesto LIKE '%subclave_pos_79_80_no_cumplimentar_a_d_j%'
                  )
            )
            SELECT
                (SELECT COUNT(*) = 3 FROM field_instructions)
                AND (SELECT COUNT(*) = 3 FROM field_rules)
                AND (
                    SELECT COUNT(*) = 3
                    FROM field_instructions
                    WHERE source_url = :source_url
                      AND source_hash = :source_hash
                      AND capture_date IS NOT NULL
                      AND casilla_referencia IN ('78', '79-80')
                )
                AND (
                    SELECT COUNT(*) = 3
                    FROM field_rules
                    WHERE source_url = :source_url
                      AND source_hash = :source_hash
                      AND capture_date IS NOT NULL
                      AND (
                        (supuesto LIKE '%clave_percepcion_pos_78_obligatoria%' AND decision = 'INCLUIR')
                        OR (
                            supuesto LIKE '%subclave_pos_79_80_obligatoria_b_c_e_f_g_h_i_k_l%'
                            AND decision = 'CONDICIONAL'
                            AND condicion LIKE '%posiciones 79-80%'
                            AND condicion LIKE '%B, C, E, F, G, H, I, K y L%'
                        )
                        OR (
                            supuesto LIKE '%subclave_pos_79_80_no_cumplimentar_a_d_j%'
                            AND decision = 'EXCLUIR'
                            AND condicion LIKE '%posiciones 79-80%'
                            AND condicion LIKE '%A, D y J%'
                        )
                      )
                )
            """
        ),
        common,
    ).scalar()
    if loaded is not True:
        raise RuntimeError("Modelo 190 field rule load did not satisfy COUNT(*) = 3")


def downgrade() -> None:
    bind = op.get_bind()
    campana_id = _campaign_id(bind)
    common = _common(campana_id)
    _delete_field_rules(bind, common)
    bind.execute(
        sa.text(
            """
            UPDATE modelo_recurso
            SET metadata = COALESCE(metadata, '{}'::jsonb) - 'evidence_scope_field_rules'
            WHERE campana_id = :campana_id
              AND tipo_recurso = 'diseno_registro'
              AND url_recurso = :source_url
              AND sha256_contenido = :source_hash
            """
        ),
        common,
    )
