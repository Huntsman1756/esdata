# esdata - Sprint M: MiCA CASP

Pattern: Ralph - one story per iteration, fresh context each time.
Runner: OpenCode.
Prerequisite: main=v1.11.0, 3131 passed, 174/174 verified.
Decision: Sprint M covers only perfil `casp`; `emisor_token` is deferred to Sprint N.

You are a senior regulatory data engineer specializing in MiCA, Regulation (EU) 2023/1114 on Markets in Crypto-Assets, and its delegated acts for Crypto-Asset Service Providers (CASP).

MiCA applies fully from 30 December 2024. In Spain, the transitional period for existing PSAV ends on 30 December 2025. The principal CASP supervisor is CNMV.

## Current DB State

- `MICA_2023_1114` exists with no CELEX and no `tipo_norma`.
- Canonical `32023R1114` does not exist.
- `perfil_entidad.codigo='casp'` does not exist.
- MiCA CASP obligations in `obligacion_perfil`: 0 rows.
- MiCA RTS/ITS loaded for CASP: 0 rows.

## Sprint Scope

1. Clean `MICA_2023_1114` into canonical `32023R1114`.
2. Create perfil `casp` in `perfil_entidad`.
3. Map base MiCA obligations for CASP.
4. Load 2-3 confirmed MiCA RTS/ITS for CASP, targeting three if verified.
5. Add fail-closed MCP behavior for missing crypto catalog data.

## CASP Context

A CASP under MiCA arts. 3.1.16 and 59 is a legal person providing one or more crypto-asset services, including custody, trading platform operation, exchange, order execution, placement, reception/transmission of orders, advice, and portfolio management.

Key CASP obligations:

- art. 59: authorization as CASP before providing services.
- art. 62: authorization application information, developed by RTS `32025R0305` and ITS `32025R0306`.
- art. 65: capital requirements by service type.
- arts. 66-67: governance, good repute, knowledge and experience.
- art. 70: custody and segregation of client assets.
- art. 72: complaints handling.
- art. 73: conflicts of interest.
- art. 76: order book, where trading-platform service applies.
- art. 81: continuity and regularity, developed by RTS `32025R0299`.
- art. 82: ICT security, linked to DORA where applicable.
- art. 83: crypto market abuse detection and prevention.
- art. 94: AML/CFT obligations by reference to AML framework.

## CELEX Verification

Before loading any RTS/ITS, verify from VPS:

```bash
curl -o /dev/null -s -w "%{http_code}" \
  "https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:XXXXX"

curl -s "https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:XXXXX" \
  | grep -oi '2023/1114\|criptoactivos\|CASP\|activos virtuales' \
  | head -3
```

Load only if HTTP status is 200 and content confirms MiCA/CASP relevance.

### EUR-Lex WAF Note

EUR-Lex can return `202 Accepted` plus a WAF challenge for plain `curl`.
If all candidates return `202` instead of `200`, use these alternatives before rejecting:

Alternative 1 - `curl` with browser-like headers:

```bash
curl -s -o /dev/null -w "%{http_code}" \
  -H "User-Agent: Mozilla/5.0 (compatible; esdata-verify/1.0)" \
  -H "Accept: text/html" \
  -L --max-redirs 3 \
  "https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32025R0305"
```

Alternative 2 - verify through `data.europa.eu`, which is preferred when EUR-Lex returns WAF:

```bash
curl -s "https://data.europa.eu/eli/reg_del/2025/305/spa" \
  | grep -oi 'criptoactivos\|2023/1114\|CASP' | head -3
```

Alternative 3 - verify through BOE Spanish DOUE mirror when a concrete DOUE id is known:

```bash
curl -s "https://www.boe.es/buscar/doc.php?id=DOUE-L-2025-XXXXX" \
  | grep -oi 'criptoactivos\|MiCA\|2023/1114' | head -3
```

If no alternative returns verifiable content, document the candidate in `docs/sprint-m-mica-report.md` as `CELEX no verificable automaticamente - verificacion manual requerida`, mark M-04 with `0 RTS cargados`, and only then mark PASS. Do not load any CELEX without content verification.

Priority candidates:

- `32025R0305` - RTS solicitud autorizacion CASP, art. 62.
- `32025R0306` - ITS plantillas solicitud autorizacion CASP.
- `32025R0299` - RTS continuidad y regularidad servicios CASP, art. 81.
- `32025R0304` - already returned HTTP 200; confirm MiCA content.
- `32025R0300` - RTS intercambio informacion autoridades.

Do not load:

- `32024R1681` - non-MiCA construction-products regulation.
- `32024R2656` - not accepted for Sprint M unless independently proven MiCA by source content; current rule is no load.

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

## Hard Rules

- All DB access must go through `docker compose exec postgres psql`.
- Never use host Python for DB writes.
- Docker services relevant to verification are `api` and `ops`; there is no service named `worker`.
- VPS has internet access; verify every CELEX with `curl` before inserting.
- `verified=true` requires loaded norma, confirmed article, and resolving `source_url`.
- `source_url` is mandatory on every seeded obligation row.
- If RTS candidates fail source/content checks, document the rejection and keep the data honest.
- Do not create `emisor_token` in Sprint M; document it as Sprint N.
