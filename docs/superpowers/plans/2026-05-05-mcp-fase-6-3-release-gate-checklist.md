# MCP Fase 6.3 Release Gate Checklist Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a manual MCP release go/no-go runbook that tells an operator exactly which existing checks to run, what evidence to record, and when to declare `GO` or `NO-GO`.

**Architecture:** Keep `6.3` as a documentation-only slice. Create one new runbook in `docs/operations/runbooks/`, claim and close the phase in `docs/master-execution-roadmap.md`, and base the checklist only on commands and gates that already exist today in the repo.

**Tech Stack:** Markdown, existing repo commands, roadmap bookkeeping

---

## File Map

- Create: `docs/operations/runbooks/mcp-release-gate.md`
  Manual release go/no-go checklist for MCP using only existing checks and commands.
- Modify: `docs/master-execution-roadmap.md`
  Claim `6.3` before drafting the runbook and close it with fresh readback evidence after the runbook is in place.

### Task 1: Claim `Fase 6.3` in the roadmap

**Files:**
- Modify: `docs/master-execution-roadmap.md`

- [ ] **Step 1: Read the live summary block before editing**

Run:

```bash
python -c "from pathlib import Path; p=Path(r'docs/master-execution-roadmap.md'); lines=p.read_text(encoding='utf-8').splitlines(); print('\n'.join(f'{i+1}: {line}' for i,line in enumerate(lines[216:224], start=217)))"
```

Expected: the block shows `Fase 6.2` closed and `Fase 6.3` as the next pending step.

- [ ] **Step 2: Update the summary to mark `6.3` as in progress**

Replace the live-summary bullets with this target structure:

```md
- Objetivo actual: ejecutar **Fase 6.3** del plan MCP para crear el checklist go/no-go de release.
- Estado actual: **Fase 5.5** `[COMPLETA]`, **Fase 6.1** `[COMPLETA]` y **Fase 6.2** `[COMPLETA]` en `G:\_Proyectos\esdata\.worktrees\next-task`; **Fase 6.3** `[EN CURSO]` redacta un runbook manual para decidir `GO` o `NO-GO` sobre readiness MCP usando solo checks existentes.
- Estado del agente activo: diseno y spec de `6.3` aprobados; redaccion del runbook `docs/operations/runbooks/mcp-release-gate.md` en curso.
- Reclamo actual: **Fase 6.3** `[EN CURSO]` - archivos reclamados: `docs/master-execution-roadmap.md`, `docs/operations/runbooks/mcp-release-gate.md`, `docs/superpowers/specs/2026-05-05-mcp-fase-6-3-release-gate-checklist-design.md`, `docs/superpowers/plans/2026-05-05-mcp-fase-6-3-release-gate-checklist.md`. Inicio: 2026-05-05.
- Siguiente paso exacto: redactar el runbook `docs/operations/runbooks/mcp-release-gate.md`, comprobar que todas sus rutas y comandos existen, y cerrar `6.3` dejando `6.4` como siguiente fase.
```

- [ ] **Step 3: Read back the updated summary**

Run:

```bash
python -c "from pathlib import Path; p=Path(r'docs/master-execution-roadmap.md'); lines=p.read_text(encoding='utf-8').splitlines(); print('\n'.join(f'{i+1}: {line}' for i,line in enumerate(lines[216:224], start=217)))"
```

Expected: the block now shows `Fase 6.3` as `[EN CURSO]` with the runbook as the active slice.

- [ ] **Step 4: Commit**

```bash
git add docs/master-execution-roadmap.md
git commit -m "docs(roadmap): claim mcp phase 6.3"
```

### Task 2: Draft the MCP release gate runbook

**Files:**
- Create: `docs/operations/runbooks/mcp-release-gate.md`

- [ ] **Step 1: Confirm the exact live commands and references the runbook should reuse**

Run these exact commands from repo root:

```bash
python -c "from pathlib import Path; print((Path(r'docs/operations/OPERATIONS.md').read_text(encoding='utf-8'))[:2200])"
python -c "from pathlib import Path; print((Path(r'docs/operations/runbooks/deploy-compose.md').read_text(encoding='utf-8'))[:2200])"
python -c "from pathlib import Path; print((Path(r'docs/reference/mcp-remediation-plan.md').read_text(encoding='utf-8'))[350*1:383*1])"
```

Expected: you can confirm the live repo already has `verify-doc-contracts.py`, `apps/api/tests/test_mcp_private.py`, and `verify_schema.py` as reusable pieces for the manual gate.

- [ ] **Step 2: Write `docs/operations/runbooks/mcp-release-gate.md`**

Create the runbook with this target structure and content meaning:

```md
# Runbook: MCP Release Gate

## Objetivo

Checklist manual de go/no-go para decidir si la superficie MCP esta lista para release con base en evidencia local reproducible.

## Alcance

- este gate cubre readiness minima de release MCP
- no sustituye CI completo ni aprobacion integral del producto
- `HTTP MCP` y `stdio MCP` siguen siendo superficies distintas y deben interpretarse como tal

## Preconditions

- worktree limpio o cambios comprendidos
- ejecutar desde la raiz activa del repo
- entorno local preparado para correr comandos Python y pytest del proyecto

## Checks requeridos

### 1. Gate documental

```bash
python scripts/maintenance/verify-doc-contracts.py
```

Interpretacion:

- verde: la separacion `REST/OpenAPI` / `HTTP MCP` / `stdio MCP` y la guia `OpenCode -> HTTP MCP` siguen intactas
- rojo: `NO-GO`

### 2. Regresion MCP privada

```bash
python -m pytest apps/api/tests/test_mcp_private.py -q
```

Interpretacion:

- verde: el transporte MCP privado y sus checks principales siguen en pie
- rojo: `NO-GO`

### 3. Gate estructural de runtime/deploy

```bash
python scripts/maintenance/verify_schema.py
```

Interpretacion:

- verde: el contrato estructural minimo del runtime actual sigue presente
- rojo: `NO-GO`

## Evidencia a registrar

Para cada check registrar:

- comando exacto
- resultado observado
- fecha/hora
- branch, worktree o SHA usado para la decision

## Decision final

### GO

- todos los checks requeridos en verde
- evidencia registrada
- sin ambiguedad abierta sobre boundaries entre `REST/OpenAPI`, `HTTP MCP` y `stdio MCP`

### NO-GO

- cualquier check falla
- cualquier check no puede reproducirse
- cualquier resultado es ambiguo o no deja evidencia suficiente

## Este gate no prueba

- cobertura total de CI
- automatizacion futura de `6.4`
- sign-off integral del producto fuera del alcance MCP

## Referencias

- `docs/reference/mcp-remediation-plan.md`
- `docs/operations/OPERATIONS.md`
- `docs/operations/runbooks/deploy-compose.md`
- `docs/master-execution-roadmap.md`
```

- [ ] **Step 3: Read back the full runbook and verify the commands and paths are real**

Run:

```bash
python -c "from pathlib import Path; print(Path(r'docs/operations/runbooks/mcp-release-gate.md').read_text(encoding='utf-8'))"
```

Expected: the runbook is complete, uses only real repo paths and commands, and ends with explicit `GO` / `NO-GO` criteria.

- [ ] **Step 4: Commit**

```bash
git add docs/operations/runbooks/mcp-release-gate.md
git commit -m "docs(operations): add mcp release gate runbook"
```

### Task 3: Close `Fase 6.3` in the roadmap

**Files:**
- Modify: `docs/master-execution-roadmap.md`
- Test: `docs/operations/runbooks/mcp-release-gate.md`

- [ ] **Step 1: Re-read the runbook and current summary before closing**

Run:

```bash
python -c "from pathlib import Path; print(Path(r'docs/operations/runbooks/mcp-release-gate.md').read_text(encoding='utf-8'))"
python -c "from pathlib import Path; p=Path(r'docs/master-execution-roadmap.md'); lines=p.read_text(encoding='utf-8').splitlines(); print('\n'.join(f'{i+1}: {line}' for i,line in enumerate(lines[216:224], start=217)))"
```

Expected: the runbook exists and the summary still shows `Fase 6.3` as `[EN CURSO]`.

- [ ] **Step 2: Update the summary and add a historical closeout note**

Replace the live-summary bullets with this target structure:

```md
- Objetivo actual: preparar **Fase 6.4** del plan MCP para automatizar la suite de regresion MCP en CI.
- Estado actual: **Fase 5.5** `[COMPLETA]`, **Fase 6.1** `[COMPLETA]`, **Fase 6.2** `[COMPLETA]` y **Fase 6.3** `[COMPLETA]` en `G:\_Proyectos\esdata\.worktrees\next-task`; el repo ya tiene una checklist manual de `GO` / `NO-GO` para release MCP basada en checks reales del estado actual.
- Estado del agente activo: cierre de `6.3` completado con runbook operativo; no hay nueva fase reclamada y pasar a `6.4` requiere confirmacion explicita del usuario.
- Reclamo actual: ninguno. **Fase 6.3** queda cerrada; archivos afectados en el slice: `docs/master-execution-roadmap.md`, `docs/operations/runbooks/mcp-release-gate.md`.
- Siguiente paso exacto: esperar confirmacion del usuario y, si la da, reclamar y ejecutar **Fase 6.4 - Suite de regresion MCP en CI**.
```

Add this historical note near the top of `### Historial MCP [HISTORICAL]`:

```md
- Nota 2026-05-05: Fase 6.3 `[COMPLETA]` cerrada en `G:\_Proyectos\esdata\.worktrees\next-task`. Resultado: `docs/operations/runbooks/mcp-release-gate.md` define una checklist manual de `GO` / `NO-GO` para release MCP usando solo checks ya existentes del repo, incluyendo `python scripts/maintenance/verify-doc-contracts.py`, `python -m pytest apps/api/tests/test_mcp_private.py -q` y `python scripts/maintenance/verify_schema.py`; el runbook deja explicitados preconditions, evidencia a registrar, interpretacion fail-closed y limites de lo que el gate no prueba. Evidencia fresca del cierre: lectura completa de `docs/operations/runbooks/mcp-release-gate.md` y comprobacion de rutas/comandos referenciados contra el repo activo. Riesgo residual explicitado: el gate sigue siendo manual y la automatizacion en CI queda pendiente para `6.4`.
```

- [ ] **Step 3: Read back the updated summary and historical note**

Run:

```bash
python -c "from pathlib import Path; p=Path(r'docs/master-execution-roadmap.md'); lines=p.read_text(encoding='utf-8').splitlines(); print('\n'.join(f'{i+1}: {line}' for i,line in enumerate(lines[216:242], start=217)))"
```

Expected: `Fase 6.3` reads as complete, there is no active claim, and `Fase 6.4` is the only next step.

- [ ] **Step 4: Commit**

```bash
git add docs/master-execution-roadmap.md
git commit -m "docs(roadmap): close mcp phase 6.3"
```

## Self-Review Checklist

- Spec coverage: the plan claims `6.3`, creates the release-gate runbook, validates its references, and closes the phase with roadmap evidence.
- Placeholder scan: there are no `TODO`, `TBD`, or "similar to" instructions; every task names exact files, commands, and target wording.
- Type consistency: the runbook commands, filenames, and phase labels match the approved spec and the current roadmap state.
