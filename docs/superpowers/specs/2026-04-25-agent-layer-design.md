# Esdata Agent Layer — Design Spec

**Fecha:** 2026-04-25
**Estado:** DRAFT
**Fase:** 13 — Capa agentes/copiloto (hibrida)

---

## 1. Objetivo

Exponer esdata como fuente de verdad para agentes de consulta y monitoreo, usando una arquitectura hibrida:
- MCP extendido para consulta externa (cliente LLM orquesta)
- Servicio de monitoreo interno para automatizacion (triggers al workflow de compliance)

No introduce nueva base de datos, nueva UI, ni auth adicional.

---

## 2. Arquitectura hibrida

```
┌─────────────────────────────────────────────┐
│  Cliente LLM (OpenCode, Claude Desktop, etc)│
│  ┌───────────────────────────────────────┐  │
│  │  MCP Client                           │  │
│  │  - agente_consulta                    │  │
│  │  - agente_monitoreo_status            │  │
│  │  - agente_compliance_resumen          │  │
│  └──────────────┬────────────────────────┘  │
└─────────────────┼──────────────────────────┘
                  │ JSON-RPC over stdio/HTTP
┌─────────────────▼──────────────────────────┐
│  esdata API (FastAPI)                      │
│  ┌───────────────────────────────────────┐ │
│  │  MCP Catalog (mcp_catalog.py)         │ │
│  │  - 5 herramientas existentes          │ │
│  │  - 3 nuevas herramientas agente       │ │
│  └───────────────────────────────────────┘ │
│  ┌───────────────────────────────────────┐ │
│  │  Agent Monitor (agent_monitor.py)     │ │
│  │  - Loop interno (cada N minutos)      │ │
│  │  - Escanea cambios regulatorios       │ │
│  │  - Compara con obligaciones aplicables│ │
│  │  - Genera triggers al workflow        │ │
│  └───────────────────────────────────────┘ │
│  ┌───────────────────────────────────────┐ │
│  │  Existing layers                      │ │
│  │  - /v1/cambios                        │ │
│  │  - /v1/obligaciones/aplicables        │ │
│  │  - /v1/compliance/workflow            │ │
│  │  - /v1/consulta                       │ │
│  └───────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

---

## 3. Componentes

### 3.1 MCP Agent Tools

**Archivo:** `apps/api/mcp_agent_tools.py`

Define 3 nuevas herramientas MCP que se registran en el catalogo compartido.

**Herramientas:**

| Nombre | Descripcion | Input |
|---|---|---|
| `agente_consulta` | Consulta fiscal/regulatoria con contexto de entidad obligada | `q` (string), `tipo_entidad` (string, opcional) |
| `agente_monitoreo_status` | Estado actual del servicio de monitoreo interno | Ninguna |
| `agente_compliance_resumen` | Resumen del workflow de compliance con estados y prioridades | `estado` (string, opcional), `limite` (int, opcional) |

**Implementacion:**
- `agente_consulta` → llama a `GET /v1/consulta` con expansion semantica
- `agente_monitoreo_status` → devuelve info del monitor (activo/inactivo, ultimo escaneo, proximo escaneo)
- `agente_compliance_resumen` → llama a `GET /v1/compliance/workflow` con filtros

**Registro:**
- Se anaden a `get_stdio_tool_definitions()` en `mcp_catalog.py`
- El server MCP HTTP (fastapi-mcp) las expone automaticamente via las operaciones existentes

### 3.2 Agent Monitor Service

**Archivo:** `apps/api/agent_monitor.py`

Servicio interno que corre como background task de FastAPI.

**Responsabilidades:**

1. **Escaneo de cambios:** cada N minutos, consulta `GET /v1/cambios` con `estado=pendiente`
2. **Evaluacion:** para cada cambio, verifica si afecta obligaciones aplicables a la entidad
3. **Trigger:** si hay impacto, crea un caso de workflow via `POST /v1/compliance/workflow`
4. **Estado:** expone su estado via la herramienta MCP `agente_monitoreo_status`

**Configuracion (env vars):**

| Variable | Default | Descripcion |
|---|---|---|
| `AGENT_MONITOR_ENABLED` | `false` | Activa/desactiva el monitor |
| `AGENT_MONITOR_INTERVAL` | `300` | Intervalo en segundos (5 min) |
| `AGENT_MONITOR_ENTIDAD` | `sociedad_valores` | Entidad a evaluar |
| `AGENT_MONITOR_PRIORIDAD` | `media` | Prioridad de triggers: baja/media/alta |

**Loop interno:**
```python
async def run_monitor_loop():
    while True:
        await asyncio.sleep(interval)
        await scan_changes()
        await evaluate_impact()
        await create_workflow_triggers()
```

**Sin endpoints nuevos:** el monitor corre internamente, no expone rutas HTTP.

### 3.3 Integration with main.py

**Archivo:** `apps/api/main.py`

- Importar `start_agent_monitor` de `agent_monitor.py`
- Llamar desde el lifespan de FastAPI
- Cleanup al shutdown

### 3.4 LLM Routing (external)

**Archivo:** `apps/api/agent_llm.py` (nuevo, opcional)

Modulo opcional para consumo de LLM externo. Si el usuario quiere que esdata mismo genere respuestas enriquecidas, no solo exponer herramientas.

**Configuracion:**

| Variable | Descripcion |
|---|---|
| `ESDATA_LLM_MODE` | `local` | `external` | `both` |
| `OPENAI_BASE_URL` | Base URL para modelo local (Ollama, etc.) |
| `OPENAI_API_KEY` | API key para modelo externo |
| `OPENAI_MODEL` | Modelo a usar (gpt-4o, claude, etc.) |

**Funcion principal:**
```python
async def generate_enriched_response(query: str, context: dict) -> str:
    """Generate enriched response using configured LLM."""
    # Uses local or external model based on ESDATA_LLM_MODE
```

**Nota:** La routing de LLM la hace principalmente el cliente MCP. Este modulo es para casos donde esdata mismo enriquece la respuesta antes de devolverla al cliente.

---

## 4. Data flow

### 4.1 Consulta (MCP)

```
Cliente LLM → MCP tools/list → [5 existentes + 3 nuevas]
Cliente LLM → MCP tools/call → agente_consulta(q="modelo 349 sanciones")
Esdata → GET /v1/consulta?q=modelo+349+sanciones
Esdata → DB search (full-text + regex)
Esdata → JSON-RPC result → Cliente LLM → Usuario
```

### 4.2 Monitoreo (internal)

```
Agent Monitor (loop) → GET /v1/cambios?estado=pendiente
Agent Monitor → GET /v1/obligaciones/aplicables(tipo_entidad=sociedad_valores)
Agent Monitor → intersecta: cambios que afectan obligaciones aplicables
Agent Monitor → POST /v1/compliance/workflow (nuevo caso)
Workflow DB → actualizado con caso nuevo
Cliente MCP → agente_monitoreo_status → muestra estado actualizado
```

---

## 5. Testing

**Archivo:** `apps/api/tests/test_agent_layer.py`

- Tests de nuevas herramientas MCP (catalogo)
- Tests de agent monitor (mock API calls)
- Tests de integracion con workflow de compliance
- Tests de configuracion (env vars)

**Cobertura minima:**
- `test_agent_tools_in_catalog` — las 3 nuevas tools estan en el catalogo
- `test_agent_consulta_calls_api` — agente_consulta llama a /v1/consulta
- `test_monitor_skipped_when_disabled` — monitor no corre cuando esta desactivado
- `test_monitor_creates_workflow_trigger` — monitor crea caso de workflow
- `test_monitor_status_exposes_info` — agente_monitoreo_status devuelve info correcta
- `test_agent_compliance_resumen_filters` — agente_compliance_resumen filtra por estado

---

## 6. Lo que NO incluye (out of scope)

- Nueva base de datos o migraciones
- UI nueva
- Auth adicional
- Memoria persistente del agente
- Multi-tenancy
- Notificaciones externas (email, webhook, etc.)
- Chat historico
- Vector embeddings para respuestas

---

## 7. Decisiones

| Decision | Eleccion | Motivo |
|---|---|---|
| Arquitectura | Hibrida (MCP + monitor interno) | Balance minimo/funcional |
| Nueva DB | No | Reutiliza workflow_cases existente |
| Nueva UI | No | El cliente MCP es la UI |
| Auth nuevo | No | Reutiliza MCP_API_KEY existente |
| LLM routing | Cliente MCP + modulo opcional | Flexibilidad sin complejidad |
| Monitor como servicio | Background task FastAPI | Sin infra nueva |

---

## 8. Archivos afectados

| Archivo | Accion | Descripcion |
|---|---|---|
| `apps/api/mcp_catalog.py` | Modificar | Anadir 3 nuevas herramientas |
| `apps/api/mcp_stdio.py` | Modificar | Consumir nuevas herramientas del catalogo |
| `apps/api/agent_monitor.py` | Nuevo | Servicio de monitoreo interno |
| `apps/api/agent_llm.py` | Nuevo (opcional) | Modulo LLM externo |
| `apps/api/main.py` | Modificar | Integrar monitor en lifespan |
| `apps/api/tests/test_agent_layer.py` | Nuevo | Tests de capa agente |
| `README.md` | Modificar | Documentar capa agente |
