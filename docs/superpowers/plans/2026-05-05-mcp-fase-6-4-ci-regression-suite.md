# MCP Fase 6.4 CI Regression Suite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a minimal explicit MCP regression block to CI by reusing the existing doc-contract gate and two existing MCP test suites inside `test-python`.

**Architecture:** Keep `6.4` intentionally small. Modify only `.github/workflows/ci.yml` and `docs/master-execution-roadmap.md`, wiring three already-existing MCP checks into `test-python` after DB bootstrap and before the broad Python test sweep.

**Tech Stack:** GitHub Actions YAML, existing Python scripts/tests, roadmap bookkeeping

---

## File Map

- Modify: `.github/workflows/ci.yml`
  Add the explicit MCP CI block inside `test-python`.
- Modify: `docs/master-execution-roadmap.md`
  Claim `6.4` before implementation and close it with fresh verification evidence after the workflow change is in place.

### Task 1: Claim `Fase 6.4` in the roadmap

**Files:**
- Modify: `docs/master-execution-roadmap.md`

- [ ] **Step 1: Read the live summary block before editing**

Run:

```bash
python -c "from pathlib import Path; p=Path(r'docs/master-execution-roadmap.md'); lines=p.read_text(encoding='utf-8').splitlines(); print('\n'.join(f'{i+1}: {line}' for i,line in enumerate(lines[216:224], start=217)))"
```

Expected: the block shows `Fase 6.3` closed and `Fase 6.4` as the next pending step.

- [ ] **Step 2: Update the summary to mark `6.4` as in progress**

Replace the live-summary bullets with this target structure:

```md
- Objetivo actual: ejecutar **Fase 6.4** del plan MCP para automatizar la suite de regresion MCP en CI.
- Estado actual: **Fase 5.5** `[COMPLETA]`, **Fase 6.1** `[COMPLETA]`, **Fase 6.2** `[COMPLETA]` y **Fase 6.3** `[COMPLETA]` en `G:\_Proyectos\esdata\.worktrees\next-task`; **Fase 6.4** `[EN CURSO]` anade a CI un bloque MCP minimo y explicito reutilizando gates y tests ya existentes.
- Estado del agente activo: diseno y spec de `6.4` aprobados; cableado del bloque MCP minimo en `.github/workflows/ci.yml` en curso.
- Reclamo actual: **Fase 6.4** `[EN CURSO]` - archivos reclamados: `docs/master-execution-roadmap.md`, `.github/workflows/ci.yml`, `docs/superpowers/specs/2026-05-05-mcp-fase-6-4-ci-regression-suite-design.md`, `docs/superpowers/plans/2026-05-05-mcp-fase-6-4-ci-regression-suite.md`. Inicio: 2026-05-05.
- Siguiente paso exacto: insertar el bloque MCP minimo en `test-python`, verificar que referencia solo comandos ya existentes y cerrar `6.4` con evidencia de lectura del workflow actualizado.
```

- [ ] **Step 3: Read back the updated summary**

Run:

```bash
python -c "from pathlib import Path; p=Path(r'docs/master-execution-roadmap.md'); lines=p.read_text(encoding='utf-8').splitlines(); print('\n'.join(f'{i+1}: {line}' for i,line in enumerate(lines[216:224], start=217)))"
```

Expected: the block now shows `Fase 6.4` as `[EN CURSO]`.

- [ ] **Step 4: Commit**

```bash
git add docs/master-execution-roadmap.md
git commit -m "docs(roadmap): claim mcp phase 6.4"
```

### Task 2: Wire the minimal MCP regression block into CI

**Files:**
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Read the current `test-python` block before editing**

Run:

```bash
python -c "from pathlib import Path; lines=Path(r'.github/workflows/ci.yml').read_text(encoding='utf-8').splitlines(); print('\n'.join(f'{i+1}: {line}' for i,line in enumerate(lines[95:121], start=96)))"
```

Expected: `Bootstrap database`, `Run model data quality gate`, `Run model data quality regression test`, and `Run Python tests` appear in order.

- [ ] **Step 2: Insert the explicit MCP CI block after DB bootstrap and before the broad Python test sweep**

Update `.github/workflows/ci.yml` so the `test-python` steps include this exact logical sequence:

```yaml
      - name: Bootstrap database
        run: |
          psql "$DATABASE_URL" -f infra/sql/init.sql
          alembic upgrade heads
        env:
          PGPASSWORD: esdata_test

      - name: Run model data quality gate
        run: python scripts/maintenance/check_model_data_quality.py

      - name: Run model data quality regression test
        run: pytest scripts/tests/test_check_model_data_quality.py -q

      - name: Run MCP doc contracts gate
        run: python scripts/maintenance/verify-doc-contracts.py

      - name: Run MCP private regression tests
        run: python -m pytest apps/api/tests/test_mcp_private.py -q

      - name: Run MCP contract regression tests
        run: python -m pytest apps/api/tests/test_mcp_contract.py -q

      - name: Run Python tests
        run: pytest apps/api/tests/ apps/workers/tests/ -v --tb=short
```

Do not add a new job. Do not add new commands beyond those three MCP checks.

- [ ] **Step 3: Read back the updated workflow slice**

Run:

```bash
python -c "from pathlib import Path; lines=Path(r'.github/workflows/ci.yml').read_text(encoding='utf-8').splitlines(); print('\n'.join(f'{i+1}: {line}' for i,line in enumerate(lines[101:129], start=102)))"
```

Expected: the MCP doc gate, MCP private regression test, and MCP contract regression test appear in `test-python` between DB bootstrap and `Run Python tests`.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add minimal mcp regression block"
```

### Task 3: Close `Fase 6.4` in the roadmap

**Files:**
- Modify: `docs/master-execution-roadmap.md`
- Test: `.github/workflows/ci.yml`

- [ ] **Step 1: Re-read the workflow slice and current summary before closing**

Run:

```bash
python -c "from pathlib import Path; lines=Path(r'.github/workflows/ci.yml').read_text(encoding='utf-8').splitlines(); print('\n'.join(f'{i+1}: {line}' for i,line in enumerate(lines[101:129], start=102)))"
python -c "from pathlib import Path; p=Path(r'docs/master-execution-roadmap.md'); lines=p.read_text(encoding='utf-8').splitlines(); print('\n'.join(f'{i+1}: {line}' for i,line in enumerate(lines[216:224], start=217)))"
```

Expected: the MCP CI block exists and the summary still shows `Fase 6.4` as `[EN CURSO]`.

- [ ] **Step 2: Update the summary and add a historical closeout note**

Replace the live-summary bullets with this target structure:

```md
- Objetivo actual: mantener la remediacion MCP sin nueva fase reclamada hasta que aparezca el siguiente slice priorizado en el plan activo.
- Estado actual: **Fase 5.5** `[COMPLETA]`, **Fase 6.1** `[COMPLETA]`, **Fase 6.2** `[COMPLETA]`, **Fase 6.3** `[COMPLETA]` y **Fase 6.4** `[COMPLETA]` en `G:\_Proyectos\esdata\.worktrees\next-task`; la CI ya contiene una senal MCP minima y explicita dentro de `test-python`.
- Estado del agente activo: cierre de `6.4` completado con wiring minimo en CI; no hay nueva fase MCP reclamada.
- Reclamo actual: ninguno. **Fase 6.4** queda cerrada; archivos afectados en el slice: `docs/master-execution-roadmap.md`, `.github/workflows/ci.yml`.
- Siguiente paso exacto: no reclamar nueva fase MCP hasta que el roadmap activo priorice el siguiente slice.
```

Add this historical note near the top of `### Historial MCP [HISTORICAL]`:

```md
- Nota 2026-05-05: Fase 6.4 `[COMPLETA]` cerrada en `G:\_Proyectos\esdata\.worktrees\next-task`. Resultado: `.github/workflows/ci.yml` ejecuta ya dentro de `test-python` una suite MCP minima y explicita compuesta por `python scripts/maintenance/verify-doc-contracts.py`, `python -m pytest apps/api/tests/test_mcp_private.py -q` y `python -m pytest apps/api/tests/test_mcp_contract.py -q`, colocada despues de `Bootstrap database` y antes del barrido general de tests Python. Evidencia fresca del cierre: lectura del workflow actualizado confirmando el bloque MCP minimo y comprobacion de que los tres comandos referenciados existen en el repo activo. Riesgo residual explicitado: la cobertura MCP automatizada sigue siendo minima y puede duplicarse parcialmente con el barrido general; ampliar la matriz o anadir suites MCP extra queda fuera de este slice.
```

- [ ] **Step 3: Read back the updated summary and historical note**

Run:

```bash
python -c "from pathlib import Path; p=Path(r'docs/master-execution-roadmap.md'); lines=p.read_text(encoding='utf-8').splitlines(); print('\n'.join(f'{i+1}: {line}' for i,line in enumerate(lines[216:242], start=217)))"
```

Expected: `Fase 6.4` reads as complete, there is no active claim, and no new MCP phase is claimed.

- [ ] **Step 4: Commit**

```bash
git add docs/master-execution-roadmap.md
git commit -m "docs(roadmap): close mcp phase 6.4"
```

## Self-Review Checklist

- Spec coverage: the plan claims `6.4`, wires the minimal MCP CI block into `test-python`, and closes the phase with roadmap evidence.
- Placeholder scan: there are no `TODO`, `TBD`, or vague follow-ups; every task names exact files, commands, and expected workflow placement.
- Type consistency: the three MCP commands in the plan match the approved spec and are referenced consistently in the CI block and roadmap closeout note.
