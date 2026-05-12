# ESData Accuracy Report

Fecha: 2026-05-12

Alcance: sprint Ralph Q-01 a Q-14. El indicador mide solo respuestas que el sistema presenta como verificadas/autoritativas. Las respuestas `honest_limit` no penalizan: son correctas si el MCP/API declara evidencia limitada y no inventa.

| domain | queries | correct | honest_limit | incorrect | confidence% |
|---|---:|---:|---:|---:|---:|
| AEAT modelos | 11 | 3 | 8 | 0 | 100 |
| BOE legislacion consolidada | 5 | 5 | 0 | 0 | 100 |
| BOE search/ranking | 5 | 5 | 0 | 0 | 100 |
| BORME | 1 | 0 | 1 | 0 | N/A |
| EUR-Lex / MiFID II | 3 | 1 | 2 | 0 | 100 |
| DGT doctrina | 2 | 2 | 0 | 0 | 100 |
| CNMV | 2 | 2 | 0 | 0 | 100 |
| MiCA / ESMA | 6 | 2 | 4 | 0 | 100 |
| AEPD | 3 | 3 | 0 | 0 | 100 |
| FATCA / CRS | 4 | 0 | 4 | 0 | N/A |
| Cross-domain routing | 5 | 5 | 0 | 0 | 100 |
| Audit trail | 6 | 6 | 0 | 0 | 100 |
| Observability | 4 | 4 | 0 | 0 | 100 |

Overall verified-answer confidence: 100% (38 correct / 38 correct+incorrect).

## Evidence Summary

- AEAT modelos: Q-01/Q-02 verified detail endpoints expose `verified`, `completeness`, `casillas_total` and evidence notices. Partial models such as 289/290 stay `evidence_limited`; no-casillas models such as 102/146/247 state that no structured casillas are expected.
- BOE legislacion: Q-03 checked LIVA art. 1/4, LGT art. 1, LIRPF art. 1 and LIS art. 1 against official consolidated BOE references.
- BOE search: Q-04 fixed and verified deterministic ranking for LIVA art. 90 and LIS art. 10, with `boe_reference`/`source_url`.
- BORME: Q-05 returns official BOE/BORME documents but marks extraction as `partial_heuristic`, so it is an honest limited answer, not authoritative mercantile registry truth.
- EUR-Lex: Q-06/Q-12 returns MiFID II `MIFID2_2014_65` with real article text and CELEX `32014L0065`; metadata-only EUR-Lex entries remain limited.
- DGT: Q-07 returns traceable DGT/PETETE consulta data with `numero_consulta`, `fecha`, `organo` and official URL.
- CNMV: Q-08 returns CNMV circular/document metadata with BOE/CNMV traceability and no ESMA/MiCA substitution.
- MiCA / ESMA: Q-09 returns real CASP ESMA register data where loaded and explicit unavailable envelopes for empty MiCA tables.
- AEPD: Q-10 returns 25 official AEPD documents with `url_aepd`; search is accent/token tolerant and does not substitute BOE legislation.
- FATCA / CRS: Q-11 correctly abstains for procedure-complete questions when ESData only has partial 289/290/reference evidence.
- Cross-domain: Q-12 verified `tipo IVA`, `modelo 303`, `circular CNMV`, `MiFID II articulo 1` and `RGPD AEPD` route to the intended domains.
- Audit trail: Q-13 verified `query_audit_log` rows for six retrieval endpoints and append-only UPDATE blocking.
- Observability: Q-14 verified 0 FIRING alerts, `stale=[]`, and every active worker has recent `sync_log`.

## Residual Risk

- `confidence% = N/A` means there were no authoritative verified answers in that domain during the sprint; the correct behavior was explicit limitation.
- This report does not claim full legal/tax coverage. It confirms that sampled verified answers match official sources and limited answers are honest.
