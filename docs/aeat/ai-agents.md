# AEAT AI agents

This document defines how agentic assistants such as Hermes may help with AEAT
campaign curation.

## Role

AI agents are documentary copilots. They may collect, compare and summarize
official evidence, but they are not fiscal decision makers.

## Allowed actions

Agents may:

- call read-only MCP/API tools;
- inspect `docs/aeat/precision-contract.md` and `docs/aeat/curation-rules.md`;
- review official-source payloads for one model at a time;
- generate draft reports under `reports/aeat-campaign-curation/<modelo>.md`;
- recommend one of `resolved_strong`, `resolved_weak`, `conflict`,
  `insufficient_evidence` or `stale_suspected` as a draft conclusion;
- write `UNKNOWN` when direct official evidence is absent or ambiguous.

## Forbidden actions

Agents must not:

- write to the database;
- run migrations;
- deploy to VPS or production;
- modify `modelo_campana`, `modelo_recurso` or assertion fields;
- decide `resolved_strong` or `ASSERTABLE_DIRECT_OFFICIAL`;
- promote campaigns in bulk;
- use BOE publication date, file name, XSD/WSDL version, endpoint, manual
  version or internal resource association as strong evidence by itself.

## Local Hermes pilot

The first Hermes experiment must run locally, not on the VPS.

Suggested profile:

```text
hermes-esdata-curator
```

Suggested local MCP target:

```text
http://host.docker.internal:8010/mcp
```

Expose only read-only model tools, for example:

```yaml
mcp_servers:
  esdata:
    url: "http://host.docker.internal:8010/mcp"
    headers:
      X-API-Key: "<local-api-key>"
    timeout: 180
    connect_timeout: 60
    tools:
      include:
        - list_modelos
        - get_modelo
        - get_modelo_fuentes_oficiales
        - get_modelo_artefactos
        - get_modelo_resumen_operativo
        - buscar_modelos_aeat_catalogo
      resources: false
      prompts: false
    sampling:
      enabled: false
```

## Pilot acceptance criteria

The first pilot should review `124` and `210`.

Each report must:

- cite the ESData fields used (`campana_safe_to_assert`,
  `campana_assertion_code`, `campana_afirmable`, `campana_resolution_status`);
- cite official-source URLs returned by ESData;
- distinguish official evidence from internal inference;
- return `UNKNOWN` when no direct official model-to-exercise evidence is found;
- avoid phrases such as "la campana activa es X" unless the assertion contract
  is satisfied and a human has accepted the curation.

No agent output is allowed to change production state. Human review remains the
only path to promotion.
