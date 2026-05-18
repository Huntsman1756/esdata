BEGIN;

WITH campana AS (
    SELECT mc.id AS campana_id
    FROM modelo_campana mc
    JOIN aeat_modelo am ON am.id = mc.modelo_id
    WHERE am.codigo = '289'
    ORDER BY mc.id DESC
    LIMIT 1
),
rows_to_insert AS (
    SELECT
        campana.campana_id,
        data.supuesto,
        data.decision,
        data.condicion,
        data.umbral,
        data.fuente_normativa,
        data.source_url
    FROM campana
    CROSS JOIN (
        VALUES
        (
            'Entidad de custodia',
            'INCLUIR',
            'entidad_tipo = CUSTODIA',
            NULL,
            'RD 1021/2015 art. 1.2.a',
            'https://www.boe.es/buscar/doc.php?id=BOE-A-2015-12399'
        ),
        (
            'Entidad de deposito',
            'INCLUIR',
            'entidad_tipo = DEPOSITO',
            NULL,
            'RD 1021/2015 art. 1.2.b',
            'https://www.boe.es/buscar/doc.php?id=BOE-A-2015-12399'
        ),
        (
            'Entidad de inversion',
            'INCLUIR',
            'entidad_tipo = INVERSION',
            NULL,
            'RD 1021/2015 art. 1.2.c',
            'https://www.boe.es/buscar/doc.php?id=BOE-A-2015-12399'
        ),
        (
            'Entidad gubernamental, organizacion internacional o banco central',
            'EXCLUIR',
            'entidad_tipo IN (GUBERNAMENTAL, ORGANIZACION_INTERNACIONAL, BANCO_CENTRAL)',
            NULL,
            'RD 1021/2015 art. 2',
            'https://www.boe.es/buscar/doc.php?id=BOE-A-2015-12399'
        ),
        (
            'Entidad no financiera activa',
            'EXCLUIR',
            'titular_tipo = ACTIVE_NFE',
            NULL,
            'RD 1021/2015 Seccion IV',
            'https://www.boe.es/buscar/doc.php?id=BOE-A-2015-12399'
        ),
        (
            'Cuenta preexistente de entidad bajo umbral de minimis',
            'EXCLUIR',
            'saldo_cuenta < 250000 AND cuenta_tipo = PREEXISTENTE_ENTIDAD',
            '250000 USD',
            'RD 1021/2015 Seccion V.D',
            'https://www.boe.es/buscar/doc.php?id=BOE-A-2015-12399'
        )
    ) AS data(supuesto, decision, condicion, umbral, fuente_normativa, source_url)
)
INSERT INTO modelo_regla_inclusion (
    campana_id,
    supuesto,
    decision,
    condicion,
    umbral,
    fuente_normativa,
    source_url,
    capture_date
)
SELECT
    campana_id,
    supuesto,
    decision,
    condicion,
    umbral,
    fuente_normativa,
    source_url,
    CURRENT_DATE
FROM rows_to_insert r
WHERE NOT EXISTS (
    SELECT 1
    FROM modelo_regla_inclusion mri
    WHERE mri.campana_id = r.campana_id
      AND mri.supuesto = r.supuesto
);

COMMIT;
