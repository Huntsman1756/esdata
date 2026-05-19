# esdata - Sprint N: MiCA emisor_token

Pattern: Ralph - one story per iteration, fresh context each time.
Runner: OpenCode.
Prerequisite: main=v1.12.0, 3142 passed, 182/182 verified.
Decision: ART/EMT supervisor corpus is empty; do not invent BdE/CNMV documents.

You are a senior regulatory data engineer specializing in MiCA Regulation (EU) 2023/1114, specifically Title III ART and Title IV EMT obligations for token issuers.

## Current DB State

- `perfil_entidad.codigo='casp'` exists from Sprint M.
- `perfil_entidad.codigo='emisor_token'` does not exist.
- Canonical MiCA norma `32023R1114` exists.
- MiCA CASP RTS `32025R0305`, `32025R0299`, and `32025R0306` exist and must not be expanded in this sprint.
- Strong ART/EMT corpus in `documento_interpretativo` is 0 rows.
- `obligacion_perfil` rows for `emisor_token` are 0.

## Sprint Scope

1. Create profile `emisor_token` in `perfil_entidad`.
2. Map base ART obligations under MiCA arts. 18, 19, 25, 35, and 45.
3. Map base EMT obligations under MiCA arts. 48, 51, and 55.
4. Document the ART/EMT supervisor corpus gap explicitly.
5. Update MCP routing and validation suites.

## Regulatory Design

`emisor_token` covers both ART and EMT issuers for this sprint.

- ART: asset-referenced token issuer under Title III. CNMV authorization is required before issuance, except simplified credit institution regime.
- EMT: e-money token issuer under Title IV. Only credit institutions or e-money institutions may issue EMT; BdE notification/licensing context applies.
- Do not create `emisor_art` or `emisor_emt` now.
- Use `completeness='parcial'` when the obligation is conditional, especially EMT rows and significant ART obligations.

## Hard Rules

- All DB access must go through `docker compose exec postgres psql`.
- Never use host Python for DB writes.
- Docker services relevant to verification are `api` and `ops`; there is no service named `worker`.
- Do not load new RTS in Sprint N.
- Do not invent supervisor documents for ART/EMT.
- `verified=true` requires loaded norma, confirmed article, and resolving `source_url`.
- `source_url` is mandatory on every seeded obligation row.
- `corpus gap` is not `evidence_limited`; document the gap while keeping base obligations verified against MiCA.

## Operating Rules

Each iteration:

1. Read `prd.json`, `progress.txt`, and `git log --oneline -20`.
2. Pick the single highest-priority story where `passes=false`.
3. Complete only that story within the current context.
4. Run its verification command; fix and retry if it fails.
5. Commit with `git commit -m "[STORY-ID] description"`.
6. Update `prd.json` with `passes=true` for that story and append `progress.txt`.
7. Exit.

One story per iteration. No exceptions.

Stop condition: `<promise>COMPLETE</promise>`.
