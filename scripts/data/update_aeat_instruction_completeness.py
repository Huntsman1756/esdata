#!/usr/bin/env python3
"""Emit SQL to update AEAT model completeness after instruction/key loads."""

from __future__ import annotations

import sys


PRIORITY_MODELS = ("187", "193", "198", "200", "216", "290", "296", "303")


def q(value: object) -> str:
    if value is None:
        return "NULL"
    return "'" + str(value).replace("'", "''") + "'"


def main() -> int:
    codes = ", ".join(q(code) for code in PRIORITY_MODELS)
    sql = f"""
WITH metrics AS (
    SELECT
        c.id AS campana_id,
        m.codigo,
        COUNT(DISTINCT cs.id) AS casillas,
        COUNT(DISTINCT mc.id) AS claves,
        COUNT(DISTINCT mi.id) AS instrucciones,
        COUNT(DISTINCT mc.id) FILTER (
            WHERE mc.source_url IS NULL OR mc.source_hash IS NULL
        ) AS claves_missing_source,
        COUNT(DISTINCT mi.id) FILTER (
            WHERE mi.source_url IS NULL OR mi.source_hash IS NULL
        ) AS instrucciones_missing_source
    FROM aeat_modelo m
    JOIN modelo_campana c
      ON c.modelo_id = m.id
     AND c.activo = true
    LEFT JOIN modelo_casilla cs ON cs.campana_id = c.id
    LEFT JOIN modelo_clave mc ON mc.campana_id = c.id
    LEFT JOIN modelo_instruccion mi ON mi.campana_id = c.id
    WHERE m.codigo IN ({codes})
    GROUP BY c.id, m.codigo
),
classified AS (
    SELECT
        *,
        CASE
            WHEN casillas > 0
             AND claves > 0
             AND instrucciones > 0
             AND claves_missing_source = 0
             AND instrucciones_missing_source = 0
            THEN 'completa'
            ELSE 'parcial'
        END AS new_completeness
    FROM metrics
),
upserted AS (
    INSERT INTO modelo_campana_operativa (
        campana_id,
        origen_metadato,
        estado_metadato,
        completeness_estado,
        nota,
        actualizado_at
    )
    SELECT
        campana_id,
        'official_aeat_instruction_key_sprint',
        CASE WHEN new_completeness = 'completa' THEN 'curado' ELSE 'inferido' END,
        new_completeness,
        CASE
            WHEN new_completeness = 'completa'
            THEN 'Completeness graduada por evidencia oficial: casillas, claves e instrucciones cargadas con fuente trazable.'
            ELSE 'Permanece parcial: faltan claves, instrucciones o trazabilidad suficiente para contrato completa.'
        END,
        now()
    FROM classified
    ON CONFLICT (campana_id)
    DO UPDATE SET
        origen_metadato = EXCLUDED.origen_metadato,
        estado_metadato = EXCLUDED.estado_metadato,
        completeness_estado = EXCLUDED.completeness_estado,
        nota = EXCLUDED.nota,
        actualizado_at = now()
    RETURNING campana_id, completeness_estado
)
SELECT
    cl.codigo,
    cl.casillas,
    cl.claves,
    cl.instrucciones,
    cl.claves_missing_source,
    cl.instrucciones_missing_source,
    cl.new_completeness
FROM classified cl
ORDER BY cl.codigo;
"""
    sys.stdout.write(sql)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
