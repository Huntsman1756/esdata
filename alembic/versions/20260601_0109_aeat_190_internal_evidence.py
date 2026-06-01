"""add internal AEAT evidence for modelo 190 keys and rules

Revision ID: 20260601_0109_aeat_190_internal_evidence
Revises: 20260601_0108_aeat_190_campaign_evidence
Create Date: 2026-06-01

Modelo 190 campaign assertion was closed separately in 0108. This revision
only fixes the internal content audit for the active 2025 campaign: the four
legacy A-D perception keys are replaced with official AEAT design evidence,
and sourced instructions/rules are added for those keys. It does not change
campaign promotion or profile applicability.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260601_0109_aeat_190_internal_evidence"
down_revision = "20260601_0108_aeat_190_campaign_evidence"
branch_labels = None
depends_on = None


CAPTURE_DATE = "2026-06-01"
DR_190_2025_URL = (
    "https://sede.agenciatributaria.gob.es/static_files/Sede/Disenyo_registro/"
    "DR_100_199/archivos_25/DISENOS_LOGICOS_190_2025.pdf"
)
DR_190_2025_HASH = "a7d1092f78620431812354e560a5146a3ae244e0aed69d9d58c353370ba0134d"
DR_190_2025_LENGTH = 1110488

KEYS = [
    {
        "codigo": "A",
        "etiqueta": "Rendimientos del trabajo",
        "descripcion": "Rendimientos del trabajo: Empleados por cuenta ajena en general.",
        "criterio": (
            "Usar para percepciones dinerarias o en especie satisfechas como "
            "rendimientos del trabajo cuando aplica el procedimiento general "
            "del articulo 82 del Reglamento del Impuesto y no proceden las "
            "claves B, C o D."
        ),
    },
    {
        "codigo": "B",
        "etiqueta": "Pensionistas y haberes pasivos",
        "descripcion": (
            "Rendimientos del trabajo: Pensionistas y perceptores de haberes "
            "pasivos y demas prestaciones del articulo 17.2.a) LIRPF."
        ),
        "criterio": (
            "Usar para percepciones no exentas correspondientes a pensiones, "
            "haberes pasivos y demas prestaciones del articulo 17.2.a) LIRPF; "
            "requiere subclave."
        ),
    },
    {
        "codigo": "C",
        "etiqueta": "Prestaciones o subsidios por desempleo",
        "descripcion": "Rendimientos del trabajo: Prestaciones o subsidios por desempleo.",
        "criterio": (
            "Usar para prestaciones o subsidios por desempleo, excepto las "
            "prestaciones satisfechas en la modalidad de pago unico; requiere "
            "subclave."
        ),
    },
    {
        "codigo": "D",
        "etiqueta": "Prestaciones por desempleo pago unico",
        "descripcion": (
            "Rendimientos del trabajo: Prestaciones por desempleo abonadas en "
            "la modalidad de pago único."
        ),
        "criterio": (
            "Clave suprimida desde 2013 para nuevas prestaciones de pago unico; "
            "se usa solo para prestaciones reintegradas en el ejercicio que "
            "fueron indebidamente percibidas en ejercicios anteriores a 2013."
        ),
    },
]

INSTRUCTIONS = [
    {
        "seccion": "diseno_registro_2025",
        "titulo": "Diseno de registro Modelo 190 2025",
        "contenido": (
            "El diseno logico AEAT del Modelo 190 para el ejercicio 2025 "
            "define la declaracion informativa anual de retenciones e ingresos "
            "a cuenta sobre rendimientos del trabajo, actividades economicas, "
            "premios, determinadas ganancias patrimoniales e imputaciones de "
            "rentas."
        ),
        "orden": 10,
        "casilla": None,
    },
    {
        "seccion": "clave_percepcion",
        "titulo": "Clave de percepcion",
        "contenido": (
            "La posicion 78 del registro de tipo 2 contiene la clave alfabetica "
            "de percepcion. Para las claves A-D, el propio diseno distingue "
            "empleados por cuenta ajena, pensionistas y haberes pasivos, "
            "prestaciones o subsidios por desempleo y prestaciones por "
            "desempleo en pago unico."
        ),
        "orden": 20,
        "casilla": "78",
    },
    {
        "seccion": "subclave",
        "titulo": "Subclave",
        "contenido": (
            "Las posiciones 79-80 contienen la subclave. En el diseno 2025 se "
            "exige subclave para las claves B y C, mientras que en claves "
            "distintas de las enumeradas por el diseno no se cumplimenta este "
            "campo."
        ),
        "orden": 30,
        "casilla": "79-80",
    },
]

RULES = [
    {
        "supuesto": "Modelo 190 clave A - rendimientos del trabajo general",
        "condicion": (
            "Percepciones dinerarias o en especie satisfechas como rendimientos "
            "del trabajo con procedimiento general del articulo 82 RIRPF y no "
            "incluidas especificamente en B, C o D."
        ),
    },
    {
        "supuesto": "Modelo 190 clave B - pensionistas y haberes pasivos",
        "condicion": (
            "Pensiones, haberes pasivos y demas prestaciones no exentas del "
            "articulo 17.2.a) LIRPF; debe consignarse la subclave aplicable."
        ),
    },
    {
        "supuesto": "Modelo 190 clave C - prestaciones o subsidios por desempleo",
        "condicion": (
            "Prestaciones o subsidios por desempleo, salvo las satisfechas en "
            "modalidad de pago unico; debe consignarse la subclave aplicable."
        ),
    },
    {
        "supuesto": "Modelo 190 clave D - reintegros de pago unico anteriores a 2013",
        "condicion": (
            "Prestaciones por desempleo en pago unico reintegradas en el "
            "ejercicio por haber sido indebidamente percibidas en ejercicios "
            "anteriores a 2013."
        ),
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


def upgrade() -> None:
    bind = op.get_bind()
    campana_id = _campaign_id(bind)
    common = {
        "campana_id": campana_id,
        "source_url": DR_190_2025_URL,
        "source_hash": DR_190_2025_HASH,
        "capture_date": CAPTURE_DATE,
    }

    bind.execute(
        sa.text(
            """
            UPDATE modelo_recurso
            SET content_length = COALESCE(content_length, :content_length),
                metadata = COALESCE(metadata, '{}'::jsonb)
                    || jsonb_build_object(
                        'capture_date', :capture_date,
                        'evidence_scope', 'modelo_190_internal_keys_rules'
                    )
            WHERE campana_id = :campana_id
              AND tipo_recurso = 'diseno_registro'
              AND url_recurso = :source_url
              AND sha256_contenido = :source_hash
            """
        ),
        {**common, "content_length": DR_190_2025_LENGTH},
    )

    bind.execute(sa.text("DELETE FROM modelo_clave WHERE campana_id = :campana_id"), common)
    bind.execute(sa.text("DELETE FROM modelo_instruccion WHERE campana_id = :campana_id"), common)
    bind.execute(sa.text("DELETE FROM modelo_regla_inclusion WHERE campana_id = :campana_id"), common)

    for key in KEYS:
        bind.execute(
            sa.text(
                """
                INSERT INTO modelo_clave (
                    campana_id, codigo, etiqueta, descripcion, tipo_clave, tipo,
                    criterio_aplicacion, source_url, source_hash, capture_date
                )
                VALUES (
                    :campana_id, :codigo, :etiqueta, :descripcion,
                    'CLAVE_PERCEPCION', 'CLAVE_PERCEPCION',
                    :criterio, :source_url, :source_hash, :capture_date
                )
                """
            ),
            {**common, **key},
        )

    for instruction in INSTRUCTIONS:
        bind.execute(
            sa.text(
                """
                INSERT INTO modelo_instruccion (
                    campana_id, seccion, titulo, contenido, orden, texto,
                    casilla_referencia, source_url, source_hash, capture_date
                )
                VALUES (
                    :campana_id, :seccion, :titulo, :contenido, :orden,
                    :contenido, :casilla, :source_url, :source_hash, :capture_date
                )
                """
            ),
            {**common, **instruction},
        )

    for rule in RULES:
        bind.execute(
            sa.text(
                """
                INSERT INTO modelo_regla_inclusion (
                    campana_id, supuesto, decision, condicion, fuente_normativa,
                    source_url, source_hash, capture_date
                )
                VALUES (
                    :campana_id, :supuesto, 'CONDICIONAL', :condicion,
                    'AEAT diseno logico Modelo 190 2025, posicion 78 y ss.',
                    :source_url, :source_hash, :capture_date
                )
                """
            ),
            {**common, **rule},
        )


def downgrade() -> None:
    bind = op.get_bind()
    campana_id = _campaign_id(bind)
    params = {
        "campana_id": campana_id,
        "source_url": DR_190_2025_URL,
        "source_hash": DR_190_2025_HASH,
    }
    bind.execute(
        sa.text(
            """
            DELETE FROM modelo_regla_inclusion
            WHERE campana_id = :campana_id
              AND source_url = :source_url
              AND source_hash = :source_hash
            """
        ),
        params,
    )
    bind.execute(
        sa.text(
            """
            DELETE FROM modelo_instruccion
            WHERE campana_id = :campana_id
              AND source_url = :source_url
              AND source_hash = :source_hash
            """
        ),
        params,
    )
    bind.execute(
        sa.text(
            """
            DELETE FROM modelo_clave
            WHERE campana_id = :campana_id
              AND source_url = :source_url
              AND source_hash = :source_hash
            """
        ),
        params,
    )
