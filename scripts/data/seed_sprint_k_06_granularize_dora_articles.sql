-- Sprint K K-06: granularize DORA article ranges to anchor articles.
--
-- This script intentionally changes only articulo_referencia and notas.
-- It does not change verified or completeness.

UPDATE obligacion_perfil
SET articulo_referencia = 'art. 5',
    notas = concat_ws(
        ' ',
        NULLIF(notas, ''),
        'Referencia granularizada: arts. 5-16 DORA + RTS 32024R1774; art. 5 es el ancla de gobernanza y marco TIC.'
    )
WHERE norma_codigo = '32022R2554'
  AND articulo_referencia IN ('arts. 5-16', 'art. 5-16')
  AND descripcion ILIKE '%Marco%riesgo TIC%';

UPDATE obligacion_perfil
SET articulo_referencia = 'art. 19',
    notas = concat_ws(
        ' ',
        NULLIF(notas, ''),
        'Referencia granularizada: arts. 17-23 DORA; art. 19 es el ancla de notificacion. Notificacion inicial: 4h desde clasificacion. Informe intermedio: 72h. Informe final: 1 mes.'
    )
WHERE norma_codigo = '32022R2554'
  AND articulo_referencia = 'arts. 17-23'
  AND descripcion ILIKE '%Reporting%incidentes%';

UPDATE obligacion_perfil
SET articulo_referencia = 'art. 26',
    notas = concat_ws(
        ' ',
        NULLIF(notas, ''),
        'Referencia granularizada: arts. 26-27 DORA; art. 26 es el ancla TLPT. Solo para entidades significativas designadas por supervisor. Periodicidad: cada 3 anos.'
    )
WHERE norma_codigo = '32022R2554'
  AND articulo_referencia = 'arts. 26-27'
  AND (
      descripcion ILIKE '%TLPT%'
      OR descripcion ILIKE '%Pruebas%resiliencia%'
  );
