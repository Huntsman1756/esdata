# ITPAJD + Norma Classification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the first mandatory missing norm (`ITPAJD`) to the shared legislation corpus and introduce the minimum classification metadata needed to distinguish ordinary tax laws from future compliance sources.

**Architecture:** Keep the existing `norma -> articulo -> version_articulo` pipeline intact. Extend the `norma` catalog with lightweight classification fields, teach the BOE worker how to classify and ingest `ITPAJD`, then expose the new metadata through the API and web types without introducing a second catalog.

**Tech Stack:** FastAPI, SQLAlchemy, SQLite test fixtures, Postgres migrations, Next.js 15, TypeScript, pytest

---

This plan intentionally covers only the first executable subproject from the approved spec:

- classification base in `norma`
- first missing mandatory norm: `ITPAJD`

Leave `Ley 38/1992`, `RDL 2/2004`, `DAC6`, and `UNE 19602` for follow-on plans once this slice is merged and verified.

## Task boundary note

Task 1 must keep the BOE write path operable against the new schema. That means `apps/workers/boe.py` may take the minimum runtime-safe defaults needed to populate `tipo_documento`, `ambito`, and `estado_cobertura` for already supported norms. What remains deferred to Task 2 is the specific `ITPAJD` source addition and per-code classification map.

### Task 1: Add classification fields to the norma catalog

**Files:**
- Create: `infra/sql/004_norma_classification.sql`
- Modify: `infra/sql/init.sql`
- Modify: `apps/workers/boe.py`
- Test: `apps/workers/tests/test_boe.py`

- [ ] **Step 1: Write the failing schema test**

Add this test near the other schema/unit tests in `apps/workers/tests/test_boe.py`:

```python
def test_schema_statements_include_norma_classification_columns():
    norma_stmt = _schema_statements("sqlite")[0]

    assert "tipo_documento TEXT NOT NULL" in norma_stmt
    assert "estado_cobertura TEXT NOT NULL" in norma_stmt
```

- [ ] **Step 2: Run the targeted test and verify it fails**

Run: `pytest apps/workers/tests/test_boe.py::test_schema_statements_include_norma_classification_columns -q`

Expected: FAIL because the current `norma` table definition does not include `tipo_documento` or `estado_cobertura`.

- [ ] **Step 3: Add the migration and base schema support**

Create `infra/sql/004_norma_classification.sql` with this migration:

```sql
ALTER TABLE norma ADD COLUMN IF NOT EXISTS tipo_documento TEXT;
ALTER TABLE norma ADD COLUMN IF NOT EXISTS estado_cobertura TEXT;

UPDATE norma
SET tipo_documento = CASE codigo
    WHEN 'LGT' THEN 'ley'
    WHEN 'LIRPF' THEN 'ley'
    WHEN 'LIS' THEN 'ley'
    WHEN 'LIVA' THEN 'ley'
    ELSE 'ley'
END
WHERE tipo_documento IS NULL;

UPDATE norma
SET ambito = CASE
    WHEN ambito = 'fiscal' THEN 'tributario'
    ELSE ambito
END;

UPDATE norma
SET estado_cobertura = 'ingestada'
WHERE estado_cobertura IS NULL;

ALTER TABLE norma ALTER COLUMN tipo_documento SET NOT NULL;
ALTER TABLE norma ALTER COLUMN estado_cobertura SET NOT NULL;
```

Update the `norma` table in `infra/sql/init.sql` to this shape:

```sql
CREATE TABLE IF NOT EXISTS norma (
    id SERIAL PRIMARY KEY,
    codigo TEXT UNIQUE NOT NULL,
    titulo TEXT NOT NULL,
    boe_id TEXT UNIQUE NOT NULL,
    eli_uri TEXT UNIQUE,
    jurisdiccion TEXT NOT NULL,
    tipo_fuente TEXT NOT NULL,
    tipo_documento TEXT NOT NULL,
    ambito TEXT NOT NULL,
    estado_cobertura TEXT NOT NULL,
    vigente_desde DATE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

Update the first schema statement in `apps/workers/boe.py` to match.

Also add the minimum runtime-safe support in `apps/workers/boe.py` so the existing BOE write path still works under the new schema:

```python
@dataclass
class NormaMetadata:
    codigo: str
    boe_id: str
    titulo: str
    eli_uri: str | None
    jurisdiccion: str
    tipo_fuente: str
    tipo_documento: str
    ambito: str
    estado_cobertura: str
    vigente_desde: str
```

For Task 1 only, `parse_metadata()` should emit defaults for already supported norms:

```python
tipo_documento="ley"
ambito="tributario"
estado_cobertura="ingestada"
```

Update `upsert_norma()` so it inserts and updates those new required columns.

Add one regression test that exercises `_ensure_schema()` plus `upsert_norma()` against the real schema path and asserts the insert persists `tipo_documento` and `estado_cobertura`.

- [ ] **Step 4: Run the targeted test again**

Run: `pytest apps/workers/tests/test_boe.py::test_schema_statements_include_norma_classification_columns -q`

Expected: PASS.

- [ ] **Step 5: Commit the schema change**

```bash
git add infra/sql/004_norma_classification.sql infra/sql/init.sql apps/workers/boe.py apps/workers/tests/test_boe.py
git commit -m "feat(norma): add catalog classification fields"
```

### Task 2: Teach the BOE worker to classify norms and ingest ITPAJD

**Files:**
- Modify: `apps/workers/boe.py`
- Modify: `apps/workers/tests/test_boe.py`
- Modify: `docker-compose.yml`
- Modify: `README.md`

- [ ] **Step 1: Write the failing worker tests**

Add these tests to `apps/workers/tests/test_boe.py`:

```python
def test_default_normas_includes_itpajd():
    from boe import DEFAULT_NORMAS

    assert DEFAULT_NORMAS["ITPAJD"] == "BOE-A-1993-253"


def test_parse_metadata_sets_classification_for_itpajd():
    payload = {
        "data": [
            {
                "titulo": "Real Decreto Legislativo 1/1993, de 24 de septiembre, por el que se aprueba el texto refundido del Impuesto sobre Transmisiones Patrimoniales y Actos Juridicos Documentados.",
                "fecha_vigencia": "19930925",
                "url_eli": "https://www.boe.es/eli/es/rdlg/1993/09/24/1/con",
            }
        ]
    }

    metadata = parse_metadata("ITPAJD", "BOE-A-1993-253", payload)

    assert metadata.tipo_documento == "real_decreto_legislativo"
    assert metadata.ambito == "tributario"
    assert metadata.estado_cobertura == "ingestada"
```

- [ ] **Step 2: Run the targeted tests and verify they fail**

Run: `pytest apps/workers/tests/test_boe.py::test_default_normas_includes_itpajd apps/workers/tests/test_boe.py::test_parse_metadata_sets_classification_for_itpajd -q`

Expected: FAIL because `ITPAJD` is missing and `NormaMetadata` does not carry the new classification fields yet.

- [ ] **Step 3: Implement BOE classification and the ITPAJD source**

In `apps/workers/boe.py`, extend the BOE source map and add a per-code classification map so current tax norms remain `ley` / `tributario` and `ITPAJD` becomes `real_decreto_legislativo` / `tributario`.

Update `parse_metadata()` to use that map.

Update the default local BOE list in `docker-compose.yml`:

```yaml
BOE_LEGISLACION_NORMAS: LIVA,LIRPF,LIS,LGT,ITPAJD
```

Update the operational env example in `README.md`:

```md
- `BOE_LEGISLACION_NORMAS=LIVA,LIS,LIRPF,LGT,ITPAJD`
```

- [ ] **Step 4: Run the worker tests for the new slice**

Run: `pytest apps/workers/tests/test_boe.py -q`

Expected: PASS.

- [ ] **Step 5: Commit the worker support**

```bash
git add apps/workers/boe.py apps/workers/tests/test_boe.py docker-compose.yml README.md
git commit -m "feat(boe): ingest itpajd with catalog classification"
```

### Task 3: Expose classification and ITPAJD through the API test fixtures

**Files:**
- Modify: `apps/api/tests/conftest.py`
- Modify: `apps/api/routers/legislacion.py`
- Modify: `apps/api/tests/test_smoke.py`

- [ ] **Step 1: Write the failing API smoke test**

Add this test to `apps/api/tests/test_smoke.py`:

```python
@pytest.mark.asyncio
async def test_legislacion_expone_itpajd_con_clasificacion():
    async with _client() as c:
        lista = await c.get("/v1/legislacion")
        detalle = await c.get("/v1/legislacion/ITPAJD")
        articulo = await c.get("/v1/legislacion/ITPAJD/articulos/7")

    assert lista.status_code == 200
    assert detalle.status_code == 200
    assert articulo.status_code == 200

    norma = next(item for item in lista.json()["normas"] if item["codigo"] == "ITPAJD")
    assert norma["tipo_documento"] == "real_decreto_legislativo"
    assert norma["ambito"] == "tributario"
    assert norma["estado_cobertura"] == "ingestada"

    assert detalle.json()["tipo_documento"] == "real_decreto_legislativo"
    assert detalle.json()["estado_cobertura"] == "ingestada"
    assert "transmisiones" in articulo.json()["texto"].lower()
```

- [ ] **Step 2: Run the targeted smoke test and verify it fails**

Run: `pytest apps/api/tests/test_smoke.py::test_legislacion_expone_itpajd_con_clasificacion -q`

Expected: FAIL because the fixture database does not seed `ITPAJD` yet and the router does not select the new fields.

- [ ] **Step 3: Seed the test database and expose the new fields in the router**

In `apps/api/tests/conftest.py`, update the test `norma` schema to include `tipo_documento` and `estado_cobertura`.

Seed the existing `LIVA` row with the new fields and add an `ITPAJD` fixture plus one article/version for `ITPAJD art. 7`.

In `apps/api/routers/legislacion.py`, select the new fields in list and detail endpoints.

- [ ] **Step 4: Run the API verification set**

Run: `pytest apps/api/tests/test_smoke.py::test_legislacion_expone_itpajd_con_clasificacion apps/api/tests/test_smoke.py::test_legislacion_lista_articulos_por_norma apps/api/tests/test_smoke.py::test_liva_articulo_91 -q`

Expected: PASS.

- [ ] **Step 5: Commit the API slice**

```bash
git add apps/api/tests/conftest.py apps/api/routers/legislacion.py apps/api/tests/test_smoke.py
git commit -m "feat(api): expose norma classification and itpajd"
```

### Task 4: Keep web types and product messaging aligned with the first slice

**Files:**
- Modify: `apps/web/lib/types.ts`
- Modify: `apps/web/app/page.tsx`
- Modify: `README.md`
- Modify: `docs/production-status-2026-04-12.md`

- [ ] **Step 1: Extend the web API types**

Update `Norma` in `apps/web/lib/types.ts` to include `tipo_documento` and `estado_cobertura`.

- [ ] **Step 2: Update the home copy to reflect the verified new floor only after the slice passes**

In `apps/web/app/page.tsx`, replace the current coverage line with:

```tsx
<p className="mt-1">Hoy cubre LGT, LIRPF, LIS, LIVA e ITPAJD. No promete mas de lo que ya esta verificado.</p>
```

Tighten the follow-up paragraph to remove `ITP y AJD` from the future-only list.

- [ ] **Step 3: Sync the operational docs**

In `README.md`, update the messaging so `ITPAJD` is reflected in the current slice without overclaiming deployed verification if Task 5 has not happened yet.

In `docs/production-status-2026-04-12.md`, add a note that the `ITPAJD` slice is implemented and pending deployed verification. The final `Slice ITPAJD` verification subsection belongs to Task 5 after production smoke passes.

- [ ] **Step 4: Run final verification commands**

Run:

```bash
pytest apps/workers/tests/test_boe.py -q
pytest apps/api/tests/test_smoke.py -q
npm --prefix apps/web run build
```

Expected:

- worker tests PASS
- API smoke tests PASS
- Next.js build succeeds

- [ ] **Step 5: Commit the user-facing alignment**

```bash
git add apps/web/lib/types.ts apps/web/app/page.tsx README.md docs/production-status-2026-04-12.md
git commit -m "docs(web): align messaging with itpajd coverage"
```

### Task 5: Deploy and verify the first coverage slice in production

**Files:**
- Modify: `README.md`
- Modify: `DEPLOY_CHECKLIST.md`

- [ ] **Step 1: Update the deploy checklist for the new migration and norm**

Append these lines to `DEPLOY_CHECKLIST.md` in the pre-deploy and smoke sections:

```md
[ ] Ejecutar migracion contra el Postgres real:
    psql $DATABASE_URL -f infra/sql/004_norma_classification.sql

[ ] Verificar nueva norma:
    curl https://esdata-production.up.railway.app/v1/legislacion/ITPAJD
    -> devuelve `tipo_documento=real_decreto_legislativo`
```

- [ ] **Step 2: Deploy after the commits land on `main`**

Run: `git push`

Expected: GitHub Actions deploys API/workers and the web workflow deploys `apps/web` if touched.

- [ ] **Step 3: Verify the production slice manually**

Run:

```bash
curl https://esdata-production.up.railway.app/v1/legislacion/ITPAJD
curl https://esdata-production.up.railway.app/v1/legislacion/ITPAJD/articulos
curl "https://esdata-production.up.railway.app/v1/buscar?q=transmisiones&norma=ITPAJD"
```

Expected:

- first call returns the ITPAJD metadata with classification fields
- second call returns at least one article
- third call returns at least one legislation result for `ITPAJD`

- [ ] **Step 4: Commit checklist-only changes if they were left out**

```bash
git add DEPLOY_CHECKLIST.md README.md
git commit -m "docs(deploy): add itpajd verification steps"
```

- [ ] **Step 5: Stop and write the next plan before expanding again**

The next implementation plan should cover exactly one of these:

```md
- `Ley 38/1992`
- `RDL 2/2004`
- `DAC6`
- `UNE 19602`
```

Do not batch the remaining four into a single implementation pass.
