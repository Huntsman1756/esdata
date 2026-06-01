"""expand modelo 190 perception keys to A-L

Revision ID: 20260601_0111_aeat_190_perception_keys_expansion
Revises: 20260601_0110_aeat_289_legal_campaign_evidence
Create Date: 2026-06-01

Revision 0109 traced the legacy A-D keys. This revision keeps the same AEAT
2025 design source and expands the active 190 campaign to the full main
perception-key set A-L. Subclave-level enumeration remains a separate cycle.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260601_0111_aeat_190_perception_keys_expansion"
down_revision = "20260601_0110_aeat_289_legal_campaign_evidence"
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
        'codigo': 'A',
        'etiqueta': 'Rendimientos del trabajo general',
        'descripcion': 'Rendimientos del trabajo: Empleados por cuenta ajena en general.',
        'criterio': 'Rendimientos del trabajo sujetos al procedimiento general del articulo 82 RIRPF y no encuadrados en B, C o D.',
    },
    {
        'codigo': 'B',
        'etiqueta': 'Pensionistas y haberes pasivos',
        'descripcion': 'Rendimientos del trabajo: Pensionistas y perceptores de haberes pasivos y demas prestaciones del articulo 17.2.a) LIRPF.',
        'criterio': 'Pensiones, haberes pasivos y prestaciones no exentas del articulo 17.2.a) LIRPF; requiere subclave.',
    },
    {
        'codigo': 'C',
        'etiqueta': 'Prestaciones o subsidios por desempleo',
        'descripcion': 'Rendimientos del trabajo: Prestaciones o subsidios por desempleo.',
        'criterio': 'Prestaciones o subsidios por desempleo, salvo pago unico; requiere subclave.',
    },
    {
        'codigo': 'D',
        'etiqueta': 'Prestaciones por desempleo pago unico',
        'descripcion': 'Rendimientos del trabajo: Prestaciones por desempleo abonadas en la modalidad de pago unico.',
        'criterio': 'Clave suprimida desde 2013 para nuevas prestaciones; se usa para reintegros de prestaciones indebidamente percibidas antes de 2013.',
    },
    {
        'codigo': 'E',
        'etiqueta': 'Consejeros y administradores',
        'descripcion': 'Rendimientos del trabajo: Consejeros y administradores.',
        'criterio': 'Retribuciones dinerarias o en especie satisfechas a administradores, miembros de consejos de administracion y organos representativos; requiere subclave.',
    },
    {
        'codigo': 'F',
        'etiqueta': 'Cursos, conferencias y obras',
        'descripcion': 'Rendimientos del trabajo: Cursos, conferencias, seminarios y similares y elaboracion de obras literarias, artisticas o cientificas.',
        'criterio': 'Rendimientos del trabajo por cursos, conferencias, seminarios o cesion de explotacion de obras; requiere subclave.',
    },
    {
        'codigo': 'G',
        'etiqueta': 'Actividades profesionales',
        'descripcion': 'Rendimientos de actividades economicas: Actividades profesionales.',
        'criterio': 'Contraprestaciones de actividades profesionales del articulo 101.5.a) LIRPF, incluida propiedad intelectual o cesion de imagen con calificacion profesional; requiere subclave.',
    },
    {
        'codigo': 'H',
        'etiqueta': 'Agricolas, ganaderas, forestales y objetiva',
        'descripcion': 'Rendimientos de actividades economicas: actividades agricolas, ganaderas y forestales y actividades en estimacion objetiva del articulo 95.6 RIRPF.',
        'criterio': 'Contraprestaciones de actividades agricolas, ganaderas o forestales y actividades en estimacion objetiva del articulo 95 RIRPF; requiere subclave.',
    },
    {
        'codigo': 'I',
        'etiqueta': 'Otros rendimientos de actividades economicas',
        'descripcion': 'Rendimientos de actividades economicas: rendimientos del articulo 75.2.b) RIRPF.',
        'criterio': 'Propiedad intelectual o industrial, asistencia tecnica, arrendamiento de bienes muebles, negocios o minas, subarrendamientos y cesion de imagen cuando no sean clave G; requiere subclave.',
    },
    {
        'codigo': 'J',
        'etiqueta': 'Cesion de derechos de imagen',
        'descripcion': 'Imputacion de rentas por cesion de derechos de imagen: contraprestaciones del articulo 92.8 LIRPF.',
        'criterio': 'Contraprestaciones a personas o entidades no residentes sujetas al ingreso a cuenta del articulo 92.8 LIRPF.',
    },
    {
        'codigo': 'K',
        'etiqueta': 'Premios y aprovechamientos forestales',
        'descripcion': 'Premios y ganancias patrimoniales de vecinos por aprovechamientos forestales en montes publicos.',
        'criterio': 'Premios sometidos a retencion o ingreso a cuenta y ganancias patrimoniales de vecinos por aprovechamientos forestales en montes publicos; requiere subclave.',
    },
    {
        'codigo': 'L',
        'etiqueta': 'Rentas exentas y dietas',
        'descripcion': 'Rentas exentas y dietas exceptuadas de gravamen.',
        'criterio': 'Dietas y gastos de viaje exceptuados de gravamen, rentas exentas del IRPF como rendimientos del trabajo y actividades economicas exentas del articulo 7 LIRPF; requiere subclave.',
    },
]


INSTRUCTIONS = [
    {
        "seccion": "diseno_registro_2025",
        "titulo": "Diseno de registro Modelo 190 2025",
        "contenido": (
            "El diseno logico AEAT del Modelo 190 para el ejercicio 2025 define "
            "la declaracion informativa anual de retenciones e ingresos a cuenta "
            "sobre rendimientos del trabajo, actividades economicas, premios, "
            "determinadas ganancias patrimoniales e imputaciones de rentas."
        ),
        "orden": 10,
        "casilla": None,
    },
    {
        "seccion": "clave_percepcion",
        "titulo": "Clave de percepcion",
        "contenido": (
            "La posicion 78 del registro de tipo 2 contiene la clave alfabetica "
            "de percepcion. El diseno 2025 enumera las claves principales A-L."
        ),
        "orden": 20,
        "casilla": "78",
    },
    {
        "seccion": "subclave",
        "titulo": "Subclave",
        "contenido": (
            "Las posiciones 79-80 contienen la subclave. El diseno 2025 exige "
            "subclave para las claves B, C, E, F, G, H, I, K y L; la enumeracion "
            "detalle de subclaves queda fuera de esta migracion."
        ),
        "orden": 30,
        "casilla": "79-80",
    },
]


RULES = [
    {
        "supuesto": f"Modelo 190 clave {key['codigo']} - {key['etiqueta']}",
        "condicion": key["criterio"],
    }
    for key in KEYS
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


def _replace_content(bind, keys: list[dict[str, str]], instructions: list[dict], rules: list[dict[str, str]]) -> None:
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
                        'capture_date', CAST(:capture_date AS text),
                        'evidence_scope', 'modelo_190_perception_keys_a_l'
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

    for key in keys:
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

    for instruction in instructions:
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

    for rule in rules:
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


def upgrade() -> None:
    bind = op.get_bind()
    _replace_content(bind, KEYS, INSTRUCTIONS, RULES)
    loaded = bind.execute(
        sa.text(
            """
            WITH active_campaign AS (
                SELECT mc.id
                FROM modelo_campana mc
                JOIN aeat_modelo am ON am.id = mc.modelo_id
                WHERE am.codigo = '190'
                  AND mc.campana = '2025'
                  AND mc.activo = true
            )
            SELECT COUNT(*) = 12
            FROM modelo_clave
            WHERE campana_id IN (SELECT id FROM active_campaign)
              AND codigo IN ('A','B','C','D','E','F','G','H','I','J','K','L')
              AND COALESCE(tipo, tipo_clave) = 'CLAVE_PERCEPCION'
              AND source_url = :source_url
              AND source_hash = :source_hash
              AND capture_date IS NOT NULL
            """
        ),
        {"source_url": DR_190_2025_URL, "source_hash": DR_190_2025_HASH},
    ).scalar()
    if loaded is not True:
        raise RuntimeError("Modelo 190 A-L perception key load did not satisfy COUNT(*) = 12")


def downgrade() -> None:
    bind = op.get_bind()
    _replace_content(bind, KEYS[:4], INSTRUCTIONS, RULES[:4])
