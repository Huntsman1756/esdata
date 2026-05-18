BEGIN;

WITH modelo AS (
    SELECT id
    FROM aeat_modelo
    WHERE codigo = '289'
    LIMIT 1
),
rows_to_insert AS (
    SELECT
        modelo.id AS modelo_id,
        data.boe_id,
        data.titulo,
        data.fecha::date AS fecha,
        data.url_boe,
        data.resumen
    FROM modelo
    CROSS JOIN (
        VALUES
        (
            'BOE-A-2015-12399',
            'Real Decreto 1021/2015 - CRS cuentas financieras',
            '2015-11-14',
            'https://www.boe.es/buscar/doc.php?id=BOE-A-2015-12399',
            'Real Decreto 1021/2015, de 13 de noviembre, obligacion de identificar la residencia fiscal y comunicar cuentas financieras en el marco CRS.'
        ),
        (
            'BOE-A-2003-23186#DA22',
            'Ley 58/2003 General Tributaria - Disposicion adicional 22',
            '2003-12-18',
            'https://www.boe.es/buscar/act.php?id=BOE-A-2003-23186',
            'Ley 58/2003 General Tributaria, Disposicion Adicional Vigesima Segunda, asistencia mutua e intercambio automatico de informacion sobre cuentas financieras.'
        ),
        (
            'EUR-CELEX-32014L0107',
            'Directiva 2014/107/UE DAC2 - intercambio automatico de cuentas financieras',
            '2014-12-16',
            'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32014L0107',
            'Directiva 2014/107/UE (DAC2), intercambio automatico obligatorio de informacion en el ambito de la fiscalidad sobre cuentas financieras.'
        )
    ) AS data(boe_id, titulo, fecha, url_boe, resumen)
)
INSERT INTO modelo_normativa (
    modelo_id,
    boe_id,
    titulo,
    fecha,
    url_boe,
    resumen
)
SELECT
    modelo_id,
    boe_id,
    titulo,
    fecha,
    url_boe,
    resumen
FROM rows_to_insert r
WHERE NOT EXISTS (
    SELECT 1
    FROM modelo_normativa mn
    WHERE mn.modelo_id = r.modelo_id
      AND (
          mn.boe_id = r.boe_id
          OR mn.url_boe = r.url_boe
      )
);

COMMIT;
