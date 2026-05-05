# MCP Fase 4.5 Vocabulary Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Activate real controlled-vocabulary validation in `documento_interpretativo` worker write boundaries without breaking worker runtime.

**Architecture:** Keep the existing `apps/workers/vocabulary.py` contract as the single source of truth and strengthen `apps/workers/vocabulary_validation.py` so it can sanitize real payloads before DB writes. Then wire that helper into worker `upsert_documento_interpretativo(...)` paths, using explicit fallback mappings for known out-of-vocabulary values and leaving worker extraction/build logic untouched.

**Tech Stack:** Python 3.12, SQLAlchemy Core, pytest, Ruff

**Repo Note:** Do not commit or push as part of this plan unless the user explicitly asks.

---

## File Map

- Modify: `apps/workers/vocabulary_validation.py`
  Make `fallback=` effective, add document-field sanitization, and centralize the known fallback mappings used by real worker writes.
- Modify: `apps/workers/tests/test_vocabulary_validation.py`
  Lock the helper behavior for explicit fallbacks, CNMV mappings, and document payload sanitization.
- Modify: `apps/workers/bde.py`
  Stop hardcoding unsanitized literals in SQL and sanitize the final record before persisting.
- Modify: `apps/workers/aepd.py`
  Sanitize the final document record before the `INSERT ... ON CONFLICT`.
- Modify: `apps/workers/bdns.py`
  Sanitize the final document record before the `INSERT ... ON CONFLICT`.
- Modify: `apps/workers/sepblac.py`
  Sanitize the final document record before the `INSERT ... ON CONFLICT`.
- Modify: `apps/workers/teac.py`
  Sanitize the final document record before the `INSERT ... ON CONFLICT`.
- Modify: `apps/workers/cendoj.py`
  Sanitize dynamic payload values like `organismo_emisor='TSJ'` before persisting.
- Modify: `apps/workers/dgt.py`
  Sanitize the defaulted dynamic payload after `setdefault(...)` and before building column lists.
- Modify: `apps/workers/cnmv.py`
  Sanitize dynamic CNMV payloads so local worker taxonomies degrade to allowed vocabulary buckets at write time.
- Modify: `apps/workers/tests/test_bde.py`
  Update persistence expectations to the normalized `organismo_emisor` value.
- Modify: `apps/workers/tests/test_cendoj.py`
  Add a real upsert regression for `TSJ -> Tribunal Supremo`.
- Modify: `apps/workers/tests/test_cnmv.py`
  Add a real upsert regression for CNMV-specific `tipo_documento` and `ambito` normalization and update runtime expectations to normalized stored values.
- Modify: `docs/master-execution-roadmap.md`
  Close `4.5` with fresh evidence and point the live summary to `Fase 5.1` if verification is green.
- Modify: `docs/operations/agent-notes.md`
  Record the reusable invariant that worker vocabulary validation must happen at the DB write boundary, not only in parser/build helpers.

### Task 1: Strengthen the shared vocabulary sanitization helper

**Files:**
- Modify: `apps/workers/tests/test_vocabulary_validation.py`
- Modify: `apps/workers/vocabulary_validation.py`
- Reference: `apps/workers/vocabulary.py`

- [ ] **Step 1: Add the failing helper regressions**

```python
from vocabulary_validation import (
    DOCUMENTO_VOCAB_FIELDS,
    WORKER_FALLBACKS,
    safe_payload_value,
    sanitize_documento_payload,
    sanitize_payload,
)


def test_safe_payload_value_uses_explicit_fallback_when_mapping_missing():
    result = safe_payload_value(
        "organismo_emisor",
        "Banco de España",
        fallback="Banco de Espana",
    )

    assert result == "Banco de Espana"


def test_sanitize_payload_prefers_worker_mapping_over_explicit_field_fallback():
    payload = {"organismo_emisor": "TSJ"}

    result = sanitize_payload(
        payload,
        frozenset({"organismo_emisor"}),
        field_fallbacks={"organismo_emisor": "CENDOJ"},
    )

    assert result["organismo_emisor"] == "Tribunal Supremo"


def test_sanitize_documento_payload_applies_known_worker_mappings():
    payload = {
        "tipo_documento": "resolucion_cnmv",
        "organismo_emisor": "Banco de España",
        "jurisdiccion": "es",
        "tipo_fuente": "cnmv",
        "ambito": "general_cnmv",
        "estado_vigencia": "vigente",
    }

    result = sanitize_documento_payload(payload)

    assert DOCUMENTO_VOCAB_FIELDS == frozenset(
        {
            "tipo_documento",
            "organismo_emisor",
            "jurisdiccion",
            "tipo_fuente",
            "ambito",
            "estado_vigencia",
        }
    )
    assert result["tipo_documento"] == "documento_cnmv"
    assert result["organismo_emisor"] == "Banco de Espana"
    assert result["ambito"] == "mercados"
    assert result["estado_vigencia"] == "vigente"
```

- [ ] **Step 2: Run the helper slice to verify red**

Run: `python -m pytest apps/workers/tests/test_vocabulary_validation.py -q -k "explicit_fallback or prefers_worker_mapping or sanitize_documento_payload_applies_known_worker_mappings"`

Expected: FAIL because `sanitize_documento_payload(...)` does not exist yet and `safe_payload_value(..., fallback=...)` still ignores the explicit fallback.

- [ ] **Step 3: Write the minimal shared helper implementation**

```python
from vocabulary import VOCABULARY, validate_field

logger = logging.getLogger(__name__)

DOCUMENTO_VOCAB_FIELDS = frozenset(
    {
        "tipo_documento",
        "organismo_emisor",
        "jurisdiccion",
        "tipo_fuente",
        "ambito",
        "estado_vigencia",
    }
)

WORKER_FALLBACKS: dict[str, dict[str, str]] = {
    "organismo_emisor": {
        "TSJ": "Tribunal Supremo",
        "Banco de España": "Banco de Espana",
    },
    "tipo_documento": {
        "resolucion_cnmv": "documento_cnmv",
        "codigo_conducta_cnmv": "documento_cnmv",
        "codigo_autoregulacion_cnmv": "documento_cnmv",
        "informe_anual_cnmv": "documento_cnmv",
        "informe_cnmv": "documento_cnmv",
        "instruccion_tecnica_cnmv": "documento_cnmv",
        "dictamen_cnmv": "documento_cnmv",
        "modelo_comunicacion_cnmv": "documento_cnmv",
        "decision_supervision_cnmv": "documento_cnmv",
        "estadistica_mercado_cnmv": "documento_cnmv",
        "reglamento_cnmv": "documento_cnmv",
        "circ_asesoramiento_cnmv": "circular_cnmv",
    },
    "ambito": {
        "general_cnmv": "mercados",
        "mercados_cnmv": "mercados",
        "reporting_regulatorio_cnmv": "reporting_regulatorio",
        "reporting_financiero_cnmv": "reporting_financiero",
        "infraestructuras_cnmv": "infraestructuras_mercado",
        "gobierno_corporativo": "mercados",
        "proteccion_inversor_cnmv": "mercados",
        "sanciones_cnmv": "mercados",
        "pgc_cnmv": "reporting_financiero",
        "transparencia_emisores": "disclosure_ue",
        "mifid_ii": "mercados_financieros_ue",
        "mifir": "mercados_financieros_ue",
        "mar": "abuso_mercado_ue",
        "dora": "resiliencia_digital_ue",
        "priips": "mercados_financieros_ue",
    },
}


def safe_payload_value(field: str, value: str, fallback: str | None = None) -> str:
    if validate_field(field, value):
        return value

    field_fallbacks = WORKER_FALLBACKS.get(field, {})
    if value in field_fallbacks:
        new_value = field_fallbacks[value]
        logger.warning("Worker fallback: %s=%r -> %r", field, value, new_value)
        return new_value

    if fallback is not None and validate_field(field, fallback):
        logger.warning("Explicit fallback: %s=%r -> %r", field, value, fallback)
        return fallback

    logger.warning(
        "Vocabulary violation (no fallback): %s=%r. Allowed: %s",
        field,
        value,
        sorted(VOCABULARY.get(field, set())),
    )
    return value


def sanitize_payload(
    payload: dict,
    vocabulary_fields: frozenset[str] | None = None,
    field_fallbacks: dict[str, str] | None = None,
) -> dict:
    fields = vocabulary_fields or frozenset(VOCABULARY.keys())
    fallback_values = field_fallbacks or {}
    sanitized = dict(payload)
    for field in fields:
        if field in sanitized and isinstance(sanitized[field], str):
            sanitized[field] = safe_payload_value(
                field,
                sanitized[field],
                fallback=fallback_values.get(field),
            )
    return sanitized


def sanitize_documento_payload(
    payload: dict,
    field_fallbacks: dict[str, str] | None = None,
) -> dict:
    return sanitize_payload(payload, DOCUMENTO_VOCAB_FIELDS, field_fallbacks)
```

- [ ] **Step 4: Run the helper slice to verify green**

Run: `python -m pytest apps/workers/tests/test_vocabulary_validation.py -q`

Expected: PASS, proving the helper now normalizes the known worker mismatches and supports explicit fallback overrides.

- [ ] **Step 5: Optional commit, only if the user explicitly asks**

```bash
git add apps/workers/vocabulary_validation.py apps/workers/tests/test_vocabulary_validation.py
git commit -m "fix: activate worker vocabulary payload sanitization"
```

### Task 2: Activate sanitization in the non-CNMV `documento_interpretativo` upserts

**Files:**
- Modify: `apps/workers/bde.py`
- Modify: `apps/workers/aepd.py`
- Modify: `apps/workers/bdns.py`
- Modify: `apps/workers/sepblac.py`
- Modify: `apps/workers/teac.py`
- Modify: `apps/workers/cendoj.py`
- Modify: `apps/workers/dgt.py`
- Modify: `apps/workers/tests/test_bde.py`
- Modify: `apps/workers/tests/test_cendoj.py`
- Test: `apps/workers/tests/test_aepd.py`
- Test: `apps/workers/tests/test_bdns.py`
- Test: `apps/workers/tests/test_sepblac.py`
- Test: `apps/workers/tests/test_dgt.py`
- Test: `apps/workers/tests/test_teac.py`

- [ ] **Step 1: Add the failing BDE and CENDOJ call-site regressions**

```python
def test_upsert_documento_interpretativo_stores_bde_fields_once():
    engine = create_engine("sqlite:///:memory:", future=True)

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE documento_interpretativo (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tipo_documento TEXT NOT NULL,
                    organismo_emisor TEXT NOT NULL,
                    jurisdiccion TEXT NOT NULL,
                    tipo_fuente TEXT NOT NULL,
                    ambito TEXT NOT NULL,
                    referencia TEXT UNIQUE NOT NULL,
                    fecha TEXT NOT NULL,
                    titulo TEXT,
                    texto TEXT NOT NULL,
                    url_fuente TEXT
                )
                """
            )
        )

        payload = {
            "referencia": "BDE-informes-2024-estabilidad",
            "fecha": "2024-01-15",
            "titulo": "Informe sobre la estabilidad financiera 2024",
            "tipo_documento": "informe_bde",
            "ambito": "estabilidad_financiera",
            "texto": "Informe de estabilidad financiera del Banco de España.",
            "url_fuente": "https://www.bde.es/f/webbde/INF/Secciones/Publicaciones/Informes/informes24/estabilidad24.pdf",
        }

        upsert_documento_interpretativo(conn, payload)
        row = conn.execute(
            text(
                "SELECT referencia, tipo_documento, organismo_emisor, tipo_fuente, ambito "
                "FROM documento_interpretativo"
            )
        ).fetchone()

    assert row == (
        "BDE-informes-2024-estabilidad",
        "informe_bde",
        "Banco de Espana",
        "bde",
        "estabilidad_financiera",
    )


def test_upsert_documento_interpretativo_normalizes_tsj_to_tribunal_supremo():
    engine = create_engine("sqlite:///:memory:", future=True)

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE documento_interpretativo (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tipo_documento TEXT NOT NULL,
                    organismo_emisor TEXT NOT NULL,
                    jurisdiccion TEXT NOT NULL,
                    tipo_fuente TEXT NOT NULL,
                    ambito TEXT NOT NULL,
                    referencia TEXT UNIQUE NOT NULL,
                    fecha TEXT NOT NULL,
                    titulo TEXT,
                    texto TEXT NOT NULL,
                    url_fuente TEXT
                )
                """
            )
        )

        payload = {
            "referencia": "CENDOJ-abc123",
            "fecha": "2026-05-04",
            "titulo": "Sentencia TSJ 1/2026",
            "texto": "Texto de ejemplo.",
            "url_fuente": "https://www.poderjudicial.es/search/TSJ/openDocument/abc123",
            "tipo_documento": "sentencia",
            "organismo_emisor": "TSJ",
            "jurisdiccion": "es",
            "tipo_fuente": "cendoj",
            "ambito": "jurisprudencia_tributaria",
        }

        upsert_documento_interpretativo(conn, payload)
        row = conn.execute(
            text(
                "SELECT tipo_documento, organismo_emisor, tipo_fuente, ambito "
                "FROM documento_interpretativo WHERE referencia = 'CENDOJ-abc123'"
            )
        ).fetchone()

    assert row == (
        "sentencia",
        "Tribunal Supremo",
        "cendoj",
        "jurisprudencia_tributaria",
    )
```

Also update the existing `apps/workers/tests/test_bde.py::test_run_sync_persists_bde_document_and_metrics` assertion from `Banco de España` to `Banco de Espana`.

- [ ] **Step 2: Run the BDE/CENDOJ slice to verify red**

Run: `python -m pytest apps/workers/tests/test_bde.py apps/workers/tests/test_cendoj.py -q`

Expected: FAIL because `bde.py` still persists `Banco de España` directly and `cendoj.py` still writes the raw `TSJ` payload value.

- [ ] **Step 3: Wire the sanitization helper into every non-CNMV document upsert in scope**

```python
from vocabulary_validation import sanitize_documento_payload


# apps/workers/bde.py
def upsert_documento_interpretativo(conn, payload: dict[str, str]) -> None:
    record = sanitize_documento_payload(
        {
            "tipo_documento": payload["tipo_documento"],
            "organismo_emisor": payload.get("organismo_emisor", "Banco de España"),
            "jurisdiccion": payload.get("jurisdiccion", "es"),
            "tipo_fuente": payload.get("tipo_fuente", "bde"),
            "ambito": payload["ambito"],
            "referencia": payload["referencia"],
            "fecha": payload["fecha"],
            "titulo": payload["titulo"],
            "texto": payload["texto"],
            "url_fuente": payload["url_fuente"],
        }
    )
    conn.execute(
        text(
            """
            INSERT INTO documento_interpretativo (
                tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente,
                ambito, referencia, fecha, titulo, texto, url_fuente
            )
            VALUES (
                :tipo_documento, :organismo_emisor, :jurisdiccion, :tipo_fuente,
                :ambito, :referencia, :fecha, :titulo, :texto, :url_fuente
            )
            ON CONFLICT (referencia) DO UPDATE SET
                tipo_documento = excluded.tipo_documento,
                organismo_emisor = excluded.organismo_emisor,
                ambito = excluded.ambito,
                fecha = excluded.fecha,
                titulo = excluded.titulo,
                texto = excluded.texto,
                url_fuente = excluded.url_fuente
            """
        ),
        record,
    )


# apps/workers/aepd.py
record = sanitize_documento_payload(
    {
        "tipo_documento": payload["tipo_documento"],
        "organismo_emisor": payload.get("organismo_emisor", "AEPD"),
        "jurisdiccion": payload.get("jurisdiccion", "es"),
        "tipo_fuente": payload.get("tipo_fuente", "aepd"),
        "ambito": payload["ambito"],
        "referencia": payload["referencia"],
        "fecha": payload["fecha"],
        "titulo": payload["titulo"],
        "texto": payload["texto"],
        "url_fuente": payload["url_fuente"],
    }
)


# apps/workers/bdns.py
record = sanitize_documento_payload(
    {
        "tipo_documento": payload.get("tipo_documento", "convocatoria_subvencion"),
        "organismo_emisor": payload.get("organismo_emisor", "BDNS"),
        "jurisdiccion": payload.get("jurisdiccion", "es"),
        "tipo_fuente": payload.get("tipo_fuente", "bdns"),
        "ambito": payload.get("ambito", "subvenciones"),
        "referencia": payload["referencia"],
        "fecha": payload["fecha"],
        "titulo": payload["titulo"],
        "texto": payload["texto"],
        "url_fuente": payload["url_fuente"],
    }
)


# apps/workers/sepblac.py
record = sanitize_documento_payload(
    {
        "tipo_documento": payload["tipo_documento"],
        "organismo_emisor": payload.get("organismo_emisor", "SEPBLAC"),
        "jurisdiccion": payload.get("jurisdiccion", "es"),
        "tipo_fuente": payload.get("tipo_fuente", "sepblac"),
        "ambito": payload["ambito"],
        "referencia": payload["referencia"],
        "fecha": payload["fecha"],
        "titulo": payload["titulo"],
        "texto": payload["texto"],
        "url_fuente": payload["url_fuente"],
    }
)


# apps/workers/teac.py
record = sanitize_documento_payload(
    {
        "tipo_documento": payload.get("tipo_documento", "resolucion_teac"),
        "organismo_emisor": payload.get("organismo_emisor", "TEAC"),
        "jurisdiccion": payload.get("jurisdiccion", "es"),
        "tipo_fuente": payload.get("tipo_fuente", "teac"),
        "ambito": payload.get("ambito", "fiscal"),
        "referencia": payload["referencia"],
        "fecha": payload["fecha"],
        "titulo": payload["titulo"],
        "texto": payload["texto"],
        "url_fuente": payload["url_fuente"],
    }
)


# apps/workers/cendoj.py
record = sanitize_documento_payload(dict(payload))


# apps/workers/dgt.py
payload.setdefault("tipo_documento", "consulta_vinculante")
payload.setdefault("organismo_emisor", "DGT")
payload.setdefault("jurisdiccion", "es")
payload.setdefault("tipo_fuente", "dgt")
payload.setdefault("ambito", "fiscal")
payload.setdefault("row_completeness", "complete")
payload.setdefault("row_provenance", "official_exact")
payload = sanitize_documento_payload(payload)
```

Use the sanitized `record` or sanitized `payload` in the existing SQL statements instead of mixing placeholders with unsanitized string literals.

- [ ] **Step 4: Run the non-CNMV worker verification slice to verify green**

Run: `python -m pytest apps/workers/tests/test_bde.py apps/workers/tests/test_cendoj.py apps/workers/tests/test_aepd.py apps/workers/tests/test_bdns.py apps/workers/tests/test_sepblac.py apps/workers/tests/test_dgt.py apps/workers/tests/test_teac.py -q`

Expected: PASS, proving the real write boundaries now sanitize normalized values while already-valid workers remain unchanged.

- [ ] **Step 5: Optional commit, only if the user explicitly asks**

```bash
git add apps/workers/bde.py apps/workers/aepd.py apps/workers/bdns.py apps/workers/sepblac.py apps/workers/teac.py apps/workers/cendoj.py apps/workers/dgt.py apps/workers/tests/test_bde.py apps/workers/tests/test_cendoj.py
git commit -m "fix: sanitize worker document payloads before upsert"
```

### Task 3: Normalize CNMV-specific taxonomy at write time

**Files:**
- Modify: `apps/workers/cnmv.py`
- Modify: `apps/workers/tests/test_cnmv.py`
- Reference: `apps/workers/vocabulary_validation.py`

- [ ] **Step 1: Add the failing CNMV normalization regressions**

```python
def test_upsert_documento_interpretativo_normalizes_non_vocabulary_cnmv_values():
    engine = create_engine("sqlite:///:memory:", future=True)

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE documento_interpretativo (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tipo_documento TEXT NOT NULL,
                    organismo_emisor TEXT NOT NULL,
                    jurisdiccion TEXT NOT NULL,
                    tipo_fuente TEXT NOT NULL,
                    ambito TEXT NOT NULL,
                    referencia TEXT UNIQUE NOT NULL,
                    fecha TEXT NOT NULL,
                    titulo TEXT,
                    texto TEXT NOT NULL,
                    url_fuente TEXT,
                    estado_vigencia TEXT
                )
                """
            )
        )

        payload = {
            "referencia": "CNMV-RES-1",
            "fecha": "2025-01-02",
            "titulo": "Resolucion de supervision general",
            "tipo_documento": "resolucion_cnmv",
            "organismo_emisor": "CNMV",
            "jurisdiccion": "es",
            "tipo_fuente": "cnmv",
            "ambito": "general_cnmv",
            "texto": "Documento de supervision general de la CNMV.",
            "url_fuente": "https://www.cnmv.es/res1.pdf",
            "estado_vigencia": "vigente",
        }

        upsert_documento_interpretativo(conn, payload)
        row = conn.execute(
            text(
                "SELECT tipo_documento, ambito, estado_vigencia "
                "FROM documento_interpretativo WHERE referencia = 'CNMV-RES-1'"
            )
        ).fetchone()

    assert row == ("documento_cnmv", "mercados", "vigente")


def test_run_sync_persists_cnmv_document_and_metrics(monkeypatch):
    ...
    assert doc == (
        "BOE-A-2009-133",
        "CNMV",
        "cnmv",
        "reporting_regulatorio",
        "circular_cnmv",
    )
```

- [ ] **Step 2: Run the CNMV slice to verify red**

Run: `python -m pytest apps/workers/tests/test_cnmv.py -q -k "normalizes_non_vocabulary_cnmv_values or run_sync_persists_cnmv_document_and_metrics"`

Expected: FAIL because `cnmv.py` still persists raw worker-local values like `resolucion_cnmv`, `general_cnmv`, and `reporting_regulatorio_cnmv`.

- [ ] **Step 3: Sanitize CNMV payloads after defaults and before column assembly**

```python
from vocabulary_validation import sanitize_documento_payload


def upsert_documento_interpretativo(conn, payload: dict[str, str]) -> None:
    payload = dict(payload)

    if conn.engine.dialect.name == "sqlite":
        table_columns = {
            row[1] for row in conn.execute(text("PRAGMA table_info(documento_interpretativo)"))
        }
    else:
        table_columns = {
            row[0]
            for row in conn.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = current_schema()
                      AND table_name = 'documento_interpretativo'
                    """
                )
            )
        }

    payload.setdefault("organismo_emisor", "CNMV")
    payload.setdefault("jurisdiccion", "es")
    payload.setdefault("tipo_fuente", "cnmv")
    payload.setdefault("row_completeness", "complete")
    payload.setdefault("row_provenance", "official_exact")

    existing = None
    referencia = payload.get("referencia")
    if referencia:
        existing = conn.execute(
            text("SELECT * FROM documento_interpretativo WHERE referencia = :ref"),
            {"ref": referencia},
        ).mappings().first()

    for col in (
        "tipo_documento",
        "ambito",
        "fecha",
        "titulo",
        "url_fuente",
        "estado_vigencia",
    ):
        if payload.get(col) is None and existing and existing.get(col) is not None:
            payload[col] = existing[col]

    payload.setdefault("tipo_documento", "circular_cnmv")
    payload.setdefault("ambito", "general_cnmv")
    payload.setdefault("fecha", datetime.now(UTC).date().isoformat())
    payload.setdefault("titulo", payload.get("referencia", "Documento CNMV"))
    payload.setdefault("url_fuente", "")
    payload.setdefault("estado_vigencia", "vigente")

    payload = sanitize_documento_payload(payload)

    columns = [
        "tipo_documento",
        "organismo_emisor",
        "jurisdiccion",
        "tipo_fuente",
        "ambito",
        "referencia",
        "fecha",
        "titulo",
        "texto",
        "url_fuente",
    ]
    for col in (
        "numero_circular",
        "fecha_publicacion",
        "referencia_boe",
        "estado_vigencia",
        "row_completeness",
        "row_provenance",
    ):
        if col in payload:
            columns.append(col)

    columns = [col for col in columns if col in table_columns]
    placeholders = ", ".join(f":{c}" for c in columns)
    cols_str = ", ".join(columns)
    update_cols = ", ".join(f"{c} = excluded.{c}" for c in columns if c != "referencia")

    conn.execute(
        text(
            f"""
            INSERT INTO documento_interpretativo ({cols_str})
            VALUES ({placeholders})
            ON CONFLICT (referencia) DO UPDATE SET
                {update_cols}
            """
        ),
        payload,
    )
```

Leave `_detect_document_type(...)` and `_detect_ambito(...)` unchanged. They remain worker-local classification helpers; only the DB write boundary is normalized in `4.5`.

- [ ] **Step 4: Run the full CNMV test file to verify green**

Run: `python -m pytest apps/workers/tests/test_cnmv.py -q`

Expected: PASS, proving the worker can keep its richer local detection while storing only approved vocabulary values in `documento_interpretativo`.

- [ ] **Step 5: Optional commit, only if the user explicitly asks**

```bash
git add apps/workers/cnmv.py apps/workers/tests/test_cnmv.py
git commit -m "fix: normalize CNMV vocabulary at write time"
```

### Task 4: Close `4.5` docs and run the full verification batch

**Files:**
- Modify: `docs/master-execution-roadmap.md`
- Modify: `docs/operations/agent-notes.md`
- Reference: `docs/reference/mcp-remediation-plan.md:295-301`

- [ ] **Step 1: Update the live roadmap summary and add the reusable agent note**

```markdown
- Objetivo actual: preparar **Fase 5.1** del plan MCP para hacer obligatorias las migraciones en deploy.
- Estado actual: **Fase 4.5** `[COMPLETA]` en `G:\_Proyectos\esdata\.worktrees\next-task`; `5.1` queda pendiente de confirmacion explicita del usuario antes de abrirse.
- Estado del agente activo: `4.5` cerrada con evidencia fresca; los upserts de `documento_interpretativo` ya sanean vocabulario en runtime real antes de escribir en DB.
- Reclamo actual: `[SIN RECLAMO]` sin archivos reclamados tras el cierre de `4.5`.
- Siguiente paso exacto: pedir confirmacion del usuario para abrir **Fase 5.1** (`scripts/ops/deploy-hetzner.sh`, `.github/workflows/deploy-hetzner.yml`, `docs/deployment/server-installation.md`, `docs/operations/runbooks/deploy-compose.md`).
```

```markdown
- Nota 2026-05-04: Fase 4.5 `[COMPLETA]` cerrada en `G:\_Proyectos\esdata\.worktrees\next-task`. Resultado: `apps/workers/vocabulary_validation.py` ya sanea payloads reales con fallbacks explicitos hacia `VOCABULARY`; `bde.py`, `aepd.py`, `bdns.py`, `sepblac.py`, `teac.py`, `cendoj.py`, `dgt.py` y `cnmv.py` aplican esa validacion en el boundary de escritura de `documento_interpretativo`; y los valores fuera de vocabulario confirmados en este slice (`Banco de España`, `TSJ`, taxonomias locales CNMV) ya degradan a valores permitidos sin romper los workers. Evidencia fresca del cierre: `python -m pytest apps/workers/tests/test_vocabulary_validation.py apps/workers/tests/test_bde.py apps/workers/tests/test_cendoj.py apps/workers/tests/test_cnmv.py apps/workers/tests/test_aepd.py apps/workers/tests/test_bdns.py apps/workers/tests/test_sepblac.py apps/workers/tests/test_dgt.py apps/workers/tests/test_teac.py -q` -> `PASS`; `python -m ruff check ... --select F,I` -> `All checks passed!`.
```

```markdown
### 2026-05-04 - Fase 4.5 vocabulary validation: validar en el write boundary, no solo en el parser

- Scope: `apps/workers/vocabulary_validation.py`, `upsert_documento_interpretativo(...)` en workers, `apps/workers/vocabulary.py`
- Hallazgo: un vocabulario controlado no esta realmente activo mientras los workers puedan saltarselo con literales en SQL o payloads sin sanear.
- Impacto: comprobar solo `build_document_payload(...)` o helpers de deteccion no garantiza que la DB reciba valores permitidos; la validacion real tiene que vivir justo antes del `INSERT ... ON CONFLICT`.
- Regla practica: dejar que el parser/build use taxonomias locales si ayuda a la extraccion, pero normalizar siempre el `record` final en el boundary de escritura hacia valores ya permitidos por `VOCABULARY`.
```

- [ ] **Step 2: Run the final `4.5` verification batch**

Run: `python -m pytest apps/workers/tests/test_vocabulary_validation.py apps/workers/tests/test_bde.py apps/workers/tests/test_cendoj.py apps/workers/tests/test_cnmv.py apps/workers/tests/test_aepd.py apps/workers/tests/test_bdns.py apps/workers/tests/test_sepblac.py apps/workers/tests/test_dgt.py apps/workers/tests/test_teac.py -q`

Expected: PASS for the full `4.5` slice.

Run: `python -m ruff check apps/workers/vocabulary_validation.py apps/workers/bde.py apps/workers/aepd.py apps/workers/bdns.py apps/workers/sepblac.py apps/workers/teac.py apps/workers/cendoj.py apps/workers/dgt.py apps/workers/cnmv.py apps/workers/tests/test_vocabulary_validation.py apps/workers/tests/test_bde.py apps/workers/tests/test_cendoj.py apps/workers/tests/test_cnmv.py docs/master-execution-roadmap.md docs/operations/agent-notes.md --select F,I`

Expected: `All checks passed!`

- [ ] **Step 3: Optional commit, only if the user explicitly asks**

```bash
git add apps/workers/vocabulary_validation.py apps/workers/bde.py apps/workers/aepd.py apps/workers/bdns.py apps/workers/sepblac.py apps/workers/teac.py apps/workers/cendoj.py apps/workers/dgt.py apps/workers/cnmv.py apps/workers/tests/test_vocabulary_validation.py apps/workers/tests/test_bde.py apps/workers/tests/test_cendoj.py apps/workers/tests/test_cnmv.py docs/master-execution-roadmap.md docs/operations/agent-notes.md
git commit -m "fix: activate worker vocabulary validation for document writes"
```
