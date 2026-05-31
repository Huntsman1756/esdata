# Source Expansion Backlog - 2026-05-17

## Contract

This file tracks source families requested on 2026-05-17. It is not a claim that all rows are loaded. Status values:

- `implemented_loaded`: code and production rows exist.
- `implemented_partial`: code and some production rows exist, but coverage is partial.
- `ready_for_ingestion`: code supports the source; production rows still need a worker run.
- `target`: source identified, implementation pending.
- `do_not_mix`: related to an existing domain, but must remain a separate family/table.

## Current Snapshot

| Domain | Status | Notes |
| --- | --- | --- |
| AEAT modelos | `implemented_partial` | 219 modelos, 31k+ casillas; 187/193/198/216/290/296 with structured instructions/keys complete, 200/303 partial. |
| AEAT CDI | `implemented_partial` | Worker/API/MCP and historical production rows exist; must still close a separate double-tax-treaty contract by country, article, income type and evidence. |
| AEAT GI42 / CRS Modelo 289 | `target` | Procedure source identified; useful for CRS/FATCA workflow expansion. |
| BOE consolidated legislation | `implemented_partial` | Core tax laws loaded; RD 813/2023 (`RD_813_2023`) loaded on VPS with 163 articles. |
| BOE diario | `implemented_partial` | Daily non-consolidated notices go to `documento_interpretativo` with `tipo_fuente='boe_diario'`; not automatically committed to repo, loaded by cron/DB. |
| CNMV | `implemented_partial` | Circulares, guias tecnicas, documentos a consulta, normativa ESI and modelos ESI are separated by document type. 2026-05-31 expansion adds the official sanctions register as `sancion_cnmv` / `sanciones_cnmv`; follow-up repo review uses Ansvar's pagination pattern to raise the sanctions page cap to 25 while keeping the family partial. |
| EUR-Lex | `implemented_partial` | Curated CELEX seed exists, including EMIR `32012R0648`; full ISRB/Q&A coverage is pending. |
| ESMA markets | `implemented_partial` | MiFIR/MiCA/DLT and selected reporting schemas/rules loaded; MiFIR reporting hub, ISRB Article 26 and Q&A index are loaded as reporting documents. VPS: `esma_reporting_document` MIFIR = 7. |
| Banco de Espana | `implemented_partial` | Small current corpus loaded; circulars and financial-system regulation index need expansion. |
| BORME | `implemented_partial` | Pilot rows loaded; improvement should focus on structured company events and freshness. |
| DGT | `implemented_loaded` | 18,631 consultas vinculantes loaded at last production snapshot; completeness still depends on source discovery limits. |
| TEAC | `implemented_partial` | 10 resoluciones loaded; DYCTEA and doctrina historica need broader ingestion. |
| AEPD | `implemented_partial` | 25 docs loaded; circulars/normativa/instrucciones/transparency families need separation. |
| SEPBLAC | `implemented_partial` | Normativa nacional/comunitaria and obligaciones pages loaded. VPS: 6 docs SEPBLAC, 4 `obligacion_sepblac`. |
| Sanctions / screening | `implemented_partial` | OFAC and EU sanctions entries exist. EU sanctions parser/cron uses the official Commission FSF XML 1.1 `downloadURL` published by `data.europa.eu` and loaded 5.996 rows on VPS (`actualizada=2026-05-08`). UN/SEPBLAC sanctions remain target/fail-closed. |
| GIIN / FATCA IRS | `implemented_partial` | GIIN registry and Modelo 290/FATCA rules exist; IRS FATCA source family needs explicit contract. |
| PGC / ESEF | `implemented_partial` | PGC data and XBRL tables exist; ESMA ESEF taxonomy element/label/mapping tables remain target. |

## BOE / EUR-Lex Financial Core

| Item | Official reference | Code status | Contract |
| --- | --- | --- | --- |
| LIVMC | `BOE-A-2023-7053` | `implemented_partial`, 356 production rows | Spanish securities-market law, primary obligation source. User-provided `BOE-A-2023-13494` is not LIVMC. |
| LPBC-FT | `BOE-A-2010-6737` | `implemented_partial`, 80 production rows as `LEY10_2010` | Keep canonical code `LEY10_2010`; aliases `LPBC`, `LPBCFT`, `PBCFT` point to it. Caveat: 2 BOE blocks skipped due invalid upstream date payload. |
| RD 1082/2012 | `BOE-A-2012-9716` | `implemented_partial`, 167 production rows | Spanish IIC regulation, primary/subordinate regulatory source. |
| RD 813/2023 | `BOE-A-2023-22763` | `implemented_partial`, 163 production rows as `RD_813_2023` | Regime for investment firms/ESI, primary/subordinate Spanish source for sociedad de valores back-office. |
| EMIR | `CELEX:32012R0648` | `implemented_partial`, 137 production rows in `eurlex_market` | EU regulation via EUR-Lex, not BOE. Common `norma/articulo` seed is metadata-only; official articles are exposed via `/v1/eurlex/market/32012R0648`. |

## Target Source Families

### AEAT / Hacienda

- CDI AEAT official page: `https://sede.agenciatributaria.gob.es/Sede/normativa-criterios-interpretativos/fiscalidad-internacional/convenios-doble-imposicion-firmados-espana.html`
- Hacienda CDI alpha page: `https://www.hacienda.gob.es/es-ES/Normativa%20y%20doctrina/Normativa/CDI/Paginas/CDI_Alfa.aspx`
- CRS Modelo 289 procedure: `https://sede.agenciatributaria.gob.es/Sede/procedimientoini/GI42.shtml`
- Helper repositories to evaluate only as tooling references, not authoritative corpus: `babu-cat/AEAT`, `OpenHacienda/puntoBOE`.
- Current residual priority from the 2026-05-31 audit: keep `124`, `126` and `128` as `CONFLICT` until direct official campaign evidence exists; re-audit `217`, `113`, `122`, `145`, `210`, `111`, `115`, `117`, `237`, `211`, `213` by official source only. Do not infer campaign truth from generic metadata.

### CNMV

- Normativa comunitaria.
- Circulares CNMV.
- Legislacion CNMV / ESI (`normativa_esi_cnmv`, implemented_partial).
- Guias tecnicas.
- Registro publico oficial de sanciones (`sancion_cnmv`, implementation 2026-05-31): keep as monitoring/evidence source, `partial_loaded`, with BOE/CNMV link per row and no claim of historical universe. `CNMV_SANCIONES_MAX_PAGES` defaults to `25` after reviewing public MCP/scraper practice; the worker stops before the cap if the official page returns no rows.
- FAQ normas/recomendaciones.
- Modelos normalizados ESI (`modelo_esi_cnmv`, implemented_partial) and IM (target).
- Libro jurisprudencia, arboles 1 and 2.

Each must keep a separate `tipo_documento`/contract. Registers and forms should become structured tables where possible, not generic documents.

### ESMA / EUR-Lex

- ESMA MiFIR reporting page and documents (`implemented_partial`: reporting hub, transaction reporting schema/instructions/validation rules, ISRB Article 26 and Q&A index).
- MiFIR review 2024/2026: target CELEX `32024R0791` and `32024L0790` before any broad market-data expansion.
- MAR dedicated coverage: target CELEX `32014R0596`.
- RTS 1/2 dedicated evidence: target CELEX `32017R0587` and `32017R0583`, ensuring profile applicability stays evidence/fail-closed.
- ESMA CSDR reporting.
- ESMA SFTR reporting.
- ESMA Interactive Single Rulebook.
- ESMA Q&A.
- ISRB acts: MiFIR, EMIR, SFTR, SECR, Benchmarks, CRAR, MiCA, Prospectus, MiFID II, UCITS, Transparency Directive, DORA, SSR, CSDR.
- ESMA MiCA non-CASP registers: target white papers, ART issuers, EMT issuers and non-compliant entities. This is separate from existing CASP rows.
- ESMA reference data: keep FIRDS/FITRS scoped. Do not download full FIRDS universe by default; use current metadata/register freshness and small DLTINS pilot samples only when needed.
- `Ansvar-Systems/EU_compliance_MCP` can be reviewed as implementation inspiration only; official EUR-Lex/ESMA remain source of truth.

### Banco de Espana

- Circulars chronological index.
- Financial-system regulation page.
- BOE financial code page.

### TEAC / AEPD / SEPBLAC

- TEAC DYCTEA and doctrina historica.
- AEPD circulars, normativa, instrucciones, and data-protection transparency information.
- SEPBLAC national and EU normativa plus obligations pages (`implemented_partial`).

### BORME

- Next safe expansion: structured act parser from official BOE/BORME PDFs already discovered by `worker-borme`.
- Candidate fields: `borme_id`, `seccion`, `fecha_publicacion`, `provincia`, `empresa_denominacion`, explicit `nif`, domicilio, objeto social, `acto_tipo`, persons/roles and registry data.
- Candidate act types: deposito de cuentas, revocacion, apoderamiento, fusion/absorcion, escision, transformacion, extincion and socio unico.
- Public repos such as GPL BORME parsers are implementation references only; do not copy code or import GPL dependencies into this repo.

### Screening / Sanctions

- EU sanctions parser/cron is `implemented_partial`; production uses the official Commission FSF XML 1.1 `downloadURL` with token published by `data.europa.eu`.
- UN and SEPBLAC sanctions remain pending.
- OpenOwnership, FollowTheMoney, Memorious, Nomenklatura, OpenSanctions and Yente are tooling/data-model candidates, not official legal sources by themselves.

### PGC / ESEF

- ESMA ESEF taxonomy 2024 ZIP.
- ICAC taxonomia contable.
- CNMV taxonomy report.
- Proposed target tables: `esef_taxonomy_element`, `esef_label`, `esef_mapping_pgc`.
