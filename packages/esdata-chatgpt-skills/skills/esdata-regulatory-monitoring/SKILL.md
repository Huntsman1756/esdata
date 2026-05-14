---
name: esdata-regulatory-monitoring
description: Produce regulatory monitoring digests and change reviews using ESData MCP evidence for BOE, AEAT, CNMV, DGT, AEPD, ESMA, EUR-Lex, BORME, FATCA/CRS, MiFID II, MiCA, and related compliance domains. Use when the user asks what changed, what to monitor, whether a source is stale, or how to route discovered URLs through verification.
---

# ESData Regulatory Monitoring

Use this skill to turn ESData evidence into a reviewable regulatory digest. It adapts the "reg feed watcher" and "policy gap analysis" patterns while preserving ESData's source contract.

## Source Policy

- Official loaded ESData records can be cited.
- SearXNG or web search can only produce discovery candidates.
- Discovery candidates must go to staging or a worker verification path before being treated as evidence.
- Do not mix BOE diario/BORME heuristic documents with consolidated legislation.

## Workflow

1. Define scope: source, date window, domain, affected entity, and policy/process being checked.
2. Query ESData for source revisions, documents, articles, models, or domain-specific endpoints.
   - For CNMV scope, also query `/v1/cnmv/coverage` to show loaded versus unavailable source families.
   - For EUR-Lex/ESMA markets, distinguish full article/schema coverage from FIRDS pilot metadata.
3. Classify each item:
   - `actionable`: verified source and likely relevant.
   - `watch`: verified source but impact unclear.
   - `discovery_only`: found externally or not loaded/verified.
   - `no_action`: not relevant to the scope.
   - `coverage_gap`: official source family known by ESData but not loaded.
4. Produce a digest with source links and impact hypotheses clearly marked as reasoning.
5. Add owner/review gate for any policy, procedure, filing, or client-facing update.

## Output

```text
Scope:
- dominio:
- ventana:
- entidad/proceso:

Cambios verificados:
| fecha | fuente | item | impacto preliminar | evidencia |

Discovery no verificado:
| url | dominio | razon para verificar | siguiente paso |

Gaps / acciones:
- ...

Gate:
- Ningun cambio entra en corpus productivo ni se comunica como obligatorio sin worker/verificacion oficial.
```

## Current Coverage Traps

- CNMV currently has a partial loaded corpus. Circulares and generic documents are not the full CNMV universe.
- CNMV `vigente_modificado` requires consolidation metadata before being treated as current consolidated text.
- SearXNG/web discovery may identify URLs for staging, but must not be cited as evidence.
- FIRDS full data is a capacity decision; use ESMA schema/validation endpoints for report-structure questions.
