-- Sprint K K-01: remove weak duplicate DORA norma entry.
--
-- Preconditions verified in production:
-- - no obligacion_perfil rows reference DORA_2022_2535
-- - no obligacion_fuente rows reference DORA_2022_2535
--
-- The authoritative DORA base regulation is norma.codigo='32022R2554'.

UPDATE obligacion_perfil
SET norma_codigo = '32022R2554'
WHERE norma_codigo = 'DORA_2022_2535';

UPDATE obligacion_fuente
SET codigo_referencia = '32022R2554'
WHERE codigo_referencia = 'DORA_2022_2535';

DELETE FROM norma
WHERE codigo = 'DORA_2022_2535';
