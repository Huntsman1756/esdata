BEGIN;

INSERT INTO documento_interpretativo (
    tipo_documento,
    organismo_emisor,
    jurisdiccion,
    tipo_fuente,
    ambito,
    referencia,
    fecha,
    titulo,
    texto,
    url_fuente,
    row_completeness,
    row_provenance,
    metadata
) VALUES (
    'registro_esma',
    'ESMA',
    'ue',
    'registro_oficial',
    'mercados_financieros_ue',
    'ESMA_REGISTERS_MIF_SI',
    CURRENT_DATE,
    'Registro ESMA de Internalizadores Sistematicos (MiFIR art. 4)',
    'Referencia oficial al registro ESMA de internalizadores sistematicos bajo MiFIR. Fuente soporte para determinar si una entidad concreta esta registrada como SI; no sustituye a RTS 1/2 ni a MiFIR como fuente normativa primaria.',
    'https://registers.esma.europa.eu/publication/searchRegister?core=ESMA_REGISTERS_MIF_SI',
    'complete',
    'official_exact',
    '{"fuente":"esma","sujeto_obligado":"esi_si","fuente_tipo":"registro_oficial"}'::jsonb
)
ON CONFLICT (referencia) DO UPDATE SET
    tipo_documento = EXCLUDED.tipo_documento,
    organismo_emisor = EXCLUDED.organismo_emisor,
    jurisdiccion = EXCLUDED.jurisdiccion,
    tipo_fuente = EXCLUDED.tipo_fuente,
    ambito = EXCLUDED.ambito,
    fecha = EXCLUDED.fecha,
    titulo = EXCLUDED.titulo,
    texto = EXCLUDED.texto,
    url_fuente = EXCLUDED.url_fuente,
    row_completeness = EXCLUDED.row_completeness,
    row_provenance = EXCLUDED.row_provenance,
    metadata = EXCLUDED.metadata;

INSERT INTO obligacion_fuente (
    obligacion_id,
    fuente_tipo,
    codigo_referencia,
    articulo,
    descripcion,
    source_url,
    peso
)
SELECT
    op.id,
    'registro_oficial',
    'ESMA_REGISTERS_MIF_SI',
    'MiFIR art. 4',
    'Registro ESMA de Internalizadores Sistematicos (MiFIR art.4)',
    'https://registers.esma.europa.eu/publication/searchRegister?core=ESMA_REGISTERS_MIF_SI',
    2
FROM obligacion_perfil op
WHERE op.perfil_codigo IN ('sociedad_valores', 'agencia_valores', 'entidad_credito')
  AND (
      op.descripcion ILIKE '%pre-negociacion%'
      OR op.descripcion ILIKE '%internalizador%'
      OR op.notas ILIKE '%Internalizador Sistematico%'
      OR op.notas ILIKE '%estatus SI%'
      OR op.notas ILIKE '%registrada como SI%'
  )
  AND NOT EXISTS (
      SELECT 1
      FROM obligacion_fuente existing
      WHERE existing.obligacion_id = op.id
        AND existing.source_url = 'https://registers.esma.europa.eu/publication/searchRegister?core=ESMA_REGISTERS_MIF_SI'
  );

COMMIT;
