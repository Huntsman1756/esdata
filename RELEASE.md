## esdata MCP v1.0.0

Release date: 2026-05-13

### What This MCP Can Be Trusted To Answer

The MCP can answer authoritatively only when the response contract marks the data as verified and complete for the requested domain.

Verified live domains in v1.0.0:

| Domain | Trusted surface |
| --- | --- |
| AEAT modelos | Model metadata and loaded official casillas/campos for models whose response returns `verified=true` and `completeness=completa`. Model 100 casillas are paginated and verified as official fields, not as obligatory fields for a taxpayer scenario. |
| AEAT no-casillas forms | Models marked `verified=true` and `completeness=no-casillas-expected` are treated as declaration or communication forms where ESData has verified that no structured casilla set is expected from the loaded source. |
| BOE consolidated legislation | Loaded consolidated articles for the supported legal corpus, with `boe_reference` or `source_url` in responses. |
| DGT doctrina | Loaded DGT consultas with traceable `numero_consulta`, date, issuing body and source URL. |
| CNMV | Loaded CNMV circulars/documents with title, publication date and official CNMV or BOE trace. |
| EUR-Lex MiFID II | MiFID II articulado loaded under CELEX `32014L0065` where article text is present. |
| AEPD | Loaded AEPD documents with title, date and official AEPD source URL. |
| MiCA / ESMA CASP | CASP register rows loaded from the official ESMA register, with official-register quality signal. |

### What This MCP Answers With Limited Evidence

These domains are intentionally conservative. They may return useful official references, but callers must not treat them as complete procedural or legal answers:

| Domain | Contract |
| --- | --- |
| AEAT modelos with `completeness=parcial` | `verified=false`; responses must say `evidence_limited` and must not invent missing casillas or filing instructions. |
| FATCA / CRS | Limited to loaded official references and model metadata. Complete filing procedure, affected-client taxonomy, thresholds and XML submission rules remain `evidence_limited` unless the specific response cites loaded official evidence. |
| BORME | Partial and heuristic. It is not definitive mercantile registry evidence. |
| EUR-Lex entries without articulado | Metadata-only entries return limited evidence and must not synthesize article text. |
| Model applicability by business scenario | For examples such as a Spanish sociedad de valores with resident and non-resident clients, ESData returns candidates only when evidence is limited. It must not claim obligatory filing unless explicit loaded evidence supports it. |

### What This MCP Does Not Cover

- Legal advice, tax advice or final compliance decisions.
- Real-time AEAT filing validation or presentation through AEAT systems.
- Complete procedural guidance for FATCA/CRS filing.
- Definitive mercantile registry data from BORME.
- AEPD sanction-resolution corpus when not loaded.
- Configured-but-empty domains such as UCITS/AIFMD/CRD/IDD/XBRL surfaces until official data is loaded.
- AEAT STATUS-D models where the official source is a dynamic endpoint, FAQ, example XML, schematic PDF or other non-deterministic source that cannot be parsed safely.
- Sanctions screening beyond the loaded corpus.

### Response Contracts

This MCP uses explicit response contracts so callers always know the confidence level of an answer:

| Contract value | Meaning |
| --- | --- |
| `verified=true`, `completeness=completa` | Authoritative for the loaded data. Data comes from an official source and passed the ESData validation contract. |
| `verified=true`, `completeness=no-casillas-expected` | Authoritative absence of structured casillas for that model/form in the loaded source. |
| `verified=true`, `completeness=deprecated` | Authoritative statement that the model is no longer current, when backed by loaded evidence. |
| `verified=false`, `completeness=parcial` | Limited evidence only. Do not treat as authoritative for missing fields, filing procedure, obligatoriedad or applicability. |
| `evidence_limited` | The system found partial evidence but not enough to answer the full claim safely. |
| `configured_but_unavailable` | The domain is known and exposed, but no real source data is loaded yet. |
| `workflow_empty` | The table is empty by current workflow state and the MCP must fail closed. |
| `allowed_empty` | Empty is an accepted operational state for that domain. |

### Security And Operations

- GitHub Dependabot critical/high alerts are closed for v1.0.0.
- The VPS release posture uses a non-root `deploy` user, root SSH login disabled, key-only SSH, active UFW and active fail2ban.
- Backup restore was tested into a non-production database before release.
- `query_audit_log` is append-only and retrieval/MCP endpoints are expected to write audit entries.
- Prometheus/Alertmanager are active; Telegram alerts have been verified in production.

### Validation Evidence

- Full local regression gate for the release merge: 2995 passed, 2 skipped.
- Post-deploy `mcp_validation_suite.py --read-only`: `ok=true`.
- Post-deploy `/status`: `api=ok`, `database=ok`, `stale_workers_count=0`.
- Post-deploy Alertmanager active alerts: 0.
- Accuracy sprint final score: 57 queries tested, 38 correct, 19 honest-limit, 0 incorrect, 100% confidence over verified answers.

### Known Limitations

ESData v1.0.0 is built to be honest before it is broad. A limited response is a correct response when the loaded corpus does not prove the requested claim. Critical legal, tax or compliance decisions must still be verified against official sources such as AEAT, BOE, CNMV, AEPD, ESMA and EUR-Lex.
