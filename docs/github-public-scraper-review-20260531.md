# Revision GitHub de scrapers publicos para fuentes parciales

Fecha: 2026-05-31

Objetivo: identificar repositorios publicos que ya hayan resuelto discovery/scraping de fuentes donde ESData sigue parcial, sin copiar codigo con licencia incompatible ni elevar claims de cobertura.

## Estado ESData usado como base

Fuentes parciales o mejorables segun la matriz viva:

- `CNMV`: parcial; hoy cubre familias documentales, pero queda residual por documentos externos no descargables y no hay producto amplio de sanciones/registros.
- `CENDOJ`: `very_limited`; el worker esta gateado por restricciones upstream/reuso.
- `AEPD`: parcial; hay guias/documentos y seeds, pero no bootstrap amplio de resoluciones.
- `BDE`: parcial; corpus pequeno y muy dependiente de seeds.
- `BORME`: parcial; ya hay sumario/PDF oficial con metadata heuristica, pero no parser mercantil certificado.
- `ESMA FIRDS/FITRS`: `very_limited`/piloto; no se debe cargar universo completo sin sprint especifico de almacenamiento y retencion.
- `PSD2/SEPA`, `GIIN/FATCA`, `CDI/DTA`, `PGC/XBRL/ESEF`: parciales por procedencia/cobertura, no por falta simple de scraper.

## Repos inspeccionados y decision

| Fuente | Repo / fichero relevante | Licencia vista | Utilidad para ESData | Decision |
| --- | --- | --- | --- | --- |
| CENDOJ | `edusu/spanish-jurisprudence-search` (`cendoj_search.py`) | `Other` | Cliente fino para `https://www.poderjudicial.es/search/search.action`, con bootstrap de sesion, formato de parametros `JURISDICCION`/`VALUESCOMUNIDAD`, parsing de resultados y aviso de WAF/rate-limit. | Muy util como referencia de protocolo. No copiar codigo; reimplementar un probe pequeno, disabled-by-default, tras revisar reuso. |
| CENDOJ | `GuiGel/mcp-cendoj` (`src/mcp_cendoj/http.py`) | Sin licencia declarada | Cliente async con sesion, limites de tamano, retry, 403/429/503 y rate limiting. | Util para contratos operativos y errores. No copiar codigo por falta de licencia. |
| CENDOJ | `vitamina-k/es-acc` (`tribunal_supremo.py`) | Sin licencia declarada | Intenta CENDOJ, pero incluye lista hardcoded de sentencias/casos con IDs aparentemente no verificables y fechas futuras. | Descartar para ingesta. Solo confirma que CENDOJ es friccionado. |
| CNMV | `worldwidelaw/legal-sources` (`sources/ES/CNMV/bootstrap.py`) | AGPL-3.0 | Scraper de registro de sanciones CNMV, pagina `Portal/Consultas/RegistroSanciones/verRegSanciones`, PDFs y metadata de sancion. | No copiar codigo AGPL. Reimplementar discovery propio si se abre sprint `cnmv_sanciones`, con revision legal de reuso. |
| CNMV | `vitamina-k/es-acc` (`etl/src/esacc_etl/pipelines/cnmv.py`) | Sin licencia declarada | Usa CSV oficial `https://www.cnmv.es/DocPortal/Publicaciones/Sanciones/Sanciones_abiertos.csv`. | Alto valor si el CSV sigue vivo. Verificar endpoint oficial y anadir familia separada `sanciones_cnmv` si procede. |
| CNMV/BDE | `Ansvar-Systems/spanish-financial-regulation-mcp` (`scripts/ingest-cnmv.ts`) | Apache-2.0 | MCP sectorial que scrapea circulares CNMV por paginas historicas, guias tecnicas y registro de sanciones con paginacion acotada. Declara que no redistribuye DB preconstruida por restricciones de fuentes. | Util como comparativa de cobertura/paginacion. ESData ya tiene parser propio equivalente; se adopta solo el patron operativo de paginar sanciones con tope amplio y corte por pagina vacia. |
| CNMV registros | `BquantFinance/cnmv` (`cnmv_entities_complete.csv`, `all_entities_detailed.csv`) | Sin licencia declarada | Snapshot CSV de entidades, fondos, administradores, socios, servicios, gestoras y depositarias CNMV con datos extraidos en agosto de 2025. No contiene scraper ni procedencia oficial por fila suficiente para ingestion autoritativa. | No ingerir el corpus. Puede servir para disenar un futuro worker de registros oficiales CNMV, pero debe reconsultar URLs oficiales y guardar `source_url`/`source_hash` por fila. |
| AEPD | `worldwidelaw/legal-sources` (`sources/ES/AEPD/bootstrap.py`) | AGPL-3.0 | Estrategia fuerte: RSS `resoluciones/feed.xml` + enumeracion directa de PDFs `https://www.aepd.es/documento/<tipo>-<numero>-<ano>.pdf` para `PS`, `AI`, `PD`, `PA`, `TD`. | No copiar codigo. Reimplementar discovery propio: es el candidato mas claro para mejorar AEPD. |
| AEPD | `ibernale/ai-lawyer` (`packages/ingest/.../sources/aepd.py`) | Sin licencia declarada | Scraping HTML de listado `resoluciones-y-actuaciones/resoluciones`, patron `PS/00001/2024`, rate limit 1 req/3s. | Util como referencia secundaria. No copiar. |
| BDE | `ibernale/ai-lawyer` (`packages/ingest/.../sources/bde.py`) | Sin licencia declarada | Fallback RSS/listado HTML para circulares, detectando `Circular N/YYYY`. El endpoint actual verificado para ESData es el indice cronologico oficial de circulares BdE. | Candidato claro para mejorar discovery BDE con implementacion propia. |
| ESMA FIRDS | `European-Securities-Markets-Authority/esma_data_py` | EUPL-1.2 | Paquete oficial ESMA para buscar/descargar datos de ESMA registers, incluyendo FIRDS/MIFID/SSR. | Mejor fuente tecnica para futuras mejoras ESMA. Usar como referencia/dep solo con decision explicita sobre EUPL y alcance. |
| ESMA FIRDS | `opensanctions/opensanctions` (`datasets/eu/esma_firds/crawler.py`) | MIT | Descarga el ultimo full dump `FULINS` desde Solr `esma_registers_firds_files`. | Tecnica util, pero choca con decision previa de no cargar universo FIRDS completo. Mantener como referencia de metadata/full-dump. |
| ESMA FIRDS | `bunburya/eu_finreg_data` (`firds.py`) | MIT | Ejemplos simples para Solr ESMA, ZIP/XML y extraccion ISIN/LEI. | Referencia ligera para tests/streaming, no suficiente como producto. |
| BORME | `PabloCastellano/bormeparser` | GPL-3.0+ | Parser historico de PDFs BORME, desmantenido, scripts de descarga/check/json. | No copiar ni depender. Puede inspirar casos de test/regex, pero ESData debe mantener parser propio. |
| BOE/BORME | `ComputingVictor/MCP-BOE` | MIT | Resolucion robusta de IDs BOE/BORME a PDF via datos abiertos o HTML `txt.php`, limites de tamano y extraccion PDF. | Util como comparativa; ESData ya usa patrones equivalentes en BOE/BORME. |
| BOE/corpus | `legalize-dev/legalize-es`, `dcarrero/boletines-md-corpus` | Sin licencia declarada visible via metadata | Corpus Markdown/legislacion, no principalmente scrapers integrables. | No ingerir corpus ni copiar sin licencia. Pueden servir para comparar cobertura si se revisa licencia. |

## Integraciones recomendadas

### 1. AEPD resoluciones bootstrap

Prioridad: alta.

Razon: ESData ya tiene worker AEPD, parser HTML/PDF, `source_revision`, `sync_log`, fail-closed API y tests base. Falta ampliar discovery de resoluciones.

Implementacion propuesta:

- Anadir discovery oficial controlado por flags:
  - RSS: `https://www.aepd.es/informes-y-resoluciones/resoluciones/feed.xml`.
  - Enumeracion acotada: `https://www.aepd.es/documento/{tipo}-{numero:05d}-{ano}.pdf` para `PS`, `AI`, `PD`, `PA`, `TD`.
- Defaults conservadores:
  - `AEPD_DISCOVER_RESOLUTIONS=true` para RSS oficial.
  - `AEPD_ENUMERATE_RESOLUTIONS=false` salvo sprint/ventana controlada.
  - `AEPD_RESOLUTION_START_YEAR`, `AEPD_RESOLUTION_MAX_PER_TYPE_YEAR`, `AEPD_RESOLUTION_MAX_CONSECUTIVE_MISSES`, `AEPD_MAX_URLS_PER_RUN`.
- Clasificar PDFs oficiales de resoluciones como `resolucion_aepd` y conservar `source_revision`/hash existente como control de cambios.
- Mantener `coverage_status=partial`, no prometer universo sancionador completo.

### 2. BDE circulares discovery

Prioridad: alta/media.

Razon: worker BDE actual es pequeno y seed-driven. El listado de circulares del BdE es una mejora de bajo riesgo si se trata como discovery documental parcial.

Implementacion propuesta:

- Descubrir enlaces desde el indice cronologico oficial de circulares del Banco de Espana.
- Detectar `Circular N/YYYY` en texto del enlace o pagina destino.
- Guardar metadata `circular_number`, `year`, `discovery_method=bde_circulares_listing`.
- Mantener seeds existentes y hacer discovery adicional, no sustitucion.

### 3. CNMV sanciones

Prioridad: media/alta.

Razon: podria enriquecer CNMV con un subdominio relevante, pero tiene mas sensibilidad legal/producto que AEPD/BDE.

Implementacion propuesta:

- Verificar primero si el CSV oficial `DocPortal/Publicaciones/Sanciones/Sanciones_abiertos.csv` sigue activo.
- Si existe y es oficial, crear familia separada `sanciones_cnmv` con contrato `partial_loaded`.
- No mezclar sanciones con circulares/modelos/normativa ya cargados.
- Revisar PII/reuso antes de exponer busqueda amplia.
- Tras revisar `Ansvar-Systems/spanish-financial-regulation-mcp`, ampliar el paginado HTML oficial con un tope conservador (`CNMV_SANCIONES_MAX_PAGES=25`) y corte al detectar pagina sin filas.
- No reutilizar snapshots `BquantFinance/cnmv`; usarlos solo como mapa de campos para un futuro worker de registros oficiales CNMV.

### 4. CENDOJ probe, no bulk

Prioridad: media/bloqueada por reuso.

Razon: hay scripts que demuestran endpoint funcional, pero CENDOJ tiene WAF/rate-limit y restricciones de reuso. Es la fuente con mayor riesgo de sobrerreclamo.

Implementacion propuesta:

- Reemplazar el estado `very_limited` solo si se crea un `CENDOJ_ENABLED` con probe muy pequeno:
  - bootstrap de sesion `indexAN.jsp`;
  - POST `search.action`;
  - busqueda por ECLI/ROJ exacto o query acotada;
  - rate limit duro y `MAX_RESPONSE_BYTES`;
  - sin bulk crawling.
- Mantener disabled-by-default hasta revision legal.

### 5. ESMA official loader

Prioridad: media/baja salvo que el producto necesite mercados.

Razon: `esma_data_py` es oficial y actualizado, pero cargar FIRDS completo contradice la decision actual de mantener FIRDS como piloto por coste/retencion.

Implementacion propuesta:

- No ampliar a FULINS completo sin sprint explicito.
- Si se abre sprint, evaluar `esma_data_py` para:
  - metadata de ficheros;
  - SSR;
  - MIFID file lists;
  - tests de checksum/streaming.

## No hacer

- No copiar codigo AGPL/GPL dentro de ESData.
- No ingerir corpus de terceros sin licencia clara aunque el repo sea publico.
- No usar repos con datos hardcoded o no verificables como fuente autoritativa.
- No elevar `CENDOJ`, `BORME`, `FIRDS` o `AEPD` a cobertura completa solo porque exista scraper publico.

## Proximo bloque recomendado

Abrir `GH-SCRAPER-AEPD-BDE-01`:

1. Implementar discovery AEPD resoluciones con tests unitarios y limites operativos.
2. Implementar discovery BDE circulares con tests unitarios.
3. Ejecutar local: tests focales, Ruff focal, `py_compile`, `verify-doc-contracts.py`, `source_assurance_gate.py`.
4. Desplegar VPS y correr `cron-aepd-weekly`/`cron-bde-weekly` una vez.
5. Validar `/status`, `/v1/aepd`, `/v1/bde`, `mcp_validation_suite.py --read-only` y `mcp_deep_contract_audit.py`.
