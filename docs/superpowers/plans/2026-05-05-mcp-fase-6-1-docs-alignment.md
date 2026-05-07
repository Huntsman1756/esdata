# MCP Fase 6.1 Docs Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align the active documentation so readers can clearly distinguish REST/OpenAPI, HTTP MCP, and stdio MCP without changing runtime behavior.

**Architecture:** This is a docs-only slice. Keep `docs/manual-usuario/06-api-y-ejemplos.md` REST-only, keep `docs/manual-usuario/07-mcp-y-clientes.md` MCP-only with an explicit HTTP vs stdio split, keep `docs/integrations/opencode-local-and-vps.md` scoped to OpenCode over HTTP MCP, and update `docs/architecture.md` to describe the three surfaces as architectural facts.

**Tech Stack:** Markdown, grep-based doc verification, roadmap bookkeeping

---

## File Map

- Modify: `docs/architecture.md`
  Clarify the three integration surfaces without turning the document into a how-to guide.
- Modify: `docs/manual-usuario/06-api-y-ejemplos.md`
  Remove `/mcp` from REST chapter framing and add a short pointer to chapter `07` for MCP.
- Modify: `docs/manual-usuario/07-mcp-y-clientes.md`
  Tighten the HTTP MCP vs stdio MCP split and keep user-facing MCP guidance there.
- Modify: `docs/integrations/opencode-local-and-vps.md`
  Keep the guide explicitly scoped to OpenCode consuming HTTP MCP over URL.
- Modify: `docs/master-execution-roadmap.md`
  Keep `6.1` claimed during execution, then close it with evidence and set `6.2` as next step.

### Task 1: Reframe `docs/architecture.md`

**Files:**
- Modify: `docs/architecture.md`

- [ ] **Step 1: Locate the integration-surface section to update**

Run: `python -c "from pathlib import Path; p=Path(r'docs/architecture.md'); text=p.read_text(encoding='utf-8'); start=text.index('## Superficies MCP actuales'); print(text[start:start+900])"`
Expected: the current MCP-focused section is printed, showing `HTTP MCP` and `stdio MCP` but not yet a top-level three-surface framing.

- [ ] **Step 2: Edit the section to introduce the three active integration surfaces**

Use this target structure inside `docs/architecture.md`:

```md
## Superficies de integracion activas

`esdata` mantiene hoy tres superficies de integracion distintas:

### REST/OpenAPI `[IMPLEMENTED]`

- expone endpoints HTTP versionables del backend FastAPI
- es la superficie mas estable para integraciones backend/app, automatizaciones y clientes no MCP
- su contrato operativo debe consultarse en `openapi.json` y en el manual REST

### HTTP MCP `[IMPLEMENTED]`

- se monta en `/mcp`
- usa `FastApiMCP` sobre operaciones HTTP reales del backend
- el catalogo activo vive en `apps/api/mcp_catalog.py` bajo `HTTP_MCP_OPERATIONS`

### stdio MCP `[IMPLEMENTED]`

- vive en `apps/api/mcp_stdio.py`
- expone tools de mas alto nivel orientadas a clientes locales via proceso hijo
- su catalogo no coincide con `HTTP_MCP_OPERATIONS`

Regla de arquitectura:

- no tratar REST, HTTP MCP y stdio MCP como una sola interfaz
- no tratar HTTP MCP y stdio MCP como un catalogo compartido
```

- [ ] **Step 3: Read back the edited section**

Run: `python -c "from pathlib import Path; p=Path(r'docs/architecture.md'); text=p.read_text(encoding='utf-8'); start=text.index('## Superficies de integracion activas'); print(text[start:start+1300])"`
Expected: the section now names `REST/OpenAPI`, `HTTP MCP`, and `stdio MCP` explicitly.

- [ ] **Step 4: Commit**

```bash
git add docs/architecture.md
git commit -m "docs(architecture): separate rest and mcp surfaces"
```

### Task 2: Make chapter `06` REST-only

**Files:**
- Modify: `docs/manual-usuario/06-api-y-ejemplos.md`

- [ ] **Step 1: Confirm the current MCP leak inside chapter `06`**

Run: `python -c "from pathlib import Path; p=Path(r'docs/manual-usuario/06-api-y-ejemplos.md'); lines=p.read_text(encoding='utf-8').splitlines(); print('\n'.join(f'{i+1}: {line}' for i,line in enumerate(lines) if '/mcp' in line or 'MCP' in line))"`
Expected: output includes the `/mcp` row currently listed in the chapter table.

- [ ] **Step 2: Remove `/mcp` from the REST chapter framing and add a pointer to chapter `07`**

Use this target wording near the surface table and examples:

```md
| Endpoint | Que busca | Ejemplo |
|---|---|---|
| `/v1/consulta` | Legislacion + modelos, con grounding y abstencion | `?q=tipo+reducido+IVA` |
| `/v1/buscar` | Legislacion indexada unicamente | `?q=prescripcion+LGT` |
| `/v1/modelos/` | Modelos tributarios (303, 349, 100...) | `/v1/modelos/303` |

## MCP

La integracion MCP se documenta aparte en `07-mcp-y-clientes.md`.
Este capitulo se limita a `REST/OpenAPI`.
```

- [ ] **Step 3: Ensure protected operational examples stay coherent**

While editing, keep `status` examples aligned with the active protected endpoint contract. Use this form if the current file needs correction:

```bash
curl -s -H "X-API-Key: $ESDATA_API_KEY" http://127.0.0.1:8000/status
```

- [ ] **Step 4: Read back the edited chapter header and examples block**

Run: `python -c "from pathlib import Path; p=Path(r'docs/manual-usuario/06-api-y-ejemplos.md'); print(p.read_text(encoding='utf-8')[:2200])"`
Expected: no `/mcp` surface row remains in the REST chapter, and MCP is pointed to chapter `07` instead.

- [ ] **Step 5: Commit**

```bash
git add docs/manual-usuario/06-api-y-ejemplos.md
git commit -m "docs(manual): keep api chapter rest only"
```

### Task 3: Tighten chapter `07` around HTTP MCP vs stdio MCP

**Files:**
- Modify: `docs/manual-usuario/07-mcp-y-clientes.md`

- [ ] **Step 1: Read the current split and note ambiguous wording**

Run: `python -c "from pathlib import Path; p=Path(r'docs/manual-usuario/07-mcp-y-clientes.md'); print(p.read_text(encoding='utf-8'))"`
Expected: the file shows both surfaces but still contains wording like `MCP` in generic terms that can be tightened.

- [ ] **Step 2: Rewrite the opening so the split is explicit from the first screenful**

Use this target opening structure:

```md
## Que es MCP en esdata

`esdata` no expone una unica superficie MCP.
Hoy existen dos superficies MCP distintas y no intercambiables:

- `HTTP MCP` montado en `/mcp`
- `stdio MCP` implementado en `apps/api/mcp_stdio.py`

Regla base:

- `HTTP MCP` y `stdio MCP` no comparten catalogo
- una integracion debe indicar explicitamente cual de las dos consume
```

- [ ] **Step 3: Keep HTTP and stdio catalog differences concrete**

Ensure the chapter still states these facts after editing:

```md
- `HTTP MCP` expone operaciones REST estructuradas definidas en `HTTP_MCP_OPERATIONS`
- `stdio MCP` expone tools de mas alto nivel como `consulta_fiscal` y `agente_consulta`
- una tool visible en stdio no debe asumirse presente en HTTP MCP
```

- [ ] **Step 4: Remove test-only or low-level implementation detail that does not help the reader**

Delete or shorten wording like this if still present in the user-facing chapter:

```md
- en tests de transporte HTTP, `MCP` debe montarse sobre una instancia fresca creada con `create_app()`
```

Keep only runtime/security details useful to an operator or integrator.

- [ ] **Step 5: Read back the first 140 lines after editing**

Run: `python -c "from pathlib import Path; p=Path(r'docs/manual-usuario/07-mcp-y-clientes.md'); lines=p.read_text(encoding='utf-8').splitlines(); print('\n'.join(f'{i+1}: {line}' for i,line in enumerate(lines[:140])))"`
Expected: the split is explicit up front, and the chapter does not imply a shared MCP catalog.

- [ ] **Step 6: Commit**

```bash
git add docs/manual-usuario/07-mcp-y-clientes.md
git commit -m "docs(manual): clarify http and stdio mcp"
```

### Task 4: Keep the OpenCode guide strictly HTTP-only

**Files:**
- Modify: `docs/integrations/opencode-local-and-vps.md`

- [ ] **Step 1: Confirm the current HTTP-only boundary markers**

Run: `python -c "from pathlib import Path; p=Path(r'docs/integrations/opencode-local-and-vps.md'); print(p.read_text(encoding='utf-8'))"`
Expected: the file already says it covers `HTTP MCP`, but the exclusion of `stdio` can be made more prominent.

- [ ] **Step 2: Strengthen the scope statement and practical rule**

Use this target wording near the scope section:

```md
Esta guia cubre solo `OpenCode` contra `HTTP MCP` montado en `/mcp`.

No cubre `stdio MCP` ni ninguna tool disponible solo a traves de `apps/api/mcp_stdio.py`.

Regla practica:

- `OpenCode` configurado con URL remota o local -> usa `HTTP MCP`
- si necesitas `stdio`, eso pertenece a otra integracion y a otra documentacion
```

- [ ] **Step 3: Keep examples consistent with HTTP MCP and `MCP_API_KEY`**

Ensure examples still match this shape:

```bash
curl -i -H "Accept: text/event-stream" -H "X-API-Key: $MCP_API_KEY" http://127.0.0.1:8000/mcp
```

and this config shape:

```json
{
  "mcp": {
    "esdata": {
      "type": "remote",
      "url": "https://api.example.internal/mcp",
      "headers": {
        "X-API-Key": "{env:ESDATA_MCP_API_KEY}"
      }
    }
  }
}
```

- [ ] **Step 4: Read back the scope and configuration sections**

Run: `python -c "from pathlib import Path; p=Path(r'docs/integrations/opencode-local-and-vps.md'); text=p.read_text(encoding='utf-8'); start=text.index('## Alcance exacto de esta guia'); end=text.index('## Buenas practicas'); print(text[start:end])"`
Expected: the guide is unmistakably HTTP-only and does not blur into stdio guidance.

- [ ] **Step 5: Commit**

```bash
git add docs/integrations/opencode-local-and-vps.md
git commit -m "docs(integrations): scope opencode to http mcp"
```

### Task 5: Close `6.1` in the roadmap with evidence

**Files:**
- Modify: `docs/master-execution-roadmap.md`

- [ ] **Step 1: Run the planned doc verification commands**

Run these exact commands from repo root:

```bash
python -c "from pathlib import Path; print('ok architecture' if '## Superficies de integracion activas' in Path(r'docs/architecture.md').read_text(encoding='utf-8') else 'missing architecture section')"
python -c "from pathlib import Path; text=Path(r'docs/manual-usuario/06-api-y-ejemplos.md').read_text(encoding='utf-8'); print('/mcp' if '/mcp' in text else 'no /mcp')"
python -c "from pathlib import Path; text=Path(r'docs/manual-usuario/07-mcp-y-clientes.md').read_text(encoding='utf-8'); print('HTTP_MCP_OPERATIONS' if 'HTTP_MCP_OPERATIONS' in text else 'missing http catalog ref'); print('consulta_fiscal' if 'consulta_fiscal' in text else 'missing stdio tool ref')"
python -c "from pathlib import Path; text=Path(r'docs/integrations/opencode-local-and-vps.md').read_text(encoding='utf-8'); print('OpenCode HTTP only' if 'Esta guia cubre solo `OpenCode` contra `HTTP MCP` montado en `/mcp`.' in text else 'scope text differs')"
```

Expected:

- first command prints `ok architecture`
- second command should show no stray `/mcp` in chapter `06` beyond an intentional pointer if you kept one in prose; if it still prints `/mcp`, manually confirm it is not teaching MCP as part of the REST chapter surface table
- third command prints both `HTTP_MCP_OPERATIONS` and `consulta_fiscal`
- fourth command confirms the HTTP-only scope sentence or a semantically equivalent final wording you can cite in the roadmap

- [ ] **Step 2: Read back the live roadmap summary before editing it**

Run: `python -c "from pathlib import Path; p=Path(r'docs/master-execution-roadmap.md'); lines=p.read_text(encoding='utf-8').splitlines(); print('\n'.join(f'{i+1}: {line}' for i,line in enumerate(lines[215:224], start=216)))"`
Expected: `6.1` is still marked `[EN CURSO]` with the current claim line.

- [ ] **Step 3: Update the roadmap live summary and add a historical closeout note**

Use this target structure in `docs/master-execution-roadmap.md`:

```md
- Objetivo actual: preparar **Fase 6.2** ...
- Estado actual: **Fase 6.1** `[COMPLETA]` ...
- Reclamo actual: ninguno. **Fase 6.1** queda cerrada ...
- Siguiente paso exacto: reclamar y ejecutar **Fase 6.2** ...
```

and add a historical note that cites the edited files and the doc-verification evidence.

- [ ] **Step 4: Read back the updated summary and historical note**

Run: `python -c "from pathlib import Path; p=Path(r'docs/master-execution-roadmap.md'); lines=p.read_text(encoding='utf-8').splitlines(); print('\n'.join(f'{i+1}: {line}' for i,line in enumerate(lines[215:245], start=216)))"`
Expected: `6.1` reads as complete, no active claim remains, and `6.2` is the only next step.

- [ ] **Step 5: Commit**

```bash
git add docs/master-execution-roadmap.md
git commit -m "docs(roadmap): close mcp phase 6.1"
```

## Self-Review Checklist

- Spec coverage: all approved files are covered by Tasks 1-5, and the plan keeps the scope docs-only.
- Placeholder scan: no `TODO`, `TBD`, or vague `fix later` language remains.
- Type consistency: the plan consistently uses `REST/OpenAPI`, `HTTP MCP`, `stdio MCP`, `HTTP_MCP_OPERATIONS`, and `OpenCode` with the same meanings across tasks.
