BEGIN;

UPDATE obligacion_perfil
SET notas = concat_ws(
        ' ',
        NULLIF(regexp_replace(COALESCE(notas, ''), '\s*Exenciones aplicables:.*$', '', 'i'), ''),
        'Exenciones aplicables: reference price waiver (RTS 1 art. 9.1.a), negotiated transaction waiver (RTS 1 art. 9.1.b), large in scale - LIS (RTS 1 art. 9.1.c; umbrales en Annex II) y order management facility waiver (RTS 1 art. 9.1.d). Solicitud de exencion ante la autoridad competente (CNMV).'
    ),
    verified = TRUE,
    completeness = 'parcial',
    capture_date = CURRENT_DATE
WHERE norma_codigo = '32017R0587'
  AND descripcion ILIKE '%pre-negociacion%';

UPDATE obligacion_perfil
SET notas = concat_ws(
        ' ',
        NULLIF(regexp_replace(COALESCE(notas, ''), '\s*Exenciones aplicables:.*$', '', 'i'), ''),
        'Exenciones aplicables: illiquid instrument waiver (RTS 2 art. 9.1.a), large in scale - LIS (RTS 2 art. 9.1.b) y above size specific to the instrument - SSTI (RTS 2 art. 9.1.c). Solicitud de exencion ante la autoridad competente (CNMV).'
    ),
    verified = TRUE,
    completeness = 'parcial',
    capture_date = CURRENT_DATE
WHERE norma_codigo = '32017R0583'
  AND descripcion ILIKE '%pre-negociacion%';

COMMIT;
