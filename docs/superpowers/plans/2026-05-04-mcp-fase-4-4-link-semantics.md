# MCP Fase 4.4 Link Semantics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Separate exact doctrinal links from heuristic ones in BOE linking and make doctrina/DGT/connectivity consumers honor that distinction without changing the public response shape.

**Architecture:** Re-tag `documento_articulo.metodo_enlace` at write time in `apps/workers/boe.py` so explicit citations persist as `auto_link_exact` and contextual fallbacks persist as `auto_link_heuristic`. Then align `doctrina`, `dgt_doctrina`, connectivity, and graph-connectivity consumers so exact-link presence, not raw confidence alone, drives strong-anchor, `verified`, and audit semantics; keep BORME explicitly heuristic-only in this slice.

**Tech Stack:** Python 3.12, SQLAlchemy Core, FastAPI routers/services, pytest, Ruff

**Repo Note:** Do not commit or push as part of this plan unless the user explicitly asks.

---

## File Map

- Modify: `apps/workers/boe.py:646-791`
  Split doctrinal link extraction/persistence into exact vs heuristic methods and keep upgrade behavior correct.
- Modify: `apps/workers/tests/test_boe.py:750-1036`
  Lock red/green behavior for exact vs heuristic persistence and exact-over-heuristic upgrades.
- Modify: `apps/api/routers/doctrina.py:86-110,449-519`
  Align strong-anchor, `verified`, and `completeness` with exact-link presence.
- Modify: `apps/api/routers/dgt_doctrina.py:103-150`
  Mirror the same exact-vs-heuristic doctrine detail semantics.
- Modify: `apps/api/tests/test_smoke.py:502-525`
  Add doctrine detail regression coverage at the API level.
- Modify: `apps/api/tests/test_api_dgt_doctrina.py`
  Add a focused detail regression so DGT doctrine only treats exact links as strong anchors.
- Modify: `apps/api/services/connectivity.py:114-159,202-234`
  Keep the existing payload shape stable while propagating the new exact/heuristic `metodo_enlace` values from storage.
- Modify: `apps/api/services/graph_connectivity.py:77-82,98-103,125-130`
  Preserve graph shape while propagating exact/heuristic link semantics through properties.
- Modify: `apps/api/tests/test_graph_connectivity.py`
  Lock the graph schema/SQL expectations for doctrinal edge properties after the semantic split.
- Modify: `apps/workers/tests/test_borme.py:129-210`
  Make the heuristic-only BORME contract explicit in tests.
- Modify: `docs/master-execution-roadmap.md`
  Close `4.4` with fresh evidence and point the live summary to `4.5` if the slice verifies green.
- Modify: `docs/operations/agent-notes.md`
  Record the reusable invariant that exact links require explicit canonical references, not contextual inference.

### Task 1: Split BOE doctrinal link persistence into exact and heuristic methods

**Files:**
- Modify: `apps/workers/tests/test_boe.py:750-1036`
- Modify: `apps/workers/boe.py:646-791`
- Reference: `docs/superpowers/specs/2026-05-04-mcp-fase-4-4-link-semantics-design.md`

- [ ] **Step 1: Add the failing BOE regression coverage for exact vs heuristic persistence**

```python
def test_auto_link_doctrina_upgrades_to_exact_method_when_better_match_found():
    eng = _setup_link_test_db()
    with eng.begin() as c:
        c.execute(
            text(
                "INSERT INTO documento_interpretativo "
                "(tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente, ambito, referencia, fecha, titulo, texto, url_fuente) "
                "VALUES ('resolucion_teac', 'TEAC', 'es', 'teac', 'fiscal', 'UPGRADE-TEST', '2026-04-12', 'Test', "
                "'Resolucion sobre LIVA 91 en materia de IVA.', NULL)"
            )
        )
        c.execute(
            text(
                "INSERT INTO documento_articulo (documento_id, articulo_id, metodo_enlace, confianza_enlace, nota) "
                "SELECT di.id, a.id, 'auto_link_heuristic', 0.85, 'Old contextual match' "
                "FROM documento_interpretativo di, articulo a JOIN norma n ON n.id = a.norma_id "
                "WHERE di.referencia = 'UPGRADE-TEST' AND n.codigo = 'LIVA' AND a.numero = '91'"
            )
        )

        auto_link_doctrina(c)

        row = c.execute(
            text(
                "SELECT da.confianza_enlace, da.metodo_enlace, da.nota "
                "FROM documento_articulo da "
                "JOIN articulo a ON a.id = da.articulo_id "
                "JOIN norma n ON n.id = a.norma_id "
                "JOIN documento_interpretativo di ON di.id = da.documento_id "
                "WHERE di.referencia = 'UPGRADE-TEST' AND n.codigo = 'LIVA' AND a.numero = '91'"
            )
        ).fetchone()

    assert row == (1.0, "auto_link_exact", "Referencia auto-detectada: LIVA art. 91")


def test_auto_link_doctrina_persists_exact_method_for_explicit_norma_and_article():
    eng = _setup_link_test_db()
    with eng.begin() as c:
        c.execute(
            text(
                "INSERT INTO documento_interpretativo "
                "(tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente, ambito, referencia, fecha, titulo, texto, url_fuente) "
                "VALUES ('consulta_vinculante', 'DGT', 'es', 'dgt', 'fiscal', 'V0000-26', '2026-01-15', 'Test', "
                "'Consulta sobre LIVA 91 y sobre el articulo 15 de la LIS.', NULL)"
            )
        )

        auto_link_doctrina(c)

        rows = c.execute(
            text(
                "SELECT n.codigo, a.numero, da.metodo_enlace, da.confianza_enlace "
                "FROM documento_articulo da "
                "JOIN articulo a ON a.id = da.articulo_id "
                "JOIN norma n ON n.id = a.norma_id "
                "ORDER BY n.codigo, a.numero"
            )
        ).fetchall()

    assert rows == [
        ("LIS", "15", "auto_link_exact", 1.0),
        ("LIVA", "91", "auto_link_exact", 1.0),
    ]


def test_auto_link_doctrina_persists_heuristic_method_for_contextual_match():
    eng = _setup_link_test_db()
    with eng.begin() as c:
        c.execute(
            text(
                "INSERT INTO documento_interpretativo "
                "(tipo_documento, organismo_emisor, jurisdiccion, tipo_fuente, ambito, referencia, fecha, titulo, texto, url_fuente) "
                "VALUES ('consulta_vinculante', 'DGT', 'es', 'dgt', 'fiscal', 'V0001-26', '2026-01-15', 'Test', "
                "'Consulta sobre el IVA. De acuerdo con el articulo 91, procede aplicar el tipo reducido.', NULL)"
            )
        )

        auto_link_doctrina(c)

        row = c.execute(
            text(
                "SELECT n.codigo, a.numero, da.metodo_enlace, da.confianza_enlace "
                "FROM documento_articulo da "
                "JOIN articulo a ON a.id = da.articulo_id "
                "JOIN norma n ON n.id = a.norma_id "
                "WHERE da.documento_id = (SELECT id FROM documento_interpretativo WHERE referencia = 'V0001-26')"
            )
        ).fetchone()

    assert row == ("LIVA", "91", "auto_link_heuristic", 0.85)
```

- [ ] **Step 2: Run the BOE linking slice to verify red**

Run: `python -m pytest apps/workers/tests/test_boe.py -q -k "upgrades_to_exact_method_when_better_match_found or persists_exact_method_for_explicit_norma_and_article or persists_heuristic_method_for_contextual_match"`

Expected: FAIL because `boe.py` still writes `metodo_enlace='auto_link'` for every doctrinal link.

- [ ] **Step 3: Write the minimal BOE implementation split**

```python
def auto_link_doctrina(conn) -> int:
    docs = conn.execute(
        text("SELECT id, referencia, texto FROM documento_interpretativo")
    ).mappings()

    links_created = 0
    for doc in docs:
        found_refs = _extract_doctrina_refs(doc["texto"])

        for codigo, numero, confianza, metodo_enlace in found_refs:
            conn.execute(
                text(
                    """
                    INSERT INTO documento_articulo (documento_id, articulo_id, metodo_enlace, confianza_enlace, nota)
                    SELECT :doc_id, a.id, :metodo_enlace, :confianza_enlace, :nota
                    FROM articulo a
                    JOIN norma n ON n.id = a.norma_id
                    WHERE n.codigo = :codigo AND a.numero = :numero
                    ON CONFLICT (documento_id, articulo_id)
                    DO UPDATE SET
                        metodo_enlace = EXCLUDED.metodo_enlace,
                        confianza_enlace = EXCLUDED.confianza_enlace,
                        nota = EXCLUDED.nota
                    WHERE (
                        EXCLUDED.metodo_enlace = 'auto_link_exact'
                        AND documento_articulo.metodo_enlace != 'auto_link_exact'
                    )
                    OR (
                        EXCLUDED.metodo_enlace = documento_articulo.metodo_enlace
                        AND EXCLUDED.confianza_enlace > documento_articulo.confianza_enlace
                    )
                    """
                ),
                {
                    "doc_id": doc["id"],
                    "codigo": codigo,
                    "numero": numero,
                    "metodo_enlace": metodo_enlace,
                    "confianza_enlace": confianza,
                    "nota": f"Referencia auto-detectada: {codigo} art. {numero}",
                },
            )
            links_created += 1

    return links_created


def _extract_doctrina_refs(text_value: str) -> set[tuple[str, str, float, str]]:
    explicit_norma_refs: set[tuple[str, str, float, str]] = set()
    source = text_value.upper()

    explicit_patterns = [
        re.compile(r"\b(LIVA|LIRPF|LIS|LGT)\s+(\d+)\b", re.IGNORECASE),
        re.compile(r"\b(LIVA|LIRPF|LIS|LGT)\s+ART\.?\s*(\d+)\b", re.IGNORECASE),
        re.compile(r"ART[ÍI]?CULO\s+(\d+)\s+DE\s+LA\s+(LIVA|LIRPF|LIS|LGT)\b", re.IGNORECASE),
        re.compile(r"ART\.?\s*(\d+)\s+DE\s+LA\s+(LIVA|LIRPF|LIS|LGT)\b", re.IGNORECASE),
        re.compile(r"\bART\.?\s+(\d+)\s+(LIVA|LIRPF|LIS|LGT)\b", re.IGNORECASE),
    ]
    for pattern in explicit_patterns:
        for match in pattern.finditer(source):
            first, second = match.groups()
            if first.isdigit():
                numero, codigo = first, second
            else:
                codigo, numero = first, second
            explicit_norma_refs.add((codigo.upper(), numero, 1.00, "auto_link_exact"))

    law_patterns = [
        re.compile(r"ART[ÍI]?CULO\s+(\d+)(?:[\.,][0-9A-ZÁÉÍÓÚÜÑº]+\)?(?:\s+[0-9A-ZÁÉÍÓÚÜÑº]+\)?)?)*\s+DE\s+LA\s+LEY\s+(\d+/\d{4})(?:\s+DEL\s+[A-ZÁÉÍÓÚÜÑ]+)?\b", re.IGNORECASE),
        re.compile(r"ART\.?\s*(\d+)(?:[\.,][0-9A-ZÁÉÍÓÚÜÑº]+\)?(?:\s+[0-9A-ZÁÉÍÓÚÜÑº]+\)?)?)*\s+DE\s+LA\s+LEY\s+(\d+/\d{4})(?:\s+DEL\s+[A-ZÁÉÍÓÚÜÑ]+)?\b", re.IGNORECASE),
    ]
    for pattern in law_patterns:
        for match in pattern.finditer(source):
            numero, ley = match.groups()
            codigo = LAW_TO_NORMA.get(ley)
            if codigo:
                explicit_norma_refs.add((codigo, numero, 1.00, "auto_link_exact"))

    for pattern in [
        re.compile(r"ART[ÍI]?CULO\s+(\d+)(?:[\.,][A-ZÁÉÍÓÚÜÑ]+(?:\s+[A-Z]\))?)?\s+DE\s+LA\s+LEY\s+DEL\s+IVA\b", re.IGNORECASE),
        re.compile(r"ART\.?\s*(\d+)(?:[\.,][A-ZÁÉÍÓÚÜÑ]+(?:\s+[A-Z]\))?)?\s+DE\s+LA\s+LEY\s+DEL\s+IVA\b", re.IGNORECASE),
    ]:
        for match in pattern.finditer(source):
            explicit_norma_refs.add(("LIVA", match.group(1), 1.00, "auto_link_exact"))

    if explicit_norma_refs:
        return explicit_norma_refs

    if len(explicit_law_normas) == 1:
        sola_norma = explicit_law_normas.pop()
        article_refs = set()
        for match in re.finditer(r"(?:ART[ÍI]?CULO|ART\.?)\s+(\d+)\b", source):
            article_refs.add((sola_norma, match.group(1), 1.00, "auto_link_exact"))
        if article_refs:
            return article_refs

    if "IVA" in source and "BASE IMPONIBLE" in source:
        return {("LIVA", "91", 0.75, "auto_link_heuristic")}
    if "IVA" in source and "REGIMEN ESPECIAL" in source:
        return {("LIVA", "91", 0.75, "auto_link_heuristic")}
    if "IVA" in source and "RECARGO DE EQUIVALENCIA" in source:
        return {("LIVA", "24", 0.75, "auto_link_heuristic")}

    contextual_refs = set()
    for match in re.finditer(r"(?:ART[ÍI]?CULO|ART\.?)\s+(\d+)\b", source):
        contextual_refs.add((context_normas[0], match.group(1), 0.85, "auto_link_heuristic"))

    return contextual_refs
```

- [ ] **Step 4: Run the BOE linking regression slice to verify green**

Run: `python -m pytest apps/workers/tests/test_boe.py -q -k "upgrades_to_exact_method_when_better_match_found or persists_exact_method_for_explicit_norma_and_article or persists_heuristic_method_for_contextual_match or auto_link_doctrina_art_norma_variants or matches_ley_del_iva_separate_article"`

Expected: PASS, proving exact and heuristic doctrinal links now persist distinct methods and exact links can upgrade older heuristic rows.

- [ ] **Step 5: Commit**

```bash
git add apps/workers/boe.py apps/workers/tests/test_boe.py
git commit -m "fix: separate exact and heuristic BOE doctrine links"
```

### Task 2: Align doctrina and DGT doctrine detail/audit semantics with exact-link presence

**Files:**
- Modify: `apps/api/routers/doctrina.py:86-110,449-519`
- Modify: `apps/api/routers/dgt_doctrina.py:103-150`
- Modify: `apps/api/tests/test_smoke.py:502-525`
- Modify: `apps/api/tests/test_api_dgt_doctrina.py`
- Reference: `apps/api/tests/conftest.py:398-416`

- [ ] **Step 1: Add failing API regressions for heuristic-only vs exact doctrine anchors**

```python
@pytest.mark.asyncio
async def test_doctrina_detail_marks_heuristic_only_links_as_partial(client):
    with db_session() as db:
        db.execute(text("DELETE FROM documento_articulo WHERE documento_id = (SELECT id FROM documento_interpretativo WHERE referencia = 'V0000-26')"))
        db.execute(
            text(
                "INSERT INTO documento_articulo (documento_id, articulo_id, metodo_enlace, confianza_enlace, nota) "
                "SELECT d.id, a.id, 'auto_link_heuristic', 0.85, 'fixture heuristico' "
                "FROM documento_interpretativo d JOIN articulo a ON 1=1 JOIN norma n ON n.id = a.norma_id "
                "WHERE d.referencia = 'V0000-26' AND n.codigo = 'LIVA' AND a.numero = '91'"
            )
        )
        db.commit()

    async with _client() as c:
        r = await c.get('/v1/doctrina/V0000-26')

    assert r.status_code == 200
    data = r.json()
    assert data['articulos_relacionados'][0]['metodo_enlace'] == 'auto_link_heuristic'
    assert data['confianza']['nivel'] == 1


@pytest.mark.asyncio
async def test_dgt_doctrina_detail_requires_exact_link_for_strong_anchor(client):
    with db_session() as db:
        db.execute(text("DELETE FROM documento_articulo WHERE documento_id = (SELECT id FROM documento_interpretativo WHERE referencia = 'V0000-26')"))
        db.execute(
            text(
                "INSERT INTO documento_articulo (documento_id, articulo_id, metodo_enlace, confianza_enlace, nota) "
                "SELECT d.id, a.id, 'auto_link_heuristic', 0.85, 'fixture heuristico' "
                "FROM documento_interpretativo d JOIN articulo a ON 1=1 JOIN norma n ON n.id = a.norma_id "
                "WHERE d.referencia = 'V0000-26' AND n.codigo = 'LIVA' AND a.numero = '91'"
            )
        )
        db.commit()

    r = await client.get('/v1/doctrina/dgt/V0000-26')
    assert r.status_code == 200
    data = r.json()
    assert data['articulos_relacionados'][0]['metodo_enlace'] == 'auto_link_heuristic'
    assert data['confianza']['nivel'] == 1
```

- [ ] **Step 2: Run the doctrina/DGT detail slice to verify red**

Run: `python -m pytest apps/api/tests/test_smoke.py apps/api/tests/test_api_dgt_doctrina.py -q -k "heuristic_only_links_as_partial or requires_exact_link_for_strong_anchor or doctrina_detalle_expone_articulos_relacionados"`

Expected: FAIL because the routers still promote heuristic links to strong anchors via `confianza_enlace >= 0.85`.

- [ ] **Step 3: Write the minimal router and audit alignment**

```python
EXACT_LINK_METHODS = {"manual", "manual_official", "auto_link_exact"}


def _has_exact_anchor(linked_articles: list[dict]) -> bool:
    return any(item["metodo_enlace"] in EXACT_LINK_METHODS for item in linked_articles)


linked_articles = list(
    db.execute(
        text(
            """
            SELECT
                n.codigo AS norma,
                a.numero,
                da.metodo_enlace,
                da.confianza_enlace
            FROM documento_articulo da
            JOIN articulo a ON a.id = da.articulo_id
            JOIN norma n ON n.id = a.norma_id
            WHERE da.documento_id = :documento_id
            ORDER BY da.confianza_enlace DESC, n.codigo, a.numero
            """
        ),
        {"documento_id": row["id"]},
    ).mappings()
)

has_any_anchor = bool(linked_articles)
has_exact_anchor = _has_exact_anchor(linked_articles)

payload = {
    "referencia": row["referencia"],
    "tipo_documento": row["tipo_documento"],
    "organismo_emisor": row["organismo_emisor"],
    "texto": row["texto"],
    "articulos_relacionados": [
        {
            "norma": item["norma"],
            "numero": item["numero"],
            "metodo_enlace": item["metodo_enlace"],
            "confianza_enlace": float(item["confianza_enlace"]),
        }
        for item in linked_articles
    ],
    "confianza": {
        "nivel": 2 if has_exact_anchor else (1 if has_any_anchor else 0),
        "fuentes": [row["referencia"]],
        "aviso": None if has_any_anchor else "Criterio sin anclaje normativo suficiente",
    },
}

_record_doctrina_query_audit(
    request,
    path=f"/v1/doctrina/{referencia}",
    query_text=referencia,
    tool_name="get_doctrina",
    retrieved_chunks=[
        {
            "referencia": row["referencia"],
            "tipo_documento": row["tipo_documento"],
            "organismo_emisor": row["organismo_emisor"],
            "norma": item["norma"],
            "numero": item["numero"],
        }
        for item in linked_articles
    ],
    response_summary=f"articulos_relacionados={len(linked_articles)}",
    confidence={
        "score": 0.9 if has_exact_anchor else (0.5 if has_any_anchor else 0.0),
        "label": "alta" if has_exact_anchor else ("media" if has_any_anchor else "baja"),
    },
    completeness="completa" if has_exact_anchor else "parcial",
    verified=has_exact_anchor,
)
```

Apply the same `EXACT_LINK_METHODS` helper/logic in `apps/api/routers/dgt_doctrina.py` so both doctrine detail surfaces agree.

- [ ] **Step 4: Run the doctrine detail regression slice to verify green**

Run: `python -m pytest apps/api/tests/test_smoke.py apps/api/tests/test_api_dgt_doctrina.py apps/api/tests/test_http_mcp_audit_phase_1_1.py -q -k "heuristic_only_links_as_partial or requires_exact_link_for_strong_anchor or doctrina_detalle_expone_articulos_relacionados or req_http_mcp_005"`

Expected: PASS, with heuristic-only links remaining visible but no longer counted as exact/verified anchors.

- [ ] **Step 5: Commit**

```bash
git add apps/api/routers/doctrina.py apps/api/routers/dgt_doctrina.py apps/api/tests/test_smoke.py apps/api/tests/test_api_dgt_doctrina.py
git commit -m "fix: require exact links for doctrine verification"
```

### Task 3: Lock graph/BORME guardrails and close the phase docs

**Files:**
- Modify: `apps/api/services/graph_connectivity.py:77-82,98-103,125-130`
- Modify: `apps/api/tests/test_graph_connectivity.py`
- Modify: `apps/workers/tests/test_borme.py:129-210`
- Modify: `docs/master-execution-roadmap.md`
- Modify: `docs/operations/agent-notes.md`

- [ ] **Step 1: Add failing regressions for connectivity propagation and BORME heuristic-only contract**

```python
def test_documento_edge_properties_keep_metodo_enlace_and_confianza_enlace():
    doctrina_props = _NODE_SCHEMA["documento"]["edges"]["articulos"]["properties"]
    assert "da.metodo_enlace" in doctrina_props
    assert "da.confianza_enlace" in doctrina_props


def test_articulo_edge_properties_keep_doctrina_link_semantics():
    doctrina_props = _NODE_SCHEMA["articulo"]["edges"]["doctrina"]["properties"]
    assert "da.metodo_enlace" in doctrina_props
    assert "da.confianza_enlace" in doctrina_props


def test_upsert_empresas_and_link_documento_empresas_keeps_heuristic_contract():
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
        conn.execute(
            text(
                """
                CREATE TABLE empresa (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    nif TEXT,
                    domicilio TEXT,
                    fuente_inicial TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (nombre)
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE documento_empresa (
                    documento_id INTEGER NOT NULL,
                    empresa_id INTEGER NOT NULL,
                    rol TEXT NOT NULL,
                    confianza_extraccion REAL NOT NULL,
                    nota TEXT,
                    PRIMARY KEY (documento_id, empresa_id)
                )
                """
            )
        )

        payload = {
            "referencia": "BORME-A-2025-55-37",
            "fecha": "2025-03-20",
            "titulo": "Actos de SALAMANCA del BORME núm. 55 de 2025",
            "tipo_documento": "cambio_domicilio",
            "texto": "ALDITRAEX SOCIEDAD LIMITADA (Sociedad absorbente). MURILLO BARRERO SOCIEDAD LIMITADA (Sociedad absorbida).",
            "url_fuente": "https://www.boe.es/borme/dias/2025/03/20/pdfs/BORME-A-2025-55-37.pdf",
            "empresa_nombre": "ALDITRAEX SOCIEDAD LIMITADA",
            "empresa_domicilio": "C SANTA LUCIA 19",
            "empresas": [
                {"nombre": "ALDITRAEX SOCIEDAD LIMITADA", "domicilio": "C SANTA LUCIA 19", "rol": "absorbente", "confianza_extraccion": 0.7, "nota": "absorcion"},
                {"nombre": "MURILLO BARRERO SOCIEDAD LIMITADA", "domicilio": None, "rol": "absorbida", "confianza_extraccion": 0.7, "nota": "absorcion"},
            ],
        }

        upsert_documento_interpretativo(conn, payload)
        empresas = upsert_empresas(conn, payload)
        link_documento_empresas(conn, payload["referencia"], empresas)

        rows = conn.execute(
            text(
                "SELECT e.nombre, de.rol, de.confianza_extraccion, de.nota "
                "FROM empresa e JOIN documento_empresa de ON de.empresa_id = e.id ORDER BY e.nombre"
            )
        ).fetchall()

    assert rows == [
        ("ALDITRAEX SOCIEDAD LIMITADA", "absorbente", 0.7, "absorcion"),
        ("MURILLO BARRERO SOCIEDAD LIMITADA", "absorbida", 0.7, "absorcion"),
    ]
```

- [ ] **Step 2: Run the targeted connectivity/BORME tests to verify baseline behavior**

Run: `python -m pytest apps/api/tests/test_graph_connectivity.py apps/workers/tests/test_borme.py -q`

Expected: PASS, confirming the graph schema and BORME heuristic fixtures are stable before the doc closeout.

- [ ] **Step 3: Make the minimal propagation/docs changes**

```markdown
- Nota 2026-05-04: Fase 4.4 `[COMPLETA]` cerrada en `G:\_Proyectos\esdata\.worktrees\next-task`. Resultado: `apps/workers/boe.py` ya separa `auto_link_exact` de `auto_link_heuristic` para `documento_articulo`; `apps/api/routers/doctrina.py` y `apps/api/routers/dgt_doctrina.py` solo marcan anclaje fuerte/verificado cuando existe al menos un enlace exacto; `apps/api/services/graph_connectivity.py` mantiene su shape pero ya propaga `metodo_enlace` con la nueva semantica; `apps/workers/tests/test_borme.py` deja explicitamente fijado que `documento_empresa` sigue siendo heuristico.
```

```markdown
- Scope: `documento_articulo.metodo_enlace`, `doctrina.py`, `dgt_doctrina.py`, `documento_empresa`
- Hallazgo: un umbral alto de confianza no convierte una inferencia contextual en enlace exacto.
- Regla practica: exacto solo con referencia canonica explicita; si el enlace nace de contexto o heuristica, debe persistirse y consumirse como tal aunque su confianza sea alta.
```

- [ ] **Step 4: Run the final `4.4` verification batch**

Run: `python -m pytest apps/workers/tests/test_boe.py apps/workers/tests/test_borme.py apps/api/tests/test_smoke.py apps/api/tests/test_api_dgt_doctrina.py apps/api/tests/test_graph_connectivity.py -q`

Expected: PASS for the full phase slice.

Run: `python -m ruff check apps/workers/boe.py apps/workers/tests/test_boe.py apps/workers/tests/test_borme.py apps/api/routers/doctrina.py apps/api/routers/dgt_doctrina.py apps/api/services/graph_connectivity.py apps/api/tests/test_smoke.py apps/api/tests/test_api_dgt_doctrina.py apps/api/tests/test_graph_connectivity.py docs/master-execution-roadmap.md docs/operations/agent-notes.md --select F,I`

Expected: `All checks passed!`

- [ ] **Step 5: Commit**

```bash
git add apps/api/services/graph_connectivity.py apps/api/tests/test_graph_connectivity.py apps/workers/tests/test_borme.py docs/master-execution-roadmap.md docs/operations/agent-notes.md
git commit -m "docs: close phase 4.4 exact vs heuristic link semantics"
```
