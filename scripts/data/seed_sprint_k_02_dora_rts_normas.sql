-- Sprint K K-02: load confirmed DORA RTS delegated regulations.
--
-- EUR-Lex verified from VPS:
-- - 32024R1774 HTTP 200, DORA content, publication 2024-06-25
-- - 32024R1773 HTTP 200, DORA content, publication 2024-06-25

INSERT INTO norma (
    codigo,
    titulo,
    boe_id,
    jurisdiccion,
    tipo_fuente,
    tipo_documento,
    ambito,
    estado_cobertura,
    vigente_desde,
    celex,
    tipo_norma,
    publicacion_doue,
    vigente,
    url_eurlex,
    norma_padre_celex
)
VALUES
(
    '32024R1774',
    'Reglamento Delegado (UE) 2024/1774 normas tecnicas de regulacion sobre herramientas, metodos, procesos y politicas de gestion del riesgo TIC y marco simplificado DORA',
    'EUR-CELEX-32024R1774',
    'ue',
    'eurlex',
    'rts',
    'mercados_financieros_ue',
    'metadata_official',
    DATE '2024-06-25',
    '32024R1774',
    'reglamento_delegado_ue',
    DATE '2024-06-25',
    TRUE,
    'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32024R1774',
    '32022R2554'
),
(
    '32024R1773',
    'Reglamento Delegado (UE) 2024/1773 normas tecnicas de regulacion sobre acuerdos contractuales con proveedores terceros de servicios TIC que sustenten funciones esenciales o importantes',
    'EUR-CELEX-32024R1773',
    'ue',
    'eurlex',
    'rts',
    'mercados_financieros_ue',
    'metadata_official',
    DATE '2024-06-25',
    '32024R1773',
    'reglamento_delegado_ue',
    DATE '2024-06-25',
    TRUE,
    'https://eur-lex.europa.eu/legal-content/ES/ALL/?uri=CELEX:32024R1773',
    '32022R2554'
)
ON CONFLICT (codigo) DO UPDATE
SET titulo = EXCLUDED.titulo,
    boe_id = EXCLUDED.boe_id,
    jurisdiccion = EXCLUDED.jurisdiccion,
    tipo_fuente = EXCLUDED.tipo_fuente,
    tipo_documento = EXCLUDED.tipo_documento,
    ambito = EXCLUDED.ambito,
    estado_cobertura = EXCLUDED.estado_cobertura,
    vigente_desde = EXCLUDED.vigente_desde,
    celex = EXCLUDED.celex,
    tipo_norma = EXCLUDED.tipo_norma,
    publicacion_doue = EXCLUDED.publicacion_doue,
    vigente = EXCLUDED.vigente,
    url_eurlex = EXCLUDED.url_eurlex,
    norma_padre_celex = EXCLUDED.norma_padre_celex;
