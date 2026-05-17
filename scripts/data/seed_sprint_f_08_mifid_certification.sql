\set ON_ERROR_STOP on

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM norma WHERE codigo = '32014L0065') THEN
        RAISE EXCEPTION 'Missing norma 32014L0065';
    END IF;
END $$;

UPDATE obligacion_perfil
SET norma_codigo = '32014L0065',
    articulo_referencia = 'art. 25.1',
    fuente_secundaria = 'ESMA35-43-1163 Guidelines on MiFID II knowledge and competence',
    source_url = 'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32014L0065',
    verified = true,
    completeness = 'completa',
    notas = 'MiFID II art. 25.1: las ESI deben asegurar y demostrar que el personal que presta asesoramiento o proporciona informacion sobre instrumentos financieros, servicios de inversion o servicios auxiliares dispone de conocimientos y competencias necesarios.'
WHERE descripcion ILIKE '%Certificacion MiFID II%'
  AND verified = false;
