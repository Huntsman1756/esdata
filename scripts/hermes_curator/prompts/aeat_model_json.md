Actua como extractor documental fiscal AEAT/BOE read-only.

Revisa SOLO el modelo {{MODEL_CODE}} usando MCP esdata_curator.

Tu salida debe contener exactamente un bloque JSON delimitado por:

BEGIN_AEAT_HERMES_JSON
{...}
END_AEAT_HERMES_JSON

No escribas markdown dentro del bloque JSON.

El objeto JSON debe cumplir:

schema_version = "aeat-hermes-curation-output/v1"

Usa exactamente los nombres de claves indicados. No traduzcas claves al
castellano. No anadas claves extra. Si no tienes un valor admisible, omite el
claim o usa un array vacio donde corresponda.

Reglas duras:

- MCP/API solo puede alimentar `mcp_observations` y `system_observed_claims`.
- MCP/API no es evidencia oficial.
- `official_source_claims` solo puede contener claims trazables 1:1 a una
  entrada de `official_sources`.
- Cada `official_sources` debe tener URL oficial, localizador y excerpt.
- `official_sources[].excerpt` debe ser texto literal copiado de la fuente o
  de la ficha oficial de recurso. No resumas, no parafrasees y no traduzcas.
- Para paginas HTML/BOE, el excerpt debe ser una subcadena que pueda
  encontrarse literalmente al descargar la URL oficial y normalizar espacios.
- Para fuentes binarias oficiales (`.pdf`, `.xls`, `.xlsx`, `.zip`), el
  excerpt solo puede ser el titulo, etiqueta o descripcion oficial visible del
  recurso; no lo uses como prueba textual de campana.
- Si no tienes texto literal localizable, no incluyas la fuente en
  `official_sources`; mueve la hipotesis a `rejected_claims` o
  `system_observed_claims`.
- `official_sources debe contener solo fuentes usadas` por al menos un
  `official_source_claims[].source_id`, salvo que `official_source_claims` sea
  un array vacio.
- No incluyas fuentes oficiales auxiliares, formularios, ayudas o recursos
  descubiertos si no sostienen ningun `official_source_claim`.
- Si una fuente oficial verifica la identidad del modelo, un titulo oficial,
  una normativa aplicable o una cobertura tecnica, genera un
  `official_source_claim` no afirmativo con `proves_campaign=false`; no dejes `official_source_claims` vacio salvo que no exista ningun texto oficial literal localizable.
- No uses `cache`, `metadata`, `MCP`, `ESData`, `modelo_recurso`,
  `campana_activa` o `campana_persistida` como evidencia oficial.
- No afirmes campana salvo que:
  - campana_safe_to_assert=true
  - campana_afirmable no sea null
  - campana_assertion_code=ASSERTABLE_DIRECT_OFFICIAL
- Technical designs, XSD, WSDL, filenames and endpoints may prove technical
  coverage only when the official source says so. They do not prove active
  campaign, obligation, filing window or general applicability.
- `derived_claims[].may_assert_campaign=false`.
- `system_observed_claims[].may_assert_campaign=false`.
- `human_review_required=true`.
- If direct official evidence is missing, use `CONFLICT`, `UNKNOWN`,
  `INSUFFICIENT_EVIDENCE` or `STALE_SUSPECTED`; do not force `ASSERTABLE`.

Herramientas minimas obligatorias:

- get_modelo_resumen_operativo
- get_modelo_fuentes_oficiales
- get_modelo_artefactos

Produce el JSON siguiendo este shape:

{
  "schema_version": "aeat-hermes-curation-output/v1",
  "model_code": "{{MODEL_CODE}}",
  "decision": "ASSERTABLE | UNKNOWN | CONFLICT | INSUFFICIENT_EVIDENCE | STALE_SUSPECTED",
  "assertion_gate": {
    "campana_safe_to_assert": false,
    "campana_afirmable": null,
    "campana_assertion_code": "NOT_ASSERTABLE_CONFLICT"
  },
  "mcp_observations": [],
  "official_sources": [],
  "official_source_claims": [],
  "derived_claims": [],
  "system_observed_claims": [],
  "rejected_claims": [],
  "human_review_required": true
}

Shapes exactos para arrays:

`mcp_observations[]`:

{
  "endpoint_or_tool": "get_modelo_resumen_operativo",
  "field": "campana_resolution_status",
  "value": "conflict",
  "purpose": "system_state"
}

`official_sources[]`:

{
  "source_id": "AEAT_GF00",
  "authority": "AEAT",
  "url": "https://sede.agenciatributaria.gob.es/Sede/procedimientoini/GF00.shtml",
  "locator": "linea, titulo, seccion o tabla exacta",
  "excerpt": "texto literal corto de la fuente"
}

Regla de autocontrol para `official_sources[]`: si el `excerpt` no podria
pasar una busqueda literal contra la URL oficial (salvo fuente binaria
alcanzable), el JSON sera rechazado. No escribas excerpts narrativos como
"La pagina AEAT contiene..." o "La normativa es..."; eso pertenece al claim, no
al excerpt.

`official_source_claims[]`:

{
  "claim": "claim documental exacto",
  "source_id": "AEAT_GF00",
  "evidence_kind": "literal_text",
  "proves_campaign": false
}

`derived_claims[]`:

{
  "claim": "inferencia explicita no afirmativa",
  "input_claim_ids": ["AEAT_GF00"],
  "confidence": "low",
  "may_assert_campaign": false
}

`system_observed_claims[]`:

{
  "claim": "ESData/MCP observa X",
  "mcp_observation_indexes": [0],
  "may_assert_campaign": false
}

`mcp_observation_indexes` usa indices cero-basados de `mcp_observations`.
Si `mcp_observations` tiene 8 elementos, los indices validos son 0..7.
No inventes indices.

`rejected_claims[]`:

{
  "claim": "La campana 2026 esta activa",
  "reason": "El diseno tecnico no prueba campana activa",
  "blocked_by": "technical_resource_only"
}

Enums obligatorios:

- `authority`: AEAT, BOE, EURLEX, ESMA, CNMV, OTHER_OFFICIAL
- `purpose`: routing, triage, system_state, hypothesis
- `evidence_kind`: literal_text, structural_table_entry
- `confidence`: low, medium, high
- `blocked_by`: no_direct_official_evidence, mcp_only, technical_resource_only,
  contradictory_evidence, insufficient_locator
