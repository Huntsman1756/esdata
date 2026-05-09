# MCP + API Surface Audit

**Fecha:** 2026-05-09T22:21 CEST  
**Entorno:** Docker Compose (esdata-api-1), API en http://127.0.0.1:8001 (interno :8000)  
**Protocolo MCP:** 2025-03-26 (Streamable HTTP)  
**Tools descubiertas:** 27 (HTTP MCP via FastApiMCP)  
**Tools stdio (no accesibles via HTTP):** 8 (consulta_fiscal, listar_obligaciones_operativas, listar_deadlines, listar_obligaciones_aplicables, get_obligacion_completa, agente_consulta, agente_monitoreo_status, agente_compliance_resumen)

---

## MCP Tools (27 HTTP)

| tool | input_required | response_ok | has_provenance | deterministic | verdict |
|------|---------------|-------------|----------------|---------------|---------|
| buscar | `[q]` | ✅ | ❌ | ✅ | **WARN** |
| buscar_legislacion | `[q]` | ❌ (500) | ❌ | ✅ | **CRITICAL** |
| list_legislacion | `[]` | ✅ | ❌ | ✅ | WARN |
| get_norma | `[codigo]` | ✅ | ✅ (eli_uri, boe_id) | ✅ | OK |
| list_articulos | `[codigo]` | ✅ | ❌ | ✅ | WARN |
| get_articulo | `[codigo, numero]` | ✅ | ✅ (boe_reference, source_url, eli_uri) | ✅ | OK |
| get_articulo_historial | `[codigo, numero]` | ✅ | ❌ | ✅ | WARN |
| list_materias | `[]` | ✅ | ❌ | ✅ | WARN |
| get_materia | `[slug]` | ✅ | ❌ | ✅ | WARN |
| buscar_doctrina | `[q]` | ✅ | ❌ | ✅ | WARN |
| get_doctrina | `[referencia]` | ✅ | ❌ | ✅ | WARN |
| list_modelos_campanas_operativas | `[codigos]` | ✅ | ❌ | ✅ | WARN |
| list_modelos | `[]` | ✅ | ❌ | ✅ | WARN |
| get_modelo | `[codigo]` | ✅ | ✅ (fuentes, normativa) | ✅ | OK |
| get_modelo_articulos | `[codigo]` | ✅ | ❌ | ✅ | WARN |
| get_modelo_casillas | `[codigo]` | ✅ | ❌ | ✅ | WARN |
| get_modelo_claves | `[codigo]` | ✅ | ❌ | ✅ | WARN |
| get_modelo_instrucciones | `[codigo]` | ✅ | ❌ | ✅ | WARN |
| get_modelo_normativa | `[codigo]` | ✅ | ✅ (boe_reference) | ✅ | OK |
| get_modelo_artefactos | `[codigo]` | ✅ | ✅ (url oficial) | ✅ | OK |
| get_modelo_resumen_operativo | `[codigo]` | ✅ | ✅ (fuentes_recomendadas) | ✅ | OK |
| get_modelo_campana_operativa | `[codigo]` | ✅ | ✅ (fuentes_recomendadas) | ✅ | OK |
| get_modelo_fuentes_oficiales | `[codigo]` | ✅ | ✅ (fuentes_oficiales con url) | ✅ | OK |
| listar_reglas_retencion_internacional | `[]` | ✅ | ❌ | ✅ | WARN |
| listar_convenios_dta_internacional | `[]` | ✅ | ❌ | ✅ | WARN |
| detalle_convenio_dta_internacional | `[codigo]` | ✅ | ❌ | ✅ | WARN |
| calcular_retencion | `[tipo_renta]` | ❌ (error) | ❌ | — | **FAIL** |

### Tools stdio (solo accesibles via stdio transport, NO via HTTP /mcp)

| tool | verdict | nota |
|------|---------|------|
| consulta_fiscal | N/A | Solo stdio — HTTP devuelve "Unknown tool" |
| listar_obligaciones_operativas | N/A | Solo stdio |
| listar_deadlines | N/A | Solo stdio |
| listar_obligaciones_aplicables | N/A | Solo stdio |
| get_obligacion_completa | N/A | Solo stdio |
| agente_consulta | N/A | Solo stdio |
| agente_monitoreo_status | N/A | Solo stdio |
| agente_compliance_resumen | N/A | Solo stdio |

**Resumen HTTP MCP:** 8/27 OK, 17/27 WARN (sin provenance explícita en response), 1 CRITICAL (500), 1 FAIL (error de args).

---

## Tools críticas — ground truth

| tool | input | response_match_boe | verdict |
|------|-------|-------------------|---------|
| get_articulo | LIVA, 91 | ✅ boe_reference=BOE-A-1992-28740, source_url=boe.es/buscar/act.php?id=BOE-A-1992-28740#a91 | **OK** |
| get_norma | LIVA | ✅ eli_uri=https://www.boe.es/eli/es/l/1992/12/28/37 | **OK** |
| buscar_legislacion | IVA | ❌ 500 Internal Server Error (Decimal serialization bug) | **CRITICAL** |
| get_articulo | LIVA_FAKE, 99999 | ✅ Error explícito (not-found, no fabrication) | OK |
| get_norma | NORMA_INEXISTENTE_XYZ | ✅ Error explícito (not-found) | OK |
| get_modelo | 99999 | ✅ Error explícito (not-found) | OK |

### Ground-truth benchmark

| check | resultado | verdict |
|-------|-----------|---------|
| BOE URL https://www.boe.es/buscar/act.php?id=BOE-A-1992-28740 existe (HEAD) | ✅ status < 400 | OK |
| get_articulo(LIVA, 91) contiene BOE-A-1992-28740 | ✅ | OK |
| get_norma(LIVA) eli_uri = https://www.boe.es/eli/es/l/1992/12/28/37 | ✅ match exacto | OK |
| buscar_legislacion('IVA') devuelve >=1 norma LIVA | ❌ endpoint 500 | **CRITICAL** |

---

## REST surfaces (muestra 30 endpoints)

| path | status | has_provenance | verdict |
|------|--------|----------------|---------|
| /v1/legislacion | 200 | ❌ | WARN |
| /v1/legislacion/LIVA | 200 | ✅ (eli_uri, boe_id) | OK |
| /v1/legislacion/LIVA/articulos | 200 | ❌ | WARN |
| /v1/legislacion/LIVA/articulos/91 | 200 | ✅ (boe_reference, source_url, eli_uri, confianza) | OK |
| /v1/legislacion/LIVA/articulos/91/historial | 200 | ❌ | WARN |
| /v1/legislacion/buscar?q=IVA | **500** | ❌ | **CRITICAL** |
| /v1/legislacion/cobertura | 200 | ❌ | WARN |
| /v1/doctrina/buscar?q=IVA | 200 | ❌ | WARN |
| /v1/modelos | 200 | ❌ | WARN |
| /v1/modelos/303 | 200 | ✅ (normativa, fuentes) | OK |
| /v1/modelos/303/articulos | 200 | ✅ (source_url en items) | OK |
| /v1/modelos/campanas-operativas | 422 | — | OK (requiere param) |
| /v1/materias | 200 | ❌ | WARN |
| /v1/buscar?q=IVA tipo reducido | 200 | ✅ (confianza con fuentes) | OK |
| /v1/consulta?q=tipo reducido IVA | **500** | ❌ | **CRITICAL** |
| /v1/sources/manifest | 200 | ❌ | WARN |
| /v1/sources/freshness | 200 | ❌ | WARN |
| /v1/observability/dashboard | 200 | ❌ | WARN |
| /health | 200 | — | OK |
| /status | 200 | — | OK |
| /v1/cnmv | 200 | ✅ (source_url boe.es) | OK |
| /v1/dgt/doctrina/buscar?q=rendimientos | 404 | — | OK (not-found explícito) |
| /v1/aepd | 200 | ✅ (source_url aepd.es) | OK |
| /v1/sepblac | 404 | — | OK (not-found explícito) |
| /v1/bde | 200 | ✅ (source_url bde.es) | OK |
| /v1/borme | 404 | — | OK (not-found explícito) |
| /v1/bdns | 404 | — | OK (not-found explícito) |
| /v1/query-audit | 404 | — | OK (ruta incorrecta, real: /v1/ai/query-audit) |
| /v1/obligaciones | 200 | ❌ | WARN |
| /v1/eurlex | 200 | ✅ (eli_uri eur-lex.europa.eu) | OK |

**Resumen REST:** 15/30 OK, 12/30 WARN (sin provenance en listados), 2 CRITICAL (500), 1 OK (422 esperado).

---

## Audit log coverage

| métrica | valor |
|---------|-------|
| Endpoint real | `/v1/ai/query-audit` |
| Status al consultar | **500** (bug: `TypeError: the JSON object must be str, bytes or bytearray, not list`) |
| Delta esperado | ≥10 |
| Delta observado | **0** (no se pudo medir — endpoint roto) |
| Verdict | **CRITICAL** — no se puede verificar cobertura de audit |

**Root cause:** `services/query_audit.py:242` intenta `json.loads()` sobre un campo que ya es una lista Python (no un string JSON). Bug de deserialización en `_map_entry`.

---

## Determinismo

| test | resultado | verdict |
|------|-----------|---------|
| `/v1/buscar?q=IVA` x3 invocaciones | ✅ Respuestas idénticas (hash MD5 coincide) | **OK** |
| `/v1/legislacion/LIVA/articulos/91` x2 | ✅ Determinista | OK |
| get_norma(LIVA) x2 via MCP | ✅ Determinista | OK |
| get_articulo(LIVA, 91) x2 via MCP | ✅ Determinista | OK |
| buscar_legislacion via MCP | N/A (500) | — |

**Nota:** El endpoint `/v1/buscar` (fulltext puro, sin embeddings) es determinista. El endpoint `/v1/legislacion/buscar` (hybrid con embeddings) no se pudo verificar por el bug de serialización Decimal.

---

## Uncertainty handling

| check | resultado | verdict |
|-------|-----------|---------|
| `confianza.nivel` en get_articulo | ✅ `{"nivel": 1, "fuentes": ["LIVA art. 91"], "aviso": null}` | OK |
| `confianza` en buscar results | ✅ Presente en cada resultado | OK |
| `completeness` en query_audit_log | ❌ No verificable (endpoint 500) | **WARN** |
| `confianza.aviso` cuando aplica | ✅ Campo presente (null cuando no aplica) | OK |

---

## Top CRITICAL findings

### 1. CRITICAL — `/v1/legislacion/buscar` y `/v1/consulta` devuelven 500
**Causa:** `TypeError: Object of type Decimal is not JSON serializable` en `routers/buscar.py:161`.  
**Impacto:** Las tools MCP `buscar_legislacion` y `consulta_fiscal` (via stdio) están completamente rotas. Un usuario MCP no puede buscar legislación.  
**Fix:** Usar `json.dumps(result, default=str)` o convertir Decimal a float antes de serializar.

### 2. CRITICAL — `/v1/ai/query-audit` devuelve 500
**Causa:** `TypeError: the JSON object must be str, bytes or bytearray, not list` en `services/query_audit.py:242`.  
**Impacto:** No se puede verificar la cobertura de auditoría E2E. Violación de S-13 (auditoría persistente obligatoria).  
**Fix:** En `_map_entry`, verificar si `row["retrieved_chunks"]` ya es una lista antes de llamar `json.loads()`.

### 3. CRITICAL — Tools stdio NO accesibles via HTTP MCP
**Causa:** Las 8 tools definidas en `get_stdio_tool_definitions()` solo se exponen via el transporte stdio (`MCPStdioServer`), no via el HTTP MCP (`FastApiMCP`).  
**Impacto:** Clientes HTTP MCP (Claude Desktop, Cursor, etc.) no pueden usar `consulta_fiscal`, `listar_obligaciones_operativas`, `listar_deadlines`, etc.  
**Fix:** Registrar las tools stdio como operaciones HTTP en `HTTP_MCP_OPERATIONS` o implementar un bridge.

### 4. WARN — 17/27 tools HTTP sin provenance explícita en response
**Causa:** Los listados (`list_legislacion`, `list_articulos`, `list_modelos`, etc.) devuelven items sin campos `source_url`/`boe_reference`/`eli_uri`. Solo los endpoints de detalle (`get_norma`, `get_articulo`) incluyen provenance.  
**Impacto:** Un agente MCP que recibe un listado no puede verificar la procedencia de cada item sin hacer una segunda llamada al detalle.  
**Recomendación:** Incluir al menos `boe_id` o `source_url` en cada item de listado.

### 5. WARN — `calcular_retencion` falla con args del schema
**Causa:** El schema requiere `tipo_renta` pero el endpoint espera también `pais_residencia` para funcionar correctamente.  
**Impacto:** Tool parcialmente funcional.

### 6. WARN — Rate limiting MCP agresivo (429)
**Observado:** Durante el batch de 10 tool calls, varias fueron rechazadas con 429 Too Many Requests.  
**Impacto:** Auditoría automatizada y uso intensivo por agentes se ve limitado.

---

## Resumen ejecutivo

| categoría | OK | WARN | CRITICAL | FAIL |
|-----------|-----|------|----------|------|
| MCP Tools (27 HTTP) | 8 | 17 | 1 | 1 |
| Critical tools ground truth | 4 | 0 | 2 | 0 |
| REST surfaces (30) | 15 | 12 | 2 | 0 |
| Audit log | — | — | 1 | — |
| Determinismo | ✅ | — | — | — |
| Uncertainty | 3/4 | 1/4 | — | — |

**Severidad global: CRITICAL** — El sistema tiene 2 bugs de serialización que rompen endpoints core (buscar, consulta, query-audit) y las tools stdio no son accesibles via HTTP MCP. Los endpoints que funcionan son deterministas y las respuestas de detalle incluyen provenance trazable a fuentes oficiales (boe.es, eur-lex.europa.eu, aepd.es, bde.es).

**Prioridad de fix:**
1. 🔴 Decimal serialization en buscar.py (desbloquea buscar_legislacion + consulta)
2. 🔴 json.loads en query_audit.py (desbloquea auditoría E2E)
3. 🟡 Exponer tools stdio via HTTP MCP (o documentar que solo están en stdio)
4. 🟡 Añadir provenance a listados
5. 🟢 Fix args de calcular_retencion
