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

Produccion VPS verificada el 2026-05-12 tras S-06:

- `norma.tipo_fuente='eurlex'`: `32` normas.
- Articulos EUR-Lex: `93` para la ingesta acotada de MiFID II (`CELEX 32014L0065`).
- Versiones EUR-Lex: `93`.
- Ultimo `cron-eurlex-weekly` probado en VPS: `status=ok`, `rows_processed=93`, `fetch_articles=True`, `seed_selected=1`, `fetch_errors=0`.

Conclusion: EUR-Lex ya no esta limitado a metadata para todos los registros; MiFID II tiene articulado real cargado desde fuente oficial y el resto de CELEX sigue degradando a `metadata_only`/`evidence_limited` cuando no hay articulos. Antes de S-05, `/v1/eurlex/{referencia}` podia devolver `texto=""` sin aviso explicito; ahora el contrato API/MCP separa `coverage_status`, `verified`, `completeness`, `articulos_total` y `evidence_notice`.

## Decisiones

1. No se copian seed JSON ni textos de los repos externos.
2. No se adoptan herramientas interpretativas tipo `check_applicability`, `map_controls` o `compare_requirements` como autoridad legal. Pueden inspirar UI/UX de consulta, pero no poblar respuestas vinculantes.
3. EUR-Lex browser fallback queda como candidato controlado, no automatico. Debe tener allowlist CELEX, timeout global, limite por ejecucion, validacion anti-WAF y escritura de `sync_log` aunque no cargue articulos.
4. BOE diario/PDF fallback se tratara como nuevo worker o extension acotada para documentos no consolidados. Debe etiquetar el origen como XML diario o PDF, no mezclarlo con legislacion consolidada.
5. El siguiente gap de contrato MCP no es mas scraping: es output schema y metadatos de calidad/frescura por herramienta.

## S-07 BOE non-consolidated fallback

Evaluacion del patron `anamtb/boe-mcp`:

- Patron aceptable: probar primero la API de legislacion consolidada para normas `BOE-A` ya integrables en `norma/articulo/version_articulo`; si no existe texto consolidado o el identificador es `BOE-B`, `BOE-S` o `BOE-N`, consultar `https://www.boe.es/diario_boe/xml.php?id=<BOE-ID>`.
- Patron aceptable con etiqueta de calidad: si el XML diario no incluye texto suficiente, usar `url_pdf`/`url_archivo` del XML como fallback PDF. La construccion heuristica de PDF solo debe aceptarse si se valida HTTP 200, `Content-Type` PDF y hash de contenido.
- Patron rechazado como default: `fetchExternalUrl` sobre enlaces externos encontrados dentro del BOE. Puede servir a una herramienta manual futura, pero no debe poblar corpus oficial sin allowlist por organismo y tipo documental.
- Patron rechazado para el corpus consolidado: insertar anuncios, licitaciones, suplementos, notificaciones o PDFs no consolidados en `articulo/version_articulo`.

Mapa de necesidades:

| Tipo BOE | Fuente primaria | Fallback | Tabla destino | Calidad inicial |
| --- | --- | --- | --- | --- |
| `BOE-A` legislacion consolidable | `datosabiertos/api/legislacion-consolidada` | XML diario solo si falta el texto consolidado | `norma`, `articulo`, `version_articulo` solo para articulado consolidado; `documento_interpretativo` si no hay articulado | `complete/official_exact` para consolidado; `partial/official_best_effort` para XML/PDF no consolidado |
| `BOE-B` anuncios | `diario_boe/xml.php?id=<id>` | PDF oficial enlazado en XML | `documento_interpretativo` con `tipo_fuente='boe_diario'` o tabla futura `boe_diario_documento` | XML: `complete/official_exact` si texto completo; PDF: `partial/official_best_effort` |
| `BOE-S` suplementos | `diario_boe/xml.php?id=<id>` | PDF oficial enlazado en XML | `documento_interpretativo` / `boe_diario_documento` | `partial` salvo estructura XML completa |
| `BOE-N` notificaciones | `diario_boe/xml.php?id=<id>` | PDF oficial enlazado en XML | `documento_interpretativo` / `boe_diario_documento` | `partial`, no usar como normativa vigente |
| BORME-like | `diario_borme` / PDF oficial | PDF extraction actual de `apps/workers/borme.py` | `documento_interpretativo`, `empresa`, `documento_empresa` | `partial/official_best_effort` cuando la extraccion societaria es heuristica |

Campos de procedencia obligatorios antes de implementar:

- `referencia`: identificador BOE/BORME exacto (`BOE-B-YYYY-NNNNN`, `BOE-S-...`, `BOE-N-...`, `BORME-...`).
- `url_fuente`: URL oficial usada para responder; XML si el texto viene del XML, PDF si el texto viene del PDF.
- `source_revision`: `worker_name`, `source_entity_tipo`, `source_entity_id`, `source_url`, `content_hash_sha256`, `fetched_at` para cada XML/PDF descargado.
- `row_completeness`: `complete` solo si el XML oficial contiene texto suficiente y estructurado; `partial` para PDF OCR/text extraction o estructura no articulada.
- `row_provenance`: `official_exact` para XML estructurado oficial; `official_best_effort` para texto extraido de PDF o campos mercantiles heurísticos.
- `metadata`: debe incluir `source_format` (`boe_daily_xml`, `boe_pdf`, `borme_pdf`), `extraction_method`, `text_length`, `pdf_url`, `xml_url`, `content_hash` y cualquier aviso de truncado.

Implementacion recomendada:

1. Crear `worker-boe-diario` / `cron-boe-diario-daily` o una extension separada de `boe.py` que escriba en `documento_interpretativo`; no mezclar con `worker-boe` consolidado.
2. Exponer endpoints/MCP como `listar_boe_diario` y `get_boe_diario`, con filtros por `boe_id`, fecha, seccion y tipo (`BOE-B/S/N`).
3. Mantener `/v1/legislacion/*` y herramientas de articulado solo para `norma/articulo/version_articulo`.
4. Activar `document_decomposition.py` despues de ingesta si se necesita retrieval por fragmentos, conservando `documento_origen_tipo='documento_interpretativo'`.
5. Anadir tests con fixtures XML/PDF oficiales pequenos: XML completo, XML sin texto suficiente, PDF enlazado, 404/No encontrado, y caso `BOE-B` que nunca debe crear filas en `articulo`.

## Backlog Derivado

| ID | Prioridad | Historia | Resultado esperado |
| --- | ---: | --- | --- |
| S-05 | 1 | EUR-Lex quality contract | Exponer `metadata_only` / `article_text_available`, `verified`, `completeness` y `evidence_notice` en API/MCP. |
| S-06 | 2 | EUR-Lex deep ingestion safe mode | Implementado: ingesta por allowlist CELEX y presupuesto por ejecucion; MiFID II cargado en VPS con 93 articulos/versiones. Pendiente de expansion: lotes adicionales y quality counters esperados/parsing por CELEX. |
| S-07 | 3 | BOE non-consolidated fallback | Evaluado y documentado: XML/PDF no consolidado debe ir a `documento_interpretativo` o tabla `boe_diario_documento`, nunca a `articulo/version_articulo`; implementacion queda como historia separada. |
| S-08 | 4 | MCP output schemas | Implementado: herramientas HTTP y stdio se enriquecen con `outputSchema` tipo objeto y anotaciones `readOnlyHint=true`, `destructiveHint=false`. |
| S-09 | 5 | EU source registry quality counters | Implementado para EUR-Lex en `norma`: `articles_expected`, `articles_parsed`, `quality_status`, `quality_checked_at`; API list/detail los expone. |
