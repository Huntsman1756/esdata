# [REFERENCE] Sociedad De Valores Compliance Engine Implementation Plan

> Documento de detalle de la ola `sociedad de valores`. No es la fuente activa de estado. La fuente activa unica de estado y ejecucion es `docs/master-execution-roadmap.md`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Evolucionar `esdata` desde motor fiscal/regulatorio trazable a una plataforma util para una sociedad de valores en Espana, con corpus curado, motor de aplicabilidad, obligaciones operativas, change impact y workflow de compliance.

**Architecture:** Mantener la arquitectura actual por fuentes (`workers` + `routers`) y anadir tres capas nuevas sobre ella: `aplicabilidad`, `operacion` y `workflow interno`. El corpus publico oficial sigue siendo la base; las capas internas solo se construyen despues de tener taxonomia y aplicabilidad solidas.

**Tech Stack:** FastAPI, SQLAlchemy, PostgreSQL, Alembic, pytest, MCP sobre FastAPI, Next.js 15 para la UI interna futura.

---

## How To Use This Plan

- Ejecutar **una tarea principal por sesion**.
- No saltar a la siguiente tarea sin dejar verdes sus tests y actualizar el estado del plan.
- Si una tarea descubre que falta una decision de dominio, documentarla en `docs/` antes de tocar schema o endpoints.
- Si aparece conflicto entre corpus, taxonomia y producto, priorizar siempre:
  1. fuente oficial,
  2. trazabilidad,
  3. aplicabilidad correcta,
  4. workflow despues.

## File Map

### Ficheros existentes que se van a extender

- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `docs/database.md`
- Modify: `docs/fiscal-regulatory-expansion-roadmap.md`
- Modify: `apps/api/main.py`
- Modify: `apps/api/mcp_server.py`
- Modify: `apps/api/schemas.py`
- Modify: `apps/api/routers/obligaciones.py`
- Modify: `apps/api/routers/consulta.py`
- Modify: `apps/workers/cnmv.py`
- Modify: `apps/workers/sepblac.py`
- Modify: `apps/workers/cendoj.py`
- Modify: `apps/workers/eurlex.py`
- Modify: `apps/workers/bde.py`
- Modify: `apps/workers/aepd.py`
- Modify: `apps/api/tests/conftest.py`
- Modify: `apps/api/tests/test_smoke.py`

### Ficheros nuevos previstos

- Create: `docs/sociedad-valores-scope.md`
- Create: `docs/controlled-vocabulary-regulatorio.md`
- Create: `docs/source-manifests/sociedad-valores-wave-1.md`
- Create: `apps/api/domain/taxonomies.py`
- Create: `apps/api/domain/entity_profiles.py`
- Create: `apps/api/services/applicability.py`
- Create: `apps/api/routers/perfiles.py`
- Create: `apps/api/routers/cambios.py`
- Create: `apps/api/routers/compliance.py`
- Create: `apps/api/tests/test_applicability.py`
- Create: `apps/api/tests/test_change_impact.py`
- Create: `apps/api/tests/test_compliance_workflow.py`
- Create: `apps/workers/tests/test_cendoj.py`
- Create: `apps/workers/tests/test_eurlex.py`
- Create: `apps/workers/tests/test_bde.py`
- Create: `apps/workers/tests/test_aepd.py`
- Create: `alembic/versions/20260425_0009_reg_entity_profiles.py`
- Create: `alembic/versions/20260425_0010_obligacion_aplicabilidad.py`
- Create: `alembic/versions/20260425_0011_change_impact.py`
- Create: `alembic/versions/20260425_0012_compliance_workflow.py`

## Session Order

### Sesion 1
- Task 1: fijar alcance de sociedad de valores
- Task 2: cerrar vocabulario controlado

### Sesion 2
- Task 3: cerrar source manifest regulatorio prioritario
- Task 4: endurecer workers y tests de corpus regulatorio

### Sesion 3
- Task 5: introducir perfil regulatorio de entidad
- Task 6: introducir motor de aplicabilidad

### Sesion 4
- Task 7: expandir modelo de obligaciones operativas
- Task 8: exponer aplicabilidad por API y MCP

### Sesion 5
- Task 9: introducir change impact engine
- Task 10: tests de impacto y diffs

### Sesion 6
- Task 11: introducir workflow de compliance
- Task 12: endurecer seguridad y tenancy para capa interna

### Sesion 7+
- Task 13: UI interna minima
- Task 14: observabilidad, docs y hardening final

## Task 1: Freeze Sociedad De Valores Scope

**Files:**
- Create: `docs/sociedad-valores-scope.md`
- Modify: `README.md`
- Modify: `docs/fiscal-regulatory-expansion-roadmap.md`

- [ ] **Step 1: Escribir el documento de alcance de dominio**

Crear `docs/sociedad-valores-scope.md` con estas secciones minimas:

```md
# Alcance objetivo: sociedad de valores

## Perfil base
- tipo_entidad: sociedad_valores
- jurisdiccion: espana
- supervision_principal: CNMV

## Servicios que el perfil puede prestar
- recepcion_transmision_ordenes
- ejecucion_ordenes
- asesoramiento_inversion
- gestion_discrecional
- colocacion
- aseguramiento
- custodia

## Variables de aplicabilidad
- retail
- profesional
- contraparte_elegible
- cross_border_ue
- cross_border_fuera_ue
- outsourcing_critico
- comercializacion_priips
- reporting_reservado
- aml_cft_reforzado

## Dominios regulatorios P1
- CNMV reporting y circulares ESI
- SEPBLAC / PBC-FT
- MiFID II / MiFIR
- MAR
- PRIIPs
- DORA

## Fuera de alcance inicial
- legal horizontal generalista
- litigacion civil/laboral amplia
- private knowledge del cliente mezclado con corpus publico
```

- [ ] **Step 2: Anadir referencia al scope en README**

Anadir una nota corta en `README.md` dentro de la seccion de roadmap o posicionamiento:

```md
- Perfil regulado prioritario actual: `sociedad de valores` en Espana, como caso de uso para evolucionar la capa regulatoria y de compliance.
```

- [ ] **Step 3: Reflejar el caso objetivo en el roadmap regulatorio**

Anadir un bloque en `docs/fiscal-regulatory-expansion-roadmap.md` bajo `Purpose`:

```md
## Target regulated entity

La entidad regulada prioritaria para la siguiente ola es una `sociedad de valores` en Espana. Las decisiones de corpus, taxonomia y workflow deben evaluarse primero contra ese caso.
```

- [ ] **Step 4: Verificar que el repo refleja el caso objetivo**

Run: `pytest apps/api/tests/test_smoke.py -k "cnmv or sepblac or obligaciones" -q`

Expected: PASS. Este paso no prueba el nuevo doc; confirma que el caso objetivo sigue alineado con el slice regulatorio ya existente.

- [ ] **Step 5: Commit**

```bash
git add README.md docs/sociedad-valores-scope.md docs/fiscal-regulatory-expansion-roadmap.md
git commit -m "docs: define sociedad de valores target scope"
```

## Task 2: Harden Controlled Vocabulary

**Files:**
- Create: `docs/controlled-vocabulary-regulatorio.md`
- Create: `apps/api/domain/taxonomies.py`
- Create: `apps/api/tests/test_taxonomies.py`
- Modify: `apps/api/schemas.py`

- [ ] **Step 1: Write the failing taxonomy test**

Crear `apps/api/tests/test_taxonomies.py`:

```python
from apps.api.domain.taxonomies import (
    ALLOWED_AMBITOS,
    ALLOWED_ESTADOS_VIGENCIA,
    ALLOWED_TIPOS_OBLIGACION,
    ALLOWED_TIPOS_FUENTE,
)


def test_regulatory_taxonomies_cover_current_seed_values():
    assert "cnmv" in ALLOWED_TIPOS_FUENTE
    assert "sepblac" in ALLOWED_TIPOS_FUENTE
    assert "aml_cft_reporting" in ALLOWED_AMBITOS
    assert "reporting_regulatorio" in ALLOWED_AMBITOS
    assert "vigente" in ALLOWED_ESTADOS_VIGENCIA
    assert "comunicacion_indicio" in ALLOWED_TIPOS_OBLIGACION
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest apps/api/tests/test_taxonomies.py -v`

Expected: FAIL with `ModuleNotFoundError` for `apps.api.domain.taxonomies`.

- [ ] **Step 3: Write minimal taxonomy module**

Crear `apps/api/domain/taxonomies.py`:

```python
ALLOWED_TIPOS_FUENTE = {
    "boe",
    "dgt",
    "teac",
    "cnmv",
    "sepblac",
    "cendoj",
    "eurlex",
    "bde",
    "aepd",
    "bdns",
    "borme",
}

ALLOWED_AMBITOS = {
    "tributario",
    "reporting_regulatorio",
    "reporting_financiero",
    "mercados",
    "aml_cft",
    "aml_cft_reporting",
    "jurisprudencia",
    "fiscal_ue",
    "mercado_interior",
    "competencia_ue",
    "supervision_bancaria",
    "proteccion_datos",
}

ALLOWED_ESTADOS_VIGENCIA = {
    "vigente",
    "historico",
    "derogado",
    "vigente_modificado",
}

ALLOWED_TIPOS_OBLIGACION = {
    "remision_informacion",
    "comunicacion_indicio",
    "presentacion_modelo",
    "control_interno",
    "reporting_prudencial",
}
```

- [ ] **Step 4: Document the controlled vocabulary**

Crear `docs/controlled-vocabulary-regulatorio.md` con una tabla por campo:

```md
# Vocabulario controlado regulatorio

## tipo_fuente
- `cnmv`
- `sepblac`
- `cendoj`
- `eurlex`
- `bde`
- `aepd`

## ambito
- `reporting_regulatorio`
- `reporting_financiero`
- `aml_cft`
- `aml_cft_reporting`
- `jurisprudencia`

## estado_vigencia
- `vigente`
- `historico`
- `derogado`
- `vigente_modificado`
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest apps/api/tests/test_taxonomies.py apps/api/tests/test_smoke.py -k "obligaciones or cnmv or sepblac" -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add docs/controlled-vocabulary-regulatorio.md apps/api/domain/taxonomies.py apps/api/tests/test_taxonomies.py apps/api/schemas.py
git commit -m "feat: add controlled regulatory vocabulary"
```

## Task 3: Create The Wave 1 Source Manifest

**Files:**
- Create: `docs/source-manifests/sociedad-valores-wave-1.md`
- Modify: `docs/regulatory-compliance-expansion-plan.md`

- [ ] **Step 1: Escribir el manifiesto de fuentes prioritarias**

Crear `docs/source-manifests/sociedad-valores-wave-1.md` con esta tabla:

```md
# Sociedad de valores - Wave 1 source manifest

| Fuente | Referencia canonica | Tipo | Prioridad | Estado actual repo | Estado objetivo |
|---|---|---|---|---|---|
| CNMV | Circulares ESI / reporting reservado | documento_regulatorio | P1 | slice inicial | corpus curado |
| SEPBLAC | Ley 10/2010 + RD 304/2014 + Modelo 19 | norma + formulario | P1 | slice inicial | corpus curado |
| EUR-Lex | MiFID II / MiFIR / MAR / PRIIPs / DORA | norma_ue | P1 | parcial | curado |
| CENDOJ | TS / AN / TSJ filtrado | jurisprudencia | P1 | basico | filtrado-curado |
| Banco de Espana | circulares y guias supervisadas | documento_regulatorio | P2 | basico | curado |
| AEPD | resoluciones/guias operativas | guidance | P2 | basico | curado |
```

- [ ] **Step 2: Relacionar el manifiesto con el plan regulatorio existente**

Anadir en `docs/regulatory-compliance-expansion-plan.md` una nota al inicio de Fase 1:

```md
- Manifest de ejecucion recomendado: `docs/source-manifests/sociedad-valores-wave-1.md`
```

- [ ] **Step 3: Commit**

```bash
git add docs/source-manifests/sociedad-valores-wave-1.md docs/regulatory-compliance-expansion-plan.md
git commit -m "docs: add sociedad de valores wave 1 source manifest"
```

## Task 4: Harden Regulatory Corpus Workers

**Files:**
- Modify: `apps/workers/cendoj.py`
- Modify: `apps/workers/eurlex.py`
- Modify: `apps/workers/bde.py`
- Modify: `apps/workers/aepd.py`
- Create: `apps/workers/tests/test_cendoj.py`
- Create: `apps/workers/tests/test_eurlex.py`
- Create: `apps/workers/tests/test_bde.py`
- Create: `apps/workers/tests/test_aepd.py`

- [ ] **Step 1: Write the failing worker smoke tests**

Crear `apps/workers/tests/test_cendoj.py`:

```python
from apps.workers.cendoj import build_document_payload


def test_cendoj_payload_extracts_court_and_type():
    html = b"<html><body>Sentencia Tribunal Supremo 12345/2024</body></html>"
    payload = build_document_payload("https://example.test/cendoj", html)

    assert payload["tipo_fuente"] == "cendoj"
    assert payload["tipo_documento"] == "sentencia"
    assert payload["court"] == "tribunal_supremo"
```

Repetir el mismo patron para:
- `test_eurlex.py` validando `tipo_fuente == "eurlex"`
- `test_bde.py` validando `tipo_fuente == "bde"`
- `test_aepd.py` validando `tipo_fuente == "aepd"`

- [ ] **Step 2: Run tests to verify current gaps**

Run: `pytest apps/workers/tests/test_cendoj.py apps/workers/tests/test_eurlex.py apps/workers/tests/test_bde.py apps/workers/tests/test_aepd.py -q`

Expected: FAIL in at least one parser path or import path until tests are wired correctly.

- [ ] **Step 3: Harden canonical references and metadata**

Aplicar estas reglas minimas en cada worker:

```python
assert payload["referencia"]
assert payload["url_fuente"]
assert payload["tipo_fuente"] in {"cendoj", "eurlex", "bde", "aepd"}
assert payload["tipo_documento"]
assert payload["ambito"]
```

Objetivo tecnico:
- referencias canonicas estables
- `source_url` siempre presente
- `tipo_documento` y `ambito` nunca vacios

- [ ] **Step 4: Run worker tests to verify they pass**

Run: `pytest apps/workers/tests/test_cendoj.py apps/workers/tests/test_eurlex.py apps/workers/tests/test_bde.py apps/workers/tests/test_aepd.py apps/workers/tests/test_cnmv.py apps/workers/tests/test_sepblac.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/workers/cendoj.py apps/workers/eurlex.py apps/workers/bde.py apps/workers/aepd.py apps/workers/tests/test_cendoj.py apps/workers/tests/test_eurlex.py apps/workers/tests/test_bde.py apps/workers/tests/test_aepd.py
git commit -m "feat: harden regulatory source workers"
```

## Task 5: Add Regulated Entity Profile Schema

**Files:**
- Create: `alembic/versions/20260425_0009_reg_entity_profiles.py`
- Create: `apps/api/domain/entity_profiles.py`
- Modify: `apps/api/tests/conftest.py`
- Create: `apps/api/tests/test_entity_profiles.py`

- [ ] **Step 1: Write the failing profile schema test**

Crear `apps/api/tests/test_entity_profiles.py`:

```python
from apps.api.domain.entity_profiles import build_default_sociedad_valores_profile


def test_default_sociedad_valores_profile_contains_core_flags():
    profile = build_default_sociedad_valores_profile()

    assert profile["tipo_entidad"] == "sociedad_valores"
    assert "servicios_inversion" in profile
    assert "reporting_reservado" in profile
    assert "cross_border_ue" in profile
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest apps/api/tests/test_entity_profiles.py -v`

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal domain helper**

Crear `apps/api/domain/entity_profiles.py`:

```python
def build_default_sociedad_valores_profile() -> dict:
    return {
        "tipo_entidad": "sociedad_valores",
        "servicios_inversion": [],
        "tipos_cliente": [],
        "cross_border_ue": False,
        "cross_border_fuera_ue": False,
        "outsourcing_critico": False,
        "reporting_reservado": True,
        "comercializacion_priips": False,
        "aml_cft_reforzado": True,
    }
```

- [ ] **Step 4: Add the migration skeleton**

Crear `alembic/versions/20260425_0009_reg_entity_profiles.py` con una tabla minima:

```python
def upgrade() -> None:
    op.create_table(
        "perfil_entidad_regulada",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("codigo", sa.Text(), nullable=False, unique=True),
        sa.Column("tipo_entidad", sa.Text(), nullable=False),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("jurisdiccion", sa.Text(), nullable=False, server_default="es"),
        sa.Column("flags_json", sa.JSON(), nullable=False),
    )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest apps/api/tests/test_entity_profiles.py apps/api/tests/test_smoke.py -k obligaciones -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add alembic/versions/20260425_0009_reg_entity_profiles.py apps/api/domain/entity_profiles.py apps/api/tests/test_entity_profiles.py apps/api/tests/conftest.py
git commit -m "feat: add regulated entity profile foundation"
```

## Task 6: Add Applicability Engine

**Files:**
- Create: `alembic/versions/20260425_0010_obligacion_aplicabilidad.py`
- Create: `apps/api/services/applicability.py`
- Create: `apps/api/tests/test_applicability.py`
- Modify: `apps/api/routers/obligaciones.py`

- [ ] **Step 1: Write the failing applicability test**

Crear `apps/api/tests/test_applicability.py`:

```python
from apps.api.services.applicability import obligation_applies


def test_reporting_reservado_applies_to_sociedad_valores_profile():
    profile = {
        "tipo_entidad": "sociedad_valores",
        "reporting_reservado": True,
    }
    obligation = {
        "codigo": "CNMV-IR-RESERVADA",
        "sujeto_obligado": "empresa_servicios_inversion",
        "ambito": "reporting_regulatorio",
    }

    assert obligation_applies(profile, obligation) is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest apps/api/tests/test_applicability.py -v`

Expected: FAIL with missing service.

- [ ] **Step 3: Write minimal applicability service**

Crear `apps/api/services/applicability.py`:

```python
def obligation_applies(profile: dict, obligation: dict) -> bool:
    if profile.get("tipo_entidad") != "sociedad_valores":
        return False

    if obligation.get("codigo") == "CNMV-IR-RESERVADA":
        return bool(profile.get("reporting_reservado"))

    if obligation.get("codigo") == "SEPBLAC-INDICIO-M19":
        return True

    return False
```

- [ ] **Step 4: Add minimal API filter for applicable obligations**

Anadir en `apps/api/routers/obligaciones.py` una variante simple de endpoint:

```python
@router.get("/aplicables", response_model=list[dict], operation_id="listar_obligaciones_aplicables")
async def listar_obligaciones_aplicables(tipo_entidad: str = "sociedad_valores"):
    profile = {"tipo_entidad": tipo_entidad, "reporting_reservado": True}
    with db_session() as db:
        rows = db.execute(text("SELECT codigo, sujeto_obligado, ambito, nombre FROM obligacion_regulatoria")).mappings()
        return [dict(row) for row in rows if obligation_applies(profile, dict(row))]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest apps/api/tests/test_applicability.py apps/api/tests/test_smoke.py -k aplicables -q`

Expected: PASS after adding the route-specific smoke assertion.

- [ ] **Step 6: Commit**

```bash
git add alembic/versions/20260425_0010_obligacion_aplicabilidad.py apps/api/services/applicability.py apps/api/tests/test_applicability.py apps/api/routers/obligaciones.py
git commit -m "feat: add obligation applicability foundation"
```

## Task 7: Expand Operational Obligation Model

**Files:**
- Modify: `apps/api/routers/obligaciones.py`
- Modify: `apps/api/schemas.py`
- Modify: `apps/api/tests/conftest.py`
- Modify: `apps/api/tests/test_smoke.py`

- [ ] **Step 1: Write the failing smoke assertion for evidence-required fields**

Anadir en `apps/api/tests/test_smoke.py`:

```python
@pytest.mark.asyncio
async def test_obligaciones_detalle_incluye_operativa_de_control():
    async with _client() as c:
        detalle = await c.get("/v1/obligaciones/SEPBLAC-INDICIO-M19")

    data = detalle.json()
    assert "evidencia_requerida" in data
    assert "owner_rol_sugerido" in data
    assert "criticidad" in data
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest apps/api/tests/test_smoke.py -k operativa_de_control -q`

Expected: FAIL because those keys are not present yet.

- [ ] **Step 3: Extend fixture schema and router payload**

Anadir estas columnas logicas al fixture y al detalle:

```python
"evidencia_requerida": "acuse_presentacion, soporte_revision, expediente_interno",
"owner_rol_sugerido": "compliance",
"criticidad": "alta",
```

Objetivo:
- no modelar aun workflow completo
- si exponer la operativa minima que falta para que la obligacion sea util

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest apps/api/tests/test_smoke.py -k "operativa_de_control or obligaciones" -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/routers/obligaciones.py apps/api/schemas.py apps/api/tests/conftest.py apps/api/tests/test_smoke.py
git commit -m "feat: enrich operational obligation metadata"
```

## Task 8: Expose Applicability In MCP And Consulta

**Files:**
- Modify: `apps/api/mcp_server.py`
- Modify: `apps/api/routers/consulta.py`
- Modify: `apps/api/tests/test_smoke.py`

- [ ] **Step 1: Write the failing consulta applicability smoke test**

Anadir a `apps/api/tests/test_smoke.py`:

```python
@pytest.mark.asyncio
async def test_consulta_devuelve_obligaciones_aplicables_para_sociedad_valores():
    async with _client() as c:
        r = await c.get("/v1/consulta?q=informacion+reservada&tipo_operacion=reporting")

    assert r.status_code == 200
    data = r.json()
    assert any(item["codigo"] == "CNMV-IR-RESERVADA" for item in data["resultados"] if item["tipo"] == "obligacion")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest apps/api/tests/test_smoke.py -k sociedad_valores -q`

Expected: FAIL if consulta still returns only generic obligation aggregation without explicit applicability.

- [ ] **Step 3: Add minimal MCP exposure**

Anadir a `apps/api/mcp_server.py`:

```python
"listar_obligaciones_aplicables",
```

Y en `consulta.py`, al construir resultados de obligaciones, usar `obligation_applies()` para marcar prioridad o filtrar cuando el contexto sea `sociedad_valores`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest apps/api/tests/test_smoke.py -k "sociedad_valores or consulta or obligaciones" -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/mcp_server.py apps/api/routers/consulta.py apps/api/tests/test_smoke.py
git commit -m "feat: expose applicability in consulta and mcp"
```

## Task 9: Add Change Impact Foundation

**Files:**
- Create: `alembic/versions/20260425_0011_change_impact.py`
- Create: `apps/api/routers/cambios.py`
- Create: `apps/api/tests/test_change_impact.py`
- Modify: `apps/api/main.py`

- [ ] **Step 1: Write the failing change impact test**

Crear `apps/api/tests/test_change_impact.py`:

```python
from httpx import ASGITransport, AsyncClient

from main import app


async def test_change_impact_endpoint_lists_seed_changes():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/cambios")

    assert r.status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest apps/api/tests/test_change_impact.py -v`

Expected: FAIL with 404 because router does not exist yet.

- [ ] **Step 3: Add minimal cambios router**

Crear `apps/api/routers/cambios.py`:

```python
from fastapi import APIRouter

router = APIRouter(prefix="/v1/cambios", tags=["cambios"])


@router.get("", operation_id="listar_cambios_regulatorios")
async def listar_cambios_regulatorios():
    return [{
        "codigo": "CAMBIO-CNMV-001",
        "fuente": "cnmv",
        "impacto": "revisar reporting reservado",
        "estado": "nuevo",
    }]
```

Y registrar el router en `apps/api/main.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest apps/api/tests/test_change_impact.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add alembic/versions/20260425_0011_change_impact.py apps/api/routers/cambios.py apps/api/tests/test_change_impact.py apps/api/main.py
git commit -m "feat: add change impact foundation"
```

## Task 10: Connect Changes To Obligations

**Files:**
- Modify: `apps/api/routers/cambios.py`
- Modify: `apps/api/tests/test_change_impact.py`

- [ ] **Step 1: Write the failing impact linkage test**

Anadir a `apps/api/tests/test_change_impact.py`:

```python
async def test_change_impact_includes_affected_obligation_codes():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/cambios")

    data = r.json()
    assert "obligaciones_afectadas" in data[0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest apps/api/tests/test_change_impact.py -q`

Expected: FAIL because the payload lacks `obligaciones_afectadas`.

- [ ] **Step 3: Add minimal linkage payload**

Actualizar el router:

```python
return [{
    "codigo": "CAMBIO-CNMV-001",
    "fuente": "cnmv",
    "impacto": "revisar reporting reservado",
    "estado": "nuevo",
    "obligaciones_afectadas": ["CNMV-IR-RESERVADA"],
    "acciones_sugeridas": ["revisar procedimiento", "validar calendario"],
}]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest apps/api/tests/test_change_impact.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/routers/cambios.py apps/api/tests/test_change_impact.py
git commit -m "feat: link change impact to obligations"
```

## Task 11: Add Compliance Workflow Foundation

**Files:**
- Create: `alembic/versions/20260425_0012_compliance_workflow.py`
- Create: `apps/api/routers/compliance.py`
- Create: `apps/api/tests/test_compliance_workflow.py`
- Modify: `apps/api/main.py`

- [ ] **Step 1: Write the failing workflow test**

Crear `apps/api/tests/test_compliance_workflow.py`:

```python
from httpx import ASGITransport, AsyncClient

from main import app


async def test_compliance_tasks_endpoint_returns_empty_list_initially():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/compliance/tasks")

    assert r.status_code == 200
    assert r.json() == {"tasks": []}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest apps/api/tests/test_compliance_workflow.py -q`

Expected: FAIL with 404.

- [ ] **Step 3: Add minimal compliance router**

Crear `apps/api/routers/compliance.py`:

```python
from fastapi import APIRouter

router = APIRouter(prefix="/v1/compliance", tags=["compliance"])


@router.get("/tasks", operation_id="listar_compliance_tasks")
async def listar_compliance_tasks():
    return {"tasks": []}
```

Registrar router en `apps/api/main.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest apps/api/tests/test_compliance_workflow.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add alembic/versions/20260425_0012_compliance_workflow.py apps/api/routers/compliance.py apps/api/tests/test_compliance_workflow.py apps/api/main.py
git commit -m "feat: add compliance workflow foundation"
```

## Task 12: Secure Internal Compliance Surface

**Files:**
- Modify: `apps/api/main.py`
- Modify: `apps/api/routers/compliance.py`
- Modify: `apps/api/tests/test_compliance_workflow.py`

- [ ] **Step 1: Write the failing auth smoke test for compliance routes**

Anadir a `apps/api/tests/test_compliance_workflow.py`:

```python
async def test_compliance_routes_are_not_public_by_default():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/v1/compliance/tasks")

    assert r.status_code in {401, 403}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest apps/api/tests/test_compliance_workflow.py -q`

Expected: FAIL because the route is still public.

- [ ] **Step 3: Add minimal guard for internal compliance routes**

Usar un header temporal para la primera ola:

```python
from fastapi import Header, HTTPException


def require_internal_api_key(x_internal_api_key: str | None = Header(default=None)):
    if x_internal_api_key != "dev-internal-key":
        raise HTTPException(status_code=401, detail="Missing internal API key")
```

Aplicarlo solo a `/v1/compliance/*` como primer cierre de seguridad.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest apps/api/tests/test_compliance_workflow.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/main.py apps/api/routers/compliance.py apps/api/tests/test_compliance_workflow.py
git commit -m "feat: protect internal compliance routes"
```

## Task 13: Add Minimal Internal UI Contract

**Files:**
- Modify: `docs/architecture.md`
- Modify: `README.md`
- Optional future implementation: `apps/web/*`

- [ ] **Step 1: Document the first internal UI pages**

Anadir a `docs/architecture.md`:

```md
## UI interna futura

La primera UI interna debe consumir solo API existente y exponer:
- perfil regulatorio de entidad
- obligaciones aplicables
- deadlines
- cambios regulatorios
- tareas de compliance
```

- [ ] **Step 2: Reflect the UI contract in README**

Anadir a `README.md`:

```md
- UI interna prevista: mapa de obligaciones aplicables, calendario, cambios regulatorios y workflow de compliance.
```

- [ ] **Step 3: Commit**

```bash
git add docs/architecture.md README.md
git commit -m "docs: define internal compliance ui contract"
```

## Task 14: Final Hardening Pass For This Wave

**Files:**
- Modify: `README.md`
- Modify: `docs/database.md`
- Modify: `docs/architecture.md`
- Modify: `docs/superpowers/plans/2026-04-25-sociedad-valores-compliance-implementation.md`

- [ ] **Step 1: Run the full validation set for this wave**

Run:

```bash
pytest apps/api/tests/test_taxonomies.py apps/api/tests/test_entity_profiles.py apps/api/tests/test_applicability.py apps/api/tests/test_change_impact.py apps/api/tests/test_compliance_workflow.py apps/api/tests/test_smoke.py apps/workers/tests/test_cnmv.py apps/workers/tests/test_sepblac.py apps/workers/tests/test_cendoj.py apps/workers/tests/test_eurlex.py apps/workers/tests/test_bde.py apps/workers/tests/test_aepd.py -q
```

Expected: PASS.

- [ ] **Step 2: Update docs to match final state**

Checklist:
- `README.md` menciona caso de uso `sociedad de valores`
- `docs/database.md` documenta nuevas tablas
- `docs/architecture.md` documenta nuevos routers
- este plan marca tareas completadas

- [ ] **Step 3: Commit documentation sync**

```bash
git add README.md docs/database.md docs/architecture.md docs/superpowers/plans/2026-04-25-sociedad-valores-compliance-implementation.md
git commit -m "docs: sync sociedad de valores implementation state"
```

## Stop Conditions

Detener la ejecucion de la siguiente tarea si ocurre alguno de estos casos:

- el corpus regulatorio sigue siendo demasiado pobre para derivar aplicabilidad fiable
- una taxonomia nueva rompe seeds o smoke tests existentes
- la capa de workflow se intenta construir sin cerrar antes aplicabilidad y seguridad minima
- se detecta que una fuente nueva no tiene referencia canonica estable

## Definition Of Done By Wave

### Wave 1 done
- scope fijado
- vocabulario controlado fijado
- source manifest fijado
- workers regulatorios P1 endurecidos

### Wave 2 done
- perfil de sociedad de valores operativo
- endpoint de obligaciones aplicables operativo
- consulta/MCP reutilizan aplicabilidad

### Wave 3 done
- change impact operativo con obligaciones afectadas

### Wave 4 done
- workflow interno minimo existe y no es publico

### Wave 5 done
- docs y arquitectura reflejan una plataforma de compliance para sociedad de valores, no solo buscador documental
