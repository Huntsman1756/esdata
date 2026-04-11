# DGT MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Incorporar doctrina real de la DGT para `LIVA` y `LIS`, enlazarla con articulos ya cargados y exponerla como una capa de consulta util en la API actual.

**Architecture:** Se reutiliza el modelo actual de `documento_interpretativo` y `documento_articulo`, se añade un worker `dgt.py` para scraping e importacion real y se refuerzan los enlaces articulo-doctrina, la taxonomia minima y la visibilidad operativa en `/status` y Railway.

**Tech Stack:** Python, FastAPI, SQLAlchemy, httpx, pytest, PostgreSQL, Railway.

---

## File Structure

- Create: `G:\_Proyectos\esdata\apps\workers\dgt.py`
- Create: `G:\_Proyectos\esdata\apps\workers\tests\test_dgt.py`
- Modify: `G:\_Proyectos\esdata\apps\api\routers\doctrina.py`
- Modify: `G:\_Proyectos\esdata\apps\api\routers\status.py`
- Modify: `G:\_Proyectos\esdata\apps\api\tests\conftest.py`
- Modify: `G:\_Proyectos\esdata\apps\api\tests\test_smoke.py`
- Modify: `G:\_Proyectos\esdata\apps\workers\boe.py`
- Modify: `G:\_Proyectos\esdata\infra\sql\init.sql`
- Modify: `G:\_Proyectos\esdata\railway.toml`
- Modify: `G:\_Proyectos\esdata\.github\workflows\deploy.yml`
- Modify: `G:\_Proyectos\esdata\README.md`
- Modify: `G:\_Proyectos\esdata\STRUCTURE.md`

## Research

- Modelo actual de doctrina ya existe en `infra/sql/init.sql` con `documento_interpretativo` y `documento_articulo`.
- La API ya expone `GET /v1/doctrina/buscar` y `GET /v1/doctrina/{referencia}` en `apps/api/routers/doctrina.py`.
- El worker BOE ya implementa autolinking de doctrina hacia articulos en `apps/workers/boe.py:auto_link_doctrina`.
- `status.py` solo contempla `worker-boe` y `cron-boe-daily`.
- No existe worker DGT real ni cron DGT en el repo actual.

## Analysis

### Options

1. Reutilizar `documento_interpretativo` y anadir `worker dgt`.
2. Crear un modelo especifico para DGT.
3. Hacer solo importacion parcial sin scraping real.

### Decision

- Chosen: opcion 1.
- Why: es la que mejor encaja con el schema y la API actuales, minimiza cambios y permite entregar valor real sin rehacer la base del proyecto.

### Risks / edge cases

- HTML o estructura del sitio DGT poco estable.
- Cambios de marcado que rompan el parser.
- Enlaces articulo-doctrina demasiado heuristicos si la referencia es ambigua.
- Exceso de alcance si se intenta meter TEAC o toda la taxonomia a la vez.

### Open questions

- No quedan abiertas para este slice: el alcance aceptado es scraping real DGT, producto util completo, solo `LIVA` y `LIS`.

## Q&A results (captured after the session)

- Outcome/acceptance criteria:
  - Doctrina DGT real cargada y consultable para `LIVA` y `LIS`.
  - Enlaces utiles entre doctrina y articulos.
  - `/status` refleja workers DGT.
  - Railway despliega worker y cron DGT.
- Scope boundaries:
  - Solo DGT.
  - Solo `LIVA` y `LIS`.
  - Sin TEAC ni webhooks en este slice.
- Constraints/non-goals:
  - Reutilizar el modelo actual.
  - No rehacer la arquitectura.
- Known modules/paths/subprojects:
  - `apps/workers/boe.py`
  - `apps/api/routers/doctrina.py`
  - `infra/sql/init.sql`
  - `railway.toml`
- Decisions made in Q&A:
  - Scraping real DGT.
  - Slice de producto util, no solo esquema.
  - Recorte a `LIVA` y `LIS`.
- Remaining open questions (if any):
  - Ninguna bloqueante.

## Implementation plan

### Task 1: Crear parser y worker DGT minimo

**Files:**
- Create: `G:\_Proyectos\esdata\apps\workers\dgt.py`
- Create: `G:\_Proyectos\esdata\apps\workers\tests\test_dgt.py`

- [ ] **Step 1: Escribir tests del parser DGT**

Cubrir con fixtures HTML reales o minimizadas:

- extraccion de `referencia`
- extraccion de `fecha`
- extraccion de `titulo`
- extraccion de `texto`
- deteccion de menciones a `LIVA` o `LIS`

- [ ] **Step 2: Ejecutar tests y confirmar fallo inicial**

Run: `pytest apps/workers/tests/test_dgt.py -q`
Expected: FAIL porque `dgt.py` no existe todavia.

- [ ] **Step 3: Implementar worker DGT minimo**

Crear `dgt.py` con estas piezas:

- `fetch_listing()`
- `fetch_document()`
- `parse_document()`
- `upsert_documento_interpretativo()`
- `run_sync()`

Campos persistidos:

- `tipo_documento='consulta_vinculante'`
- `organismo_emisor='DGT'`
- `jurisdiccion='es'`
- `tipo_fuente='dgt'`
- `ambito='fiscal'`
- `referencia`
- `fecha`
- `titulo`
- `texto`
- `url_fuente`

- [ ] **Step 4: Ejecutar tests del parser**

Run: `pytest apps/workers/tests/test_dgt.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/workers/dgt.py apps/workers/tests/test_dgt.py
git commit -m "feat(dgt): add initial DGT scraping worker"
```

### Task 2: Persistencia y filtro LIVA/LIS

**Files:**
- Modify: `G:\_Proyectos\esdata\apps\workers\dgt.py`
- Modify: `G:\_Proyectos\esdata\infra\sql\init.sql`
- Modify: `G:\_Proyectos\esdata\apps\api\tests\conftest.py`

- [ ] **Step 1: Escribir test de persistencia idempotente**

Verificar:

- mismo `referencia` no duplica filas
- solo se guardan documentos que mencionen `LIVA` o `LIS`

- [ ] **Step 2: Ejecutar test y confirmar fallo**

Run: `pytest apps/workers/tests/test_dgt.py -k persistence -q`
Expected: FAIL por falta de upsert/filtro correcto.

- [ ] **Step 3: Implementar persistencia y filtro**

Mantener el schema actual. Si hace falta, solo ampliar seeds de test, no cambiar el modelo base.

- [ ] **Step 4: Ejecutar tests del worker**

Run: `pytest apps/workers/tests/test_dgt.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/workers/dgt.py apps/workers/tests/test_dgt.py infra/sql/init.sql apps/api/tests/conftest.py
git commit -m "feat(dgt): persist and filter DGT doctrine for LIVA and LIS"
```

### Task 3: Mejorar enlazado doctrina-articulo

**Files:**
- Modify: `G:\_Proyectos\esdata\apps\workers\boe.py`
- Modify: `G:\_Proyectos\esdata\apps\workers\dgt.py`
- Modify: `G:\_Proyectos\esdata\apps\workers\tests\test_boe.py`
- Modify: `G:\_Proyectos\esdata\apps\workers\tests\test_dgt.py`

- [ ] **Step 1: Escribir tests de enlazado mas estricto**

Casos minimos:

- `LIVA 91`
- `art. 91 LIVA`
- `articulo 15 LIS`
- texto ambiguo que no debe generar enlace fuerte

- [ ] **Step 2: Ejecutar tests y confirmar fallo**

Run: `pytest apps/workers/tests/test_boe.py apps/workers/tests/test_dgt.py -q`
Expected: FAIL en patrones nuevos o en niveles de confianza esperados.

- [ ] **Step 3: Implementar heuristica mejorada**

Reglas minimas:

- `1.00` si norma + articulo explicitos
- `0.85` si el contexto del documento deja clara la norma
- `0.70` para heuristica debil

- [ ] **Step 4: Ejecutar tests del worker**

Run: `pytest apps/workers/tests/test_boe.py apps/workers/tests/test_dgt.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/workers/boe.py apps/workers/dgt.py apps/workers/tests/test_boe.py apps/workers/tests/test_dgt.py
git commit -m "feat(doctrina): improve doctrine to article linking"
```

### Task 4: Hacer la API de doctrina realmente util

**Files:**
- Modify: `G:\_Proyectos\esdata\apps\api\routers\doctrina.py`
- Modify: `G:\_Proyectos\esdata\apps\api\tests\test_smoke.py`
- Modify: `G:\_Proyectos\esdata\apps\api\tests\conftest.py`

- [ ] **Step 1: Escribir tests API de valor real**

Cubrir:

- filtro por `organismo_emisor`
- resultado de busqueda con doctrina DGT realista
- detalle con `articulos_relacionados`
- `confianza.nivel` coherente con enlaces existentes

- [ ] **Step 2: Ejecutar tests y confirmar fallo**

Run: `pytest apps/api/tests/test_smoke.py -k doctrina -q`
Expected: FAIL porque la respuesta actual no expone articulos ni confianza suficiente.

- [ ] **Step 3: Implementar mejora de respuesta**

Cambios minimos:

- exponer articulos enlazados en el detalle
- permitir `organismo_emisor`
- ajustar `confianza` a nivel `2` con enlace fuerte, `1` con documento sin enlace fuerte

- [ ] **Step 4: Ejecutar smoke tests API**

Run: `pytest apps/api/tests/test_smoke.py -k doctrina -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/routers/doctrina.py apps/api/tests/test_smoke.py apps/api/tests/conftest.py
git commit -m "feat(api): expose useful DGT doctrine responses"
```

### Task 5: Materias curadas minimas para LIVA y LIS

**Files:**
- Modify: `G:\_Proyectos\esdata\infra\sql\init.sql`
- Modify: `G:\_Proyectos\esdata\apps\workers\boe.py`
- Modify: `G:\_Proyectos\esdata\apps\api\tests\conftest.py`

- [ ] **Step 1: Escribir test de materias minimas**

Materias objetivo:

- `tipo-reducido-iva`
- `exenciones-iva`
- `devengo-iva`
- `gastos-no-deducibles`
- `operaciones-vinculadas`
- `bases-imponibles-negativas`

- [ ] **Step 2: Ejecutar tests y confirmar fallo**

Run: `pytest apps/workers/tests/test_boe.py apps/api/tests/test_smoke.py -q`
Expected: FAIL porque no existen aun esas materias ni sus asociaciones.

- [ ] **Step 3: Implementar taxonomia minima**

Mantenerlo simple:

- seeds curados en `init.sql`
- reglas heuristicas pequeñas para artículos ya cargados

- [ ] **Step 4: Ejecutar tests**

Run: `pytest apps/workers/tests/test_boe.py apps/api/tests/test_smoke.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add infra/sql/init.sql apps/workers/boe.py apps/api/tests/conftest.py apps/api/tests/test_smoke.py apps/workers/tests/test_boe.py
git commit -m "feat(taxonomy): add initial LIVA and LIS curated materias"
```

### Task 6: Operacion y despliegue DGT en Railway

**Files:**
- Modify: `G:\_Proyectos\esdata\apps\api\routers\status.py`
- Modify: `G:\_Proyectos\esdata\railway.toml`
- Modify: `G:\_Proyectos\esdata\.github\workflows\deploy.yml`
- Modify: `G:\_Proyectos\esdata\README.md`
- Modify: `G:\_Proyectos\esdata\STRUCTURE.md`

- [ ] **Step 1: Escribir test/chequeo de status**

Esperar workers:

- `worker-dgt`
- `cron-dgt-weekly`

- [ ] **Step 2: Ejecutar tests y confirmar fallo**

Run: `pytest apps/api/tests/test_smoke.py -k status -q`
Expected: FAIL porque `status.py` no refleja aun los workers DGT.

- [ ] **Step 3: Implementar despliegue y status**

Cambios minimos:

- anadir servicios DGT a `railway.toml`
- desplegarlos en `deploy.yml`
- ampliar `/status`
- documentar variables nuevas en `README.md`

- [ ] **Step 4: Ejecutar tests finales de regresion**

Run:

- `pytest apps/workers/tests/test_dgt.py -q`
- `pytest apps/workers/tests/test_boe.py -q`
- `pytest apps/api/tests/test_smoke.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/routers/status.py railway.toml .github/workflows/deploy.yml README.md STRUCTURE.md
git commit -m "feat(deploy): add DGT worker services and status reporting"
```

## Tests to run

- `pytest apps/workers/tests/test_dgt.py -q`
- `pytest apps/workers/tests/test_boe.py -q`
- `pytest apps/api/tests/test_smoke.py -q`

## Acceptance checklist

- [ ] Existe `apps/workers/dgt.py`
- [ ] Hay scraping real DGT con persistencia idempotente
- [ ] Solo se incorpora doctrina objetivo de `LIVA` y `LIS`
- [ ] `GET /v1/doctrina/buscar` devuelve resultados utiles
- [ ] `GET /v1/doctrina/{referencia}` devuelve articulos enlazados
- [ ] `/status` refleja worker y cron DGT
- [ ] Railway puede desplegar `worker-dgt` y `cron-dgt-weekly`
- [ ] La documentacion queda actualizada con la nueva topologia
