# MCP Fase 3.2 Modelo Articulo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Endurecer `modelo_articulo` para exigir `(norma, numero)` y provenance fuerte, ocultando del runtime los enlaces legacy debiles.

**Architecture:** El slice mantiene `modelo_articulo` como tabla unica y endurece tres superficies: escritura de seeds, lectura del runtime y esquema Alembic. La implementacion debe seguir TDD: primero fijar el contrato en tests de scripts, despues fijar el comportamiento visible del API con un fixture que mezcle una fila fuerte y una legacy, y por ultimo cerrar el schema con una migracion minima y auditada.

**Tech Stack:** Python, pytest, FastAPI, SQLAlchemy text queries, Alembic, SQLite test mirror, PostgreSQL.

---

**Execution Note:** No crear commits durante la ejecucion de este plan salvo que el usuario lo pida explicitamente. Usa los pasos de verificacion como checkpoints.

## File Map

- Modify: `scripts/tests/test_seed_modelo_articulo.py`
- Modify: `scripts/data/seed_modelo_articulo.py`
- Modify: `scripts/tests/test_aeat_seed_canonical_flow.py`
- Modify: `scripts/seed-modelos.py`
- Modify: `apps/api/tests/conftest.py`
- Modify: `apps/api/tests/test_modelos_truth_contract.py`
- Modify: `apps/api/services/modelos.py`
- Modify: `apps/api/schemas.py`
- Modify: `apps/api/tests/test_alembic_integrity.py`
- Create: `alembic/versions/20260504_0056_modelo_articulo_provenance.py`
- Modify: `docs/master-execution-roadmap.md`

### Task 1: Lock the legacy helper to exact-key tuples

**Files:**
- Modify: `scripts/tests/test_seed_modelo_articulo.py`
- Modify: `scripts/data/seed_modelo_articulo.py`

- [ ] **Step 1: Write the failing tuple-contract tests**

```python
"""Tests para seed_modelo_articulo.py -- AEAT model <-> article mappings."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "data"))
from seed_modelo_articulo import MAPPINGS


LEGACY_PSEUDO_NORMAS = {
    "IRPF",
    "IS",
    "IVA",
    "OP.347",
    "FACTA",
    "IVA.A",
    "IRPF.T",
    "IRNR",
    "DAC2",
    "SII",
    "BIEN.EX",
    "PROV.NR",
}


class TestModeloArticuloData:
    def test_mappings_not_empty(self):
        assert len(MAPPINGS) > 0

    def test_mappings_have_seven_fields(self):
        for row in MAPPINGS:
            assert len(row) == 7

    def test_mappings_use_exact_article_keys(self):
        for modelo, norma, numero, casilla, nota, fuente, url_fuente in MAPPINGS:
            assert modelo
            assert norma not in LEGACY_PSEUDO_NORMAS
            assert numero
            assert casilla is None or casilla
            assert nota

    def test_mappings_require_official_source_fields(self):
        for _, _, _, _, _, fuente, url_fuente in MAPPINGS:
            assert fuente
            assert url_fuente.startswith("https://")
```

- [ ] **Step 2: Run the script test to verify it fails**

Run: `python -m pytest scripts/tests/test_seed_modelo_articulo.py -q`
Expected: FAIL because `MAPPINGS` still has 5 fields and the second slot still contains pseudo-impuestos instead of exact norm codes.

- [ ] **Step 3: Rewrite the legacy helper with verified 7-field rows and strong inserts**

```python
"""LEGACY / NO AUTORITATIVO.

Legacy seed for `modelo_articulo` mappings.

No usar como flujo canonico productivo AEAT. Esta ruta se mantiene solo como
compatibilidad temporal, pero ya no puede insertar enlaces ambiguos.
"""

import os

DB_URL = os.getenv("DATABASE_URL", "postgresql://esdata:esdata_dev@localhost:5432/esdata")

MAPPINGS = [
    (
        "100",
        "LIRPF",
        "17",
        "0002",
        "Rendimientos del trabajo",
        "Instrucciones Modelo 100 2025 -- Casilla 0002",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-renta-personas-fisicas-irpf/modelo-100/instrucciones/index.shtml",
    ),
    (
        "303",
        "LIVA",
        "92",
        "01",
        "IVA devengado",
        "Instrucciones Modelo 303 2025 -- Casilla 01",
        "https://sede.agenciatributaria.gob.es/Sede/ayuda/impuesto-valor-anadido-iva/modelo-303/instrucciones/index.shtml",
    ),
]


def seed():
    import psycopg

    conn = psycopg.connect(DB_URL)
    cur = conn.cursor()

    inserted = 0
    skipped = 0

    for modelo, norma, articulo_num, casilla, nota, fuente, url_fuente in MAPPINGS:
        cur.execute(
            """
            SELECT a.id
            FROM articulo a
            JOIN norma n ON n.id = a.norma_id
            WHERE n.codigo = %s AND a.numero = %s
            LIMIT 1
            """,
            (norma, articulo_num),
        )
        articulo_row = cur.fetchone()
        if not articulo_row:
            skipped += 1
            continue

        cur.execute(
            """
            INSERT INTO modelo_articulo (
                modelo_id,
                articulo_id,
                norma,
                numero,
                casilla,
                nota,
                fuente,
                url_fuente,
                metodo_enlace,
                confianza_enlace
            )
            VALUES (
                (SELECT id FROM aeat_modelo WHERE codigo = %s),
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                'manual_official',
                1.0
            )
            ON CONFLICT (modelo_id, articulo_id) DO UPDATE SET
                norma = EXCLUDED.norma,
                numero = EXCLUDED.numero,
                casilla = EXCLUDED.casilla,
                nota = EXCLUDED.nota,
                fuente = EXCLUDED.fuente,
                url_fuente = EXCLUDED.url_fuente,
                metodo_enlace = EXCLUDED.metodo_enlace,
                confianza_enlace = EXCLUDED.confianza_enlace
            """,
            (
                modelo,
                articulo_row[0],
                norma,
                articulo_num,
                casilla,
                nota,
                fuente,
                url_fuente,
            ),
        )
        inserted += 1

    conn.commit()
    print(f"Seeded {inserted} modelo_articulo mappings; skipped {skipped}")
    conn.close()
```

- [ ] **Step 4: Run the script test again to verify it passes**

Run: `python -m pytest scripts/tests/test_seed_modelo_articulo.py -q`
Expected: PASS

### Task 2: Guard the canonical root seed against weak writes

**Files:**
- Modify: `scripts/tests/test_aeat_seed_canonical_flow.py`
- Modify: `scripts/seed-modelos.py`

- [ ] **Step 1: Add the failing canonical-flow guardrail test**

```python
def test_root_seed_modelos_persists_exact_key_and_strong_provenance():
    seed_modelos = _read("scripts/seed-modelos.py")

    assert "INSERT INTO modelo_articulo (" in seed_modelos
    assert "norma," in seed_modelos
    assert "numero," in seed_modelos
    assert "metodo_enlace," in seed_modelos
    assert "confianza_enlace" in seed_modelos
    assert "'manual_official'" in seed_modelos
```

- [ ] **Step 2: Run the canonical guardrail test to verify it fails**

Run: `python -m pytest scripts/tests/test_aeat_seed_canonical_flow.py -q`
Expected: FAIL because `scripts/seed-modelos.py` still inserts only `casilla`, `nota`, `fuente` and `url_fuente`.

- [ ] **Step 3: Update the canonical seed writer to persist the exact key and strong provenance**

```python
# inside seed_modelos(conn, dry_run: bool = False)
cur.execute(
    """
    INSERT INTO modelo_articulo (
        modelo_id,
        articulo_id,
        norma,
        numero,
        casilla,
        nota,
        fuente,
        url_fuente,
        metodo_enlace,
        confianza_enlace
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'manual_official', 1.0)
    ON CONFLICT (modelo_id, articulo_id) DO UPDATE SET
        norma = EXCLUDED.norma,
        numero = EXCLUDED.numero,
        casilla = EXCLUDED.casilla,
        nota = EXCLUDED.nota,
        fuente = EXCLUDED.fuente,
        url_fuente = EXCLUDED.url_fuente,
        metodo_enlace = EXCLUDED.metodo_enlace,
        confianza_enlace = EXCLUDED.confianza_enlace
    """,
    (
        modelo_id,
        articulo_id,
        norma,
        numero,
        casilla,
        nota,
        fuente,
        url_fuente,
    ),
)
```

- [ ] **Step 4: Run the canonical-flow test again to verify it passes**

Run: `python -m pytest scripts/tests/test_aeat_seed_canonical_flow.py -q`
Expected: PASS

### Task 3: Reproduce the runtime bug with a strong row and a hidden legacy row

**Files:**
- Modify: `apps/api/tests/conftest.py`
- Modify: `apps/api/tests/test_modelos_truth_contract.py`

- [ ] **Step 1: Expand the SQLite mirror and add the failing API contract tests**

```python
# in apps/api/tests/conftest.py
"""
CREATE TABLE modelo_articulo (
    modelo_id INTEGER NOT NULL REFERENCES aeat_modelo(id) ON DELETE CASCADE,
    articulo_id INTEGER NOT NULL REFERENCES articulo(id) ON DELETE CASCADE,
    norma TEXT NOT NULL,
    numero TEXT NOT NULL,
    casilla TEXT,
    nota TEXT,
    fuente TEXT NOT NULL,
    url_fuente TEXT,
    metodo_enlace TEXT NOT NULL,
    confianza_enlace REAL NOT NULL,
    PRIMARY KEY (modelo_id, articulo_id),
    UNIQUE(modelo_id, norma, numero)
)
"""

"""
INSERT INTO modelo_articulo (
    modelo_id,
    articulo_id,
    norma,
    numero,
    casilla,
    nota,
    fuente,
    url_fuente,
    metodo_enlace,
    confianza_enlace
)
SELECT m.id, a.id, 'LIVA', '91', '0002', 'Rendimientos trabajo',
       'Instrucciones Modelo 100 2025', 'https://sede.agenciatributaria.gob.es',
       'manual_official', 1.0
FROM aeat_modelo m, articulo a
JOIN norma n ON n.id = a.norma_id
WHERE m.codigo = '100' AND n.codigo = 'LIVA' AND a.numero = '91'
"""

"""
INSERT INTO modelo_articulo (
    modelo_id,
    articulo_id,
    norma,
    numero,
    casilla,
    nota,
    fuente,
    url_fuente,
    metodo_enlace,
    confianza_enlace
)
SELECT m.id, a.id, 'LIVA', '91', '9999', 'Legacy link should stay hidden',
       'Legacy helper import', 'https://legacy.example.invalid',
       'legacy_numero_only', 0.0
FROM aeat_modelo m, articulo a
JOIN norma n ON n.id = a.norma_id
WHERE m.codigo = '303' AND n.codigo = 'LIVA' AND a.numero = '91'
"""
```

```python
# in apps/api/tests/test_modelos_truth_contract.py
@pytest.mark.asyncio
async def test_modelo_detail_keeps_strong_modelo_articulo_links_visible():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get("/v1/modelos/100")

    assert response.status_code == 200
    data = response.json()
    assert any(
        item["norma"] == "LIVA" and item["numero"] == "91"
        for item in data["articulos"]
    )


@pytest.mark.asyncio
async def test_modelo_detail_hides_legacy_modelo_articulo_links():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get("/v1/modelos/303")

    assert response.status_code == 200
    data = response.json()
    assert data["articulos"] == []


@pytest.mark.asyncio
async def test_modelos_list_excludes_hidden_legacy_modelo_articulo_counts():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-api-key": "test-secret-key"},
    ) as client:
        response = await client.get("/v1/modelos")

    assert response.status_code == 200
    data = response.json()
    modelo_303 = next(item for item in data["modelos"] if item["codigo"] == "303")
    assert modelo_303["articulos_count"] == 0
```

- [ ] **Step 2: Run the API contract tests to verify they fail**

Run: `python -m pytest apps/api/tests/test_modelos_truth_contract.py -q`
Expected: FAIL because the current runtime still returns every `modelo_articulo` row and still counts the legacy row for `303`.

- [ ] **Step 3: Keep the existing smoke case ready as a guardrail**

Run: `python -m pytest apps/api/tests/test_smoke.py -q -k "test_modelo_articulos_endpoint"`
Expected: FAIL or unstable until the runtime filter is implemented, because the new legacy `303` row is now present in the fixture.

### Task 4: Filter the runtime to strong rows only

**Files:**
- Modify: `apps/api/services/modelos.py`
- Modify: `apps/api/schemas.py`

- [ ] **Step 1: Implement the minimal strong-row filter in the service layer**

```python
def list_modelos_summary(db):
    return db.execute(
        text(
            """
            SELECT
                m.codigo,
                m.nombre,
                m.periodo,
                m.impuesto,
                COUNT(DISTINCT ma.articulo_id) AS articulos_count,
                COUNT(DISTINCT mc.id) AS casillas_count
            FROM aeat_modelo m
            LEFT JOIN modelo_articulo ma
                ON ma.modelo_id = m.id
               AND ma.metodo_enlace = 'manual_official'
               AND ma.confianza_enlace = 1.0
               AND ma.url_fuente IS NOT NULL
            LEFT JOIN modelo_campana mcam ON mcam.modelo_id = m.id AND mcam.activo = true
            LEFT JOIN modelo_casilla mc ON mc.campana_id = mcam.id AND mc.activa = true
            GROUP BY m.id, m.codigo, m.nombre, m.periodo, m.impuesto
            ORDER BY m.codigo
            """
        )
    ).mappings()


def list_modelo_articulos(db, codigo: str):
    return db.execute(
        text(
            """
            SELECT
                n.codigo AS norma,
                a.numero,
                a.titulo,
                ma.casilla,
                ma.nota,
                ma.fuente,
                ma.url_fuente
            FROM modelo_articulo ma
            JOIN articulo a ON a.id = ma.articulo_id
            JOIN norma n ON n.id = a.norma_id
            WHERE ma.modelo_id = (SELECT id FROM aeat_modelo WHERE codigo = :codigo)
              AND ma.metodo_enlace = 'manual_official'
              AND ma.confianza_enlace = 1.0
              AND ma.url_fuente IS NOT NULL
              AND ma.norma = n.codigo
              AND ma.numero = a.numero
            ORDER BY n.codigo, a.numero
            """
        ),
        {"codigo": codigo},
    ).mappings()
```

```python
class ModeloArticulo(BaseModel):
    norma: str = Field(description="Codigo de la norma del enlace verificado")
    numero: str = Field(description="Numero del articulo enlazado de forma exacta")
    titulo: str | None = Field(default=None, description="Titulo del articulo")
    casilla: str | None = Field(default=None, description="Casilla AEAT asociada")
    nota: str | None = Field(default=None, description="Nota explicativa del enlace")
    fuente: str = Field(description="Fuente oficial que respalda el enlace verificado")
    url_fuente: str | None = Field(
        default=None,
        description="URL oficial usada para verificar el enlace",
    )
```

- [ ] **Step 2: Re-run the truth-contract test to verify it passes**

Run: `python -m pytest apps/api/tests/test_modelos_truth_contract.py -q`
Expected: PASS

- [ ] **Step 3: Re-run the focused smoke test to verify the hidden legacy row stays hidden**

Run: `python -m pytest apps/api/tests/test_smoke.py -q -k "test_modelo_articulos_endpoint"`
Expected: PASS

### Task 5: Add the Alembic revision for exact key and provenance fields

**Files:**
- Modify: `apps/api/tests/test_alembic_integrity.py`
- Create: `alembic/versions/20260504_0056_modelo_articulo_provenance.py`

- [ ] **Step 1: Add the failing Alembic integrity test**

```python
def test_modelo_articulo_provenance_revision_adds_exact_key_fields():
    revision_path = ALEMBIC_VERSIONS / "20260504_0056_modelo_articulo_provenance.py"
    contents = revision_path.read_text(encoding="utf-8")

    for fragment in (
        "ADD COLUMN IF NOT EXISTS norma TEXT",
        "ADD COLUMN IF NOT EXISTS numero TEXT",
        "ADD COLUMN IF NOT EXISTS metodo_enlace TEXT",
        "ADD COLUMN IF NOT EXISTS confianza_enlace NUMERIC(3,2)",
        "UPDATE modelo_articulo ma",
        "legacy_numero_only",
        "ALTER TABLE modelo_articulo ALTER COLUMN norma SET NOT NULL",
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_modelo_articulo_modelo_norma_numero",
    ):
        assert fragment in contents
```

- [ ] **Step 2: Run the Alembic integrity test to verify it fails**

Run: `python -m pytest apps/api/tests/test_alembic_integrity.py -q`
Expected: FAIL with `FileNotFoundError` because the new revision file does not exist yet.

- [ ] **Step 3: Create the new Alembic revision with minimal, explicit SQL**

```python
"""harden modelo_articulo provenance

# Revision ID: 20260504_0056_modelo_articulo_provenance
# Revises: 20260503_0055_query_audit_response_payload
# Create Date: 2026-05-04 00:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260504_0056_modelo_articulo_provenance"
down_revision = "20260503_0055_query_audit_response_payload"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("ALTER TABLE modelo_articulo ADD COLUMN IF NOT EXISTS norma TEXT"))
    op.execute(sa.text("ALTER TABLE modelo_articulo ADD COLUMN IF NOT EXISTS numero TEXT"))
    op.execute(sa.text("ALTER TABLE modelo_articulo ADD COLUMN IF NOT EXISTS metodo_enlace TEXT"))
    op.execute(sa.text("ALTER TABLE modelo_articulo ADD COLUMN IF NOT EXISTS confianza_enlace NUMERIC(3,2)"))

    op.execute(
        sa.text(
            """
            UPDATE modelo_articulo ma
            SET norma = n.codigo,
                numero = a.numero,
                metodo_enlace = COALESCE(ma.metodo_enlace, 'legacy_numero_only'),
                confianza_enlace = COALESCE(ma.confianza_enlace, 0.0)
            FROM articulo a
            JOIN norma n ON n.id = a.norma_id
            WHERE a.id = ma.articulo_id
            """
        )
    )

    op.execute(sa.text("ALTER TABLE modelo_articulo ALTER COLUMN norma SET NOT NULL"))
    op.execute(sa.text("ALTER TABLE modelo_articulo ALTER COLUMN numero SET NOT NULL"))
    op.execute(sa.text("ALTER TABLE modelo_articulo ALTER COLUMN metodo_enlace SET NOT NULL"))
    op.execute(sa.text("ALTER TABLE modelo_articulo ALTER COLUMN confianza_enlace SET NOT NULL"))

    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                ALTER TABLE modelo_articulo
                ADD CONSTRAINT ck_modelo_articulo_confianza_enlace_range
                CHECK (confianza_enlace >= 0.0 AND confianza_enlace <= 1.0);
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;
            """
        )
    )

    op.execute(
        sa.text(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_modelo_articulo_modelo_norma_numero ON modelo_articulo (modelo_id, norma, numero)"
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS ux_modelo_articulo_modelo_norma_numero"))
    op.execute(
        sa.text(
            "ALTER TABLE modelo_articulo DROP CONSTRAINT IF EXISTS ck_modelo_articulo_confianza_enlace_range"
        )
    )
    op.execute(sa.text("ALTER TABLE modelo_articulo DROP COLUMN IF EXISTS confianza_enlace"))
    op.execute(sa.text("ALTER TABLE modelo_articulo DROP COLUMN IF EXISTS metodo_enlace"))
    op.execute(sa.text("ALTER TABLE modelo_articulo DROP COLUMN IF EXISTS numero"))
    op.execute(sa.text("ALTER TABLE modelo_articulo DROP COLUMN IF EXISTS norma"))
```

- [ ] **Step 4: Run the Alembic integrity test again to verify it passes**

Run: `python -m pytest apps/api/tests/test_alembic_integrity.py -q`
Expected: PASS

### Task 6: Run the full verification set and update the roadmap

**Files:**
- Modify: `docs/master-execution-roadmap.md`

- [ ] **Step 1: Run the full 3.2 verification sequence in order**

Run: `python -m pytest scripts/tests/test_seed_modelo_articulo.py -q`
Expected: PASS

Run: `python -m pytest scripts/tests/test_aeat_seed_canonical_flow.py -q`
Expected: PASS

Run: `python -m pytest apps/api/tests/test_modelos_truth_contract.py -q`
Expected: PASS

Run: `python -m pytest apps/api/tests/test_smoke.py -q -k "test_modelo_articulos_endpoint"`
Expected: PASS

Run: `python -m pytest apps/api/tests/test_alembic_integrity.py -q`
Expected: PASS

- [ ] **Step 2: Update the roadmap note and next step after the tests are green**

```md
- Nota 2026-05-04: Fase 3.2 `[COMPLETA]` cerrada. Resultado: `modelo_articulo` ya persiste `(norma, numero, metodo_enlace, confianza_enlace)` en escritura, las filas legacy quedan ocultas del runtime y `articulos_count` solo cuenta enlaces fuertes. Evidencia fresca: `python -m pytest scripts/tests/test_seed_modelo_articulo.py -q`; `python -m pytest scripts/tests/test_aeat_seed_canonical_flow.py -q`; `python -m pytest apps/api/tests/test_modelos_truth_contract.py -q`; `python -m pytest apps/api/tests/test_smoke.py -q -k "test_modelo_articulos_endpoint"`; `python -m pytest apps/api/tests/test_alembic_integrity.py -q`.
- Siguiente paso exacto: ejecutar **Fase 3.3** del plan MCP: gating de completitud en runtime de modelos.
```

- [ ] **Step 3: Stop here and ask the user before any commit or PR work**

Run: `git status --short`
Expected: only the files from this slice are modified, and there is no commit or PR action unless the user explicitly asks for it.
