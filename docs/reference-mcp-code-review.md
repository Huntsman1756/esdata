# Reference MCP Code Review

Fecha: 2026-05-12

Repos revisados:

- `https://github.com/Ansvar-Systems/EU_compliance_MCP` / `https://github.com/ansvar-systems/eu_compliance_mcp` en `51b247c`.
- `https://github.com/anamtb/boe-mcp` en `999f48f`.

Objetivo: identificar codigo reutilizable como patron tecnico para cerrar gaps regulatorios de ESData sin usar datos comunitarios como fuente de verdad. La regla de ESData se mantiene: solo se persisten datos trazables a fuente oficial.

## Hallazgos Reutilizables

| Repo | Patron util | Evidencia en codigo revisado | Encaje ESData |
| --- | --- | --- | --- |
| `EU_compliance_MCP` | Fetch EUR-Lex con navegador cuando hay AWS WAF | `scripts/ingest-eurlex-browser.ts` usa Puppeteer, user-agent realista, espera red inactiva y rechaza HTML sospechosamente pequeno o paginas `window.gokuProps` | Util como fallback controlado, no como default. ESData ya tiene camino preferente por `publications.europa.eu/resource/celex/{CELEX}` y manifestaciones oficiales; el navegador solo deberia activarse con limite por CELEX y validacion fuerte. |
| `EU_compliance_MCP` | Registro de fuentes y frescura por CELEX | `scripts/check-updates.ts` trata `source_registry` como fuente de verdad y marca `UPDATE AVAILABLE`, `INCOMPLETE` o `MANUAL CHECK REQUIRED` | Encaja con `source_revision` y `/v1/sources/freshness`. Falta llevar el concepto de `articles_expected/articles_parsed/quality_status` a EUR-Lex para distinguir metadata-only de articulado completo. |
| `EU_compliance_MCP` | Catalogo MCP centralizado con anotaciones read-only | `src/tools/registry.ts` centraliza tool definitions y anade `readOnlyHint/destructiveHint` | ESData ya centraliza `HTTP_MCP_OPERATIONS`, pero el deep audit sigue avisando que faltan `outputSchema` en 63 tools. El patron sirve para fase de contrato MCP. |
| `EU_compliance_MCP` | Validaciones de calidad del parser | `scripts/ingest-eurlex.ts` valida anexos, definiciones, articulos y longitud antes de aceptar corpus | Incorporable para EUR-Lex: no marcar una norma como completa si no hay conteo esperado o texto suficiente. |
| `anamtb/boe-mcp` | BOE consolidado + diario XML + PDF fallback | `src/boe/api.ts` intenta legislacion consolidada, cae a `diario_boe/xml.php?id=...`, y si el texto es insuficiente intenta PDF | Util para BOE no consolidado, anuncios `BOE-B/BOE-S/BOE-N` y BORME. ESData BOE cubre legislacion consolidada; falta una historia separada para diario/PDF no consolidado con procedencia y marca de extraccion. |
| `anamtb/boe-mcp` | Relaciones BOE anteriores/posteriores | `getBoeRelationships()` lee `buscar/doc.php?id=<id>&xml=1` y extrae referencias | Puede mejorar grafo normativo de ESData si se persiste como relaciones verificadas, no inferidas. |

## Comprobacion ESData Actual

Produccion VPS verificada el 2026-05-12:

- `norma.tipo_fuente='eurlex'`: `32` normas.
- Articulos EUR-Lex: `0`.
- Versiones EUR-Lex: `0`.
- Ultimos `worker-eurlex` / `cron-eurlex-weekly`: `status=ok`, `fetch_articles=False`, `discovery_enabled=False`.

Conclusion: EUR-Lex esta sano como metadata oficial, pero no como corpus profundo de articulado. Antes de este cambio, `/v1/eurlex/{referencia}` podia devolver `texto=""` sin un aviso explicito de evidencia limitada. Eso se corrige en el contrato API/MCP con `coverage_status`, `verified`, `completeness`, `articulos_total` y `evidence_notice`.

## Decisiones

1. No se copian seed JSON ni textos de los repos externos.
2. No se adoptan herramientas interpretativas tipo `check_applicability`, `map_controls` o `compare_requirements` como autoridad legal. Pueden inspirar UI/UX de consulta, pero no poblar respuestas vinculantes.
3. EUR-Lex browser fallback queda como candidato controlado, no automatico. Debe tener allowlist CELEX, timeout global, limite por ejecucion, validacion anti-WAF y escritura de `sync_log` aunque no cargue articulos.
4. BOE diario/PDF fallback se tratara como nuevo worker o extension acotada para documentos no consolidados. Debe etiquetar el origen como XML diario o PDF, no mezclarlo con legislacion consolidada.
5. El siguiente gap de contrato MCP no es mas scraping: es output schema y metadatos de calidad/frescura por herramienta.

## Backlog Derivado

| ID | Prioridad | Historia | Resultado esperado |
| --- | ---: | --- | --- |
| S-05 | 1 | EUR-Lex quality contract | Exponer `metadata_only` / `article_text_available`, `verified`, `completeness` y `evidence_notice` en API/MCP. |
| S-06 | 2 | EUR-Lex deep ingestion safe mode | Activar ingesta de articulado por lotes pequenos usando Publications Office y, solo si hace falta, browser fallback validado. |
| S-07 | 3 | BOE non-consolidated fallback | Ingerir BOE diario/XML y PDF para documentos no consolidados con procedencia separada. |
| S-08 | 4 | MCP output schemas | Anadir `outputSchema`/anotaciones read-only a herramientas MCP expuestas. |
| S-09 | 5 | EU source registry quality counters | Persistir `articles_expected`, `articles_parsed` y `quality_status` por CELEX cuando el worker pueda medirlo. |

