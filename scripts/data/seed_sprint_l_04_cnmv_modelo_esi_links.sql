-- Sprint L L-04: link CNMV ESI normalized model documents.
--
-- The AEAT model tables are intentionally not reused here: modelo_casilla and
-- modelo_instruccion hang from modelo_campana -> aeat_modelo, so CNMV forms
-- should not be forced into that schema without a dedicated design review.

INSERT INTO cnmv_obligation_link (documento_referencia, tipo_obligacion, nota)
SELECT
    d.referencia,
    'modelo_normalizado_esi',
    d.titulo
FROM documento_interpretativo d
WHERE d.organismo_emisor = 'CNMV'
  AND d.tipo_documento = 'modelo_esi_cnmv'
  AND NOT EXISTS (
      SELECT 1
      FROM cnmv_obligation_link l
      WHERE l.documento_referencia = d.referencia
        AND l.tipo_obligacion = 'modelo_normalizado_esi'
  );
