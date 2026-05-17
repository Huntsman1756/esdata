# Sprint A Coverage Report: TEAC DYCTEA + SEPBLAC granular

Date: 2026-05-17

Scope: production rows loaded during Sprint A for TEAC DYCTEA, SEPBLAC granular families, and RD 304/2014 as the LPBC-FT regulation. Counts below come from production SQL on the active VPS.

## Production Counts

| Fuente | tipo_documento | COUNT produccion | verified% | Notas |
|---|---:|---:|---:|---|
| TEAC / DYCTEA | `resolucion_teac` | 558 | 51.25% | Official DYCTEA URLs present for 558 rows. Text is complete for 286 rows and partial/metadata-heavy for 272 rows. Do not treat the corpus as all TEAC doctrine. |
| SEPBLAC | `normativa_sepblac` | 7 | 85.71% | Official SEPBLAC normative pages/documents. Contract: regulatory source, but verify primary/secondary rank before treating as primary law. |
| SEPBLAC | `obligacion_sepblac` | 7 | 42.86% | Official SEPBLAC obligation summaries. Contract: operational summaries by subject type, not primary law. 3 rows include `sujeto_obligado` metadata. |
| SEPBLAC | `guia_operativa_sepblac` | 7 | 85.71% | Official SEPBLAC guides/recommendations/publications. Contract: supervisory/operational guidance, not primary law. |
| BOE | `RD_304_2014` in `norma`/`articulo` | 76 articles | n/a | Official BOE source `BOE-A-2014-4742`. Article 4 is exposed via `/v1/legislacion/RD_304_2014/articulos/4`. |

## SQL Evidence

```sql
SELECT tipo_documento, COUNT(*) AS count,
       ROUND(100.0 * COUNT(*) FILTER (WHERE COALESCE(metadata->>'verified','false')='true') / NULLIF(COUNT(*),0), 2) AS verified_pct,
       COUNT(*) FILTER (WHERE row_completeness='complete' OR metadata->>'row_completeness'='completa') AS complete_rows,
       COUNT(*) FILTER (WHERE row_completeness='partial' OR metadata->>'row_completeness'='parcial') AS partial_rows
FROM documento_interpretativo
WHERE tipo_documento IN ('resolucion_teac','normativa_sepblac','obligacion_sepblac','guia_operativa_sepblac')
GROUP BY tipo_documento
ORDER BY tipo_documento;
```

Result:

| tipo_documento | count | verified_pct | complete_rows | partial_rows |
|---|---:|---:|---:|---:|
| `guia_operativa_sepblac` | 7 | 85.71 | 6 | 1 |
| `normativa_sepblac` | 7 | 85.71 | 6 | 1 |
| `obligacion_sepblac` | 7 | 42.86 | 3 | 4 |
| `resolucion_teac` | 558 | 51.25 | 286 | 272 |

```sql
SELECT n.codigo, n.boe_id, COUNT(a.id) AS articulos
FROM norma n
LEFT JOIN articulo a ON a.norma_id=n.id
WHERE n.codigo='RD_304_2014'
GROUP BY n.codigo,n.boe_id;
```

Result:

| codigo | boe_id | articulos |
|---|---|---:|
| `RD_304_2014` | `BOE-A-2014-4742` | 76 |

## Validation Evidence

- Production `mcp_validation_suite.py --read-only --base-url http://api:8000` from the `ops` container with API keys injected -> `ok=true`.
- Production `mcp_deep_contract_audit.py --base-url http://api:8000` from the `ops` container -> `ok=true`.
- The delegated semantic suite inside the deep audit ran 48 checks with 0 failures.

## Contract Notes

- TEAC DYCTEA is now a useful corpus, not a complete official universe. Rows without full parseable text remain partial even when the official URL is present.
- SEPBLAC families must not be collapsed into generic "SEPBLAC documents":
  - `normativa_sepblac`: official regulatory texts or normative source pages.
  - `obligacion_sepblac`: operational obligation summaries by subject; useful for applicability, but not primary law.
  - `guia_operativa_sepblac`: guidance, recommendations and supervisory orientation; not primary law.
- `tipologia_sepblac` remains a target. The prompt source for documentation/tipologies returned 404 during Sprint A and was not loaded.
- RD 304/2014 was loaded from `BOE-A-2014-4742`. The PRD's `BOE-A-2014-5438` was verified as a different royal decree and was not retained.
