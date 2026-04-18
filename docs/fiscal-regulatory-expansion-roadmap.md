# Fiscal and Regulatory Expansion Roadmap

## Purpose

This document translates the current product gap into an executable expansion plan for `esdata`.

The goal is not to turn `esdata` into a generic legal copilot. The goal is to strengthen the fiscal and regulatory data layer that already exists in the repo so it can support:

- fiscal research with official-source traceability
- regulatory compliance workflows
- downstream AI agents and internal copilots
- future private-knowledge overlays for firms or in-house teams

This roadmap is written to fit the current architecture of the project:

- source-specific workers
- FastAPI routers by domain/source
- shared PostgreSQL storage
- official-source traceability
- public API and MCP surface

## Current baseline

Today `esdata` already has a strong nucleus:

- `BOE` legislative ingestion for a selected fiscal corpus
- `DGT` doctrine ingestion
- `TEAC` doctrine ingestion
- `AEAT` model metadata, instructions, boxes, keys and regulatory links
- initial documentary slices for `CNMV` and `SEPBLAC`
- initial normalized layer for `obligacion_regulatoria`
- `BDNS` and `BORME` as adjacent public sources

This means the next phase should not restart architecture. It should extend the existing source pattern with higher-value corpora and denser normalization.

## Expansion principles

### 1. Keep the current source pattern

New public sources should continue to follow the existing pattern:

- one worker per source or source family
- one router per source or normalized domain
- one canonical reference format per source
- persistence in shared tables only when the semantics match
- bridge tables when the semantics do not match cleanly

### 2. Preserve traceability over convenience

Every new slice must keep:

- source URL
- canonical reference
- publication or resolution date
- issuing body
- document type
- vigency status when possible
- explicit links to superior norm or related obligations

### 3. Separate raw corpus from normalized obligations

The roadmap has two different layers:

- corpus layer: laws, judgments, doctrine, circulars, manuals, resolutions
- normalized layer: obligations, deadlines, filing duties, subjects, evidence, trigger events

The mistake to avoid is trying to normalize everything before the corpus is dense enough.

### 4. Bias to fiscal and regulatory value

This roadmap excludes broad legal coverage unless it directly improves the fiscal/regulatory product.

That means priority goes to:

- tax procedure
- tax doctrine
- tax litigation
- financial regulation
- AML / PBC-FT
- administrative compliance sources that affect corporate operations

## Target source map

The highest-value missing sources are below.

| Priority | Source | Why it matters | Best fit in current architecture |
|---|---|---|---|
| P1 | `CENDOJ` filtered corpus | adds real jurisprudence beyond `TEAC` and makes the product materially stronger in fiscal disputes and administrative litigation | new worker + new router + reuse `documento_interpretativo` initially |
| P1 | additional `BOE` regulatory texts | closes the gap between law and day-to-day practice, especially for regulations and procedural texts | extend `worker-boe` where possible, fallback worker or seed path where BOE API coverage fails |
| P1 | `EUR-Lex` expanded corpus | needed for financial regulation and EU-driven compliance | new `worker-eurlex` or reusable EU support module, reuse `norma` |
| P2 | `AEPD` | highly relevant for operational compliance and internal legal work | new worker + router, reuse `documento_interpretativo` |
| P2 | `Banco de España` | key for regulated financial activity and circular-driven obligations | new worker + router, reuse `documento_interpretativo` plus obligations |
| P2 | `DGSJFP` | relevant for company, registry and mercantile/regulatory interpretations | new worker + router, reuse `documento_interpretativo` |
| P3 | `CNMC` | useful but less central than tax, AML and financial regulation for current positioning | new worker + router, reuse `documento_interpretativo` |
| P3 | `ITSS` | useful if employment compliance becomes a real product axis | new worker + router, reuse `documento_interpretativo` |

## Detailed source plan

## 1. CENDOJ

### Why add it

`TEAC` is strong for tax doctrine and economic-administrative criteria, but it does not replace judicial case law.

The minimum useful CENDOJ slice is not all jurisdictions. It should start with:

- `Tribunal Supremo`
- `Audiencia Nacional`
- `TSJ`

And with matter filters close to the current product:

- tributario
- contencioso-administrativo
- mercantil-regulatorio
- AML / PBC-FT where identifiable

### Storage fit

Phase 1 can reuse `documento_interpretativo` with a stricter subtype taxonomy, for example:

- `sentencia_ts`
- `sentencia_an`
- `sentencia_tsj`
- `auto`

Long term, a dedicated judicial table may be cleaner, but it is not required to unlock value.

### New components

- `apps/workers/cendoj.py`
- `apps/api/routers/jurisprudencia.py`
- optional `apps/api/services/jurisprudencia.py`

### Ingestion concerns

- canonicalization of identifiers
- duplicates across chambers or exports
- partial metadata quality depending on source entrypoint
- court/chamber normalization
- references to law articles that differ from DGT/TEAC citation patterns

### Maintenance model

- weekly sync initially
- idempotent upsert by canonical resolution reference
- backfill mode separate from rolling sync
- source-health metrics in `sync_log`

## 2. BOE expansion beyond current nucleus

### Why add it

The current BOE slice is valuable but still too narrow for day-to-day tax and compliance work.

The biggest gap is regulatory and operational depth, especially:

- `RIRPF`
- `RIVA`
- `RIS`
- procedural and management regulations
- supporting orders and implementing rules that sit below the law

### Storage fit

Keep using:

- `norma`
- `articulo`
- `version_articulo`

This is the right shape and should remain the default for hierarchical norms.

### Implementation approach

Use a split path:

1. `worker-boe` for norms supported by the BOE consolidated API
2. a fallback strategy for norms not covered cleanly by that API:
   - direct HTML/PDF parsing
   - bootstrap seeds with canonical IDs
   - source-specific fetch adapters where necessary

### New components

- extend `apps/workers/boe.py`
- optional helper module for non-consolidated BOE texts
- no new router required if the norm model remains consistent

### Maintenance model

- daily sync for live norms
- explicit coverage manifest in config
- per-norm health reporting in `sync_log`
- regression tests for each newly added norm code

## 3. EUR-Lex expansion

### Why add it

The repo already acknowledges EU-driven fiscal/regulatory needs. The current coverage is too thin to support strong regulatory workflows.

EU material matters especially for:

- prudential and reporting duties
- financial intermediaries
- AML frameworks
- DAC-related reporting

### Storage fit

Reuse `norma` for:

- regulations
- delegated regulations
- directives where useful for context

Important distinction:

- directly applicable EU regulations belong naturally in `norma`
- guidance-like EU material should not be forced into `norma`

### New components

- `apps/workers/eurlex.py`
- optional `apps/api/routers/ue.py` if separate surface is useful

### Maintenance model

- weekly sync
- canonical CELEX-based references
- explicit relation mapping from EU norm to BOE/CNMV/SEPBLAC obligations where available

## 4. AEPD

### Why add it

AEPD matters because real fiscal and regulatory work in companies often crosses into privacy compliance:

- customer data
- employee data
- KYC and onboarding
- AML monitoring records
- retention and access rights

### Storage fit

Reuse `documento_interpretativo` with source taxonomy:

- `aepd`
- `resolucion_aepd`
- `guia_aepd`
- `informe_aepd`

### New components

- `apps/workers/aepd.py`
- `apps/api/routers/aepd.py`

### Maintenance model

- weekly or biweekly sync
- explicit distinction between sanction/resolution/guidance
- later bridge to normalized obligations only for guidance with reusable operational duties

## 5. Banco de España

### Why add it

This is one of the most natural next sources after CNMV and SEPBLAC.

It strengthens:

- financial regulation
- reporting duties
- prudential or operational circulars
- supervised entity workflows

### Storage fit

Reuse `documento_interpretativo` for circulars and guidance first.

If a stable hierarchy of official circulars behaves like law in practice, evaluate selective reuse of `norma` later. Do not force that in the first slice.

### New components

- `apps/workers/bde.py`
- `apps/api/routers/bde.py`

### Maintenance model

- weekly sync
- circular-specific canonical reference
- obligation extraction only after corpus quality is stable

## 6. DGSJFP

### Why add it

Useful for:

- registry interpretation
- mercantile practice
- company acts and documentation
- linking public company data with legal interpretation

This is especially complementary to the current `BORME` and `empresa` foundation.

### Storage fit

Reuse `documento_interpretativo`.

### New components

- `apps/workers/dgsjfp.py`
- `apps/api/routers/dgsjfp.py`

### Maintenance model

- weekly sync
- canonical reference normalization
- later cross-linking to `empresa` and `documento_empresa`

## Core normalization work that should run in parallel

Adding sources is not enough. The following shared work must advance alongside ingestion.

## A. Taxonomy hardening

The repo already uses `organismo_emisor`, `tipo_fuente`, `tipo_documento` and `ambito`. These need a stricter shared vocabulary before source count grows too much.

Recommended next step:

- create a documented controlled vocabulary for:
  - `tipo_fuente`
  - `tipo_documento`
  - `ambito`
  - `estado_vigencia`
  - `tipo_obligacion`

This can live first as docs + tests before becoming DB constraints.

## B. Document chunking

This is already identified in the current regulatory plan and should remain a top shared investment.

Add later-stage support for:

- `documento_fragmento`
- `documento_seccion`
- `documento_anexo`

This is what will make obligation extraction and grounded answers much better.

Without chunking:

- the system can index documents
- the system struggles to point precisely to the operative section

With chunking:

- obligations become more defensible
- UI and API responses become more actionable
- AI consumers get much better grounding

## C. Obligation normalization

The current `obligacion_regulatoria` slice should evolve into a more operational model.

Minimum recommended additions over time:

- `trigger_evento`
- `fecha_inicio_computo`
- `plazo`
- `canal_presentacion`
- `evidencia_requerida`
- `riesgo_incumplimiento`
- `sancion_referencia`
- `empresa_tipo_objetivo`

This should expand source by source, not as a big-bang redesign.

## Recommended implementation order

## Wave 1: highest ROI with lowest architectural risk

1. expand `BOE` regulatory corpus
2. implement filtered `CENDOJ`
3. implement `EUR-Lex` worker

Reason:

- this strengthens the legal core immediately
- reuses the current architecture cleanly
- improves both fiscal and regulatory depth
- does not depend on user-facing product redesign

## Wave 2: operational compliance layer

4. expand `CNMV` from initial slice to richer corpus
5. expand `SEPBLAC` from initial slice to richer corpus
6. add `Banco de España`
7. add `AEPD`

Reason:

- this creates the strongest compliance moat
- it composes naturally with `obligacion_regulatoria`
- it makes the product useful for regulated-company workflows, not only legal research

## Wave 3: adjacent public-law and corporate support

8. add `DGSJFP`
9. add `CNMC`
10. consider `ITSS` only if employment compliance becomes a clear product axis

## Required repo changes by category

## Workers

Likely additions:

- `apps/workers/cendoj.py`
- `apps/workers/eurlex.py`
- `apps/workers/aepd.py`
- `apps/workers/bde.py`
- `apps/workers/dgsjfp.py`

Likely extensions:

- `apps/workers/boe.py`
- `apps/workers/cnmv.py`
- `apps/workers/sepblac.py`

For each new worker, also add:

- source-specific tests under `apps/workers/tests/`
- env variables in `.env.example`
- prod env variables in `infra/deploy/compose.env.example`
- service and cron entries in `infra/deploy/docker-compose.prod.yml`
- deployment wiring in `.github/workflows/deploy.yml`
- status reporting in API
- smoke checks in `scripts/smoke-check.py`

## API

Likely new routers:

- `jurisprudencia`
- `ue` if separated from generic legislation
- `aepd`
- `bde`
- `dgsjfp`

Likely shared additions:

- stronger filter model for source, body, court, type, vigency, date range
- normalized response fragments for obligation-backed endpoints
- optional aggregate search endpoint that can span legislation, doctrine, jurisprudence and regulatory documents

## Database

Short term:

- keep reusing `norma` and `documento_interpretativo`
- add bridge tables where source semantics need relations

Medium term:

- add chunking tables
- add stronger obligation fields
- consider dedicated judicial metadata table only if `CENDOJ` complexity makes `documento_interpretativo` too overloaded

## Operations and maintenance

Each new source needs an explicit maintenance contract.

That contract should define:

- ingestion cadence
- canonical identifier strategy
- deduplication strategy
- retry policy
- source breakage detection
- expected freshness SLA
- manual backfill procedure

Recommended default cadence:

| Source | Cadence |
|---|---|
| `BOE` live norms | daily |
| `DGT` | weekly |
| `TEAC` | weekly |
| `CENDOJ` filtered corpus | weekly |
| `EUR-Lex` | weekly |
| `CNMV` | weekly |
| `SEPBLAC` | weekly |
| `AEPD` | weekly or biweekly |
| `Banco de España` | weekly |
| `DGSJFP` | weekly |

## Minimum verification checklist per new source

Before a source is declared live, verify:

1. canonical reference is stable
2. upsert is idempotent
3. source URL is stored
4. `sync_log` shows per-run outcome
5. at least one smoke-check endpoint exists
6. the source appears in `/status`
7. API response includes enough metadata to explain provenance
8. search and detail endpoints behave correctly with empty results and partial corpus
9. at least one real-source fixture or recorded example exists in tests

## What should not be done yet

Avoid these until the corpus is denser:

- building a broad horizontal legal product surface
- mixing private customer documents into the public corpus model
- creating a generic AI chat layer before the source graph is stronger
- over-normalizing obligations from low-quality or weakly structured sources

## Concrete next session plan

The next execution block should be:

1. write a source-manifest for Wave 1
2. extend BOE coverage with the next regulatory texts that fit the existing norm pipeline
3. scaffold `worker-cendoj` and `jurisprudencia` router
4. scaffold `worker-eurlex`
5. harden controlled vocabularies for source/type/ambit/vigency
6. extend smoke checks and status reporting

If the goal is to maximize competitive strength in fiscal and regulatory coverage, this order is better than adding more UI first.

## Outcome if this roadmap is executed well

If the roadmap is followed, `esdata` does not become a generic legal assistant.

It becomes something more defensible:

- a fiscal and regulatory data engine for Spain
- grounded in official public sources
- traceable to article, resolution, circular or manual section
- reusable by APIs, internal copilots and external products
- hard to replicate quickly without building the same ingestion and normalization stack
