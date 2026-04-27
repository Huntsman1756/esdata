# AI Act Risk Assessment

## Estado

- Tipo: `ACTIVE`
- Fase: `26.3`
- Alcance: framework de riesgos AI para componentes de IA de `esdata`

## Objetivo

Documentar el registro de riesgos AI y las medidas de mitigacion minimas para operar `esdata` como sistema de apoyo fiscal-regulatorio con requisitos reforzados de gobernanza, trazabilidad y supervision.

`esdata` no es un copiloto legal generalista ni debe emitir asesoramiento legal o financiero. El framework aplica a embeddings, retrieval hibrido, componentes LLM y cualquier automatizacion AI conectada a endpoints `AI` del backend.

## Contexto regulatorio

- Referencia principal: Reglamento de IA de la UE para sistemas de alto riesgo.
- Contexto de uso: entidad regulada tipo `sociedad de valores` en Espana.
- Requisitos relevantes: gestion continua de riesgos, transparencia, supervision humana, trazabilidad, calidad de datos y controles de seguridad.

## Registro de riesgos activo

| Risk ID | Categoria | Descripcion | Prob. | Impacto | Score | Severidad | Mitigacion principal | Responsable | Revision |
|---|---|---|---:|---:|---:|---|---|---|---|
| `RISK-001` | `bias_retrieval` | Sesgo en retrieval hacia fuentes o regiones sobrerrepresentadas | 0.60 | 0.70 | 0.66 | high | Evaluacion periodica de cobertura geografica y fairness | equipo datos | trimestral |
| `RISK-002` | `hallucination` | Respuestas no respaldadas por fuentes oficiales | 0.30 | 0.90 | 0.66 | critical | Evidencia obligatoria, disclaimers y trazabilidad de decision | equipo AI | mensual |
| `RISK-003` | `data_leakage` | Filtrado de PII o datos sensibles en respuestas o logs | 0.20 | 0.95 | 0.65 | critical | Sanitizacion, minimizacion de datos y no log de PII | seguridad | mensual |
| `RISK-004` | `prompt_injection` | Manipulacion del modelo mediante instrucciones maliciosas | 0.40 | 0.80 | 0.64 | high | Middleware de seguridad AI, bloqueo conservador y patrones de inyeccion | seguridad | mensual |
| `RISK-005` | `model_degradation` | Degradacion de calidad por drift o version obsoleta | 0.50 | 0.50 | 0.50 | medium | Seguimiento de versiones y reevaluacion periodica | equipo AI | trimestral |
| `RISK-006` | `stale_data` | Datos regulatorios desactualizados en corpus o resultados | 0.50 | 0.70 | 0.62 | high | Workers con deteccion de cambios y control de vigencia | equipo datos | mensual |
| `RISK-007` | `geographic_bias` | Concentracion de cobertura en regiones concretas | 0.50 | 0.50 | 0.50 | medium | Medicion de distribucion geografica y diversificacion de fuentes | equipo datos | trimestral |
| `RISK-008` | `provider_dependency` | Dependencia excesiva de un proveedor/modelo externo | 0.30 | 0.60 | 0.48 | medium | Soporte multi-proveedor y fallback local | arquitectura | semestral |

Score calculado como `probability * 0.4 + impact * 0.6`.

## Controles implementados en codigo

- Registro de riesgos y evaluacion automatizada: `apps/api/services/ai_risk.py`
- Endpoints de consulta y reporte: `apps/api/routers/ai_risk.py`
- Auditoria de decisiones AI: `apps/api/services/ai_audit.py`, `apps/api/routers/ai_audit_log.py`
- Disclaimers AI: `apps/api/services/ai_disclaimer.py`
- Testing adversarial y filtrado de inputs: `apps/api/services/adversarial.py`, `apps/api/middleware/ai_safety.py`, `apps/api/routers/ai_safety.py`

## Monitoreo y operacion

- Revision ordinaria del registro: trimestral, o antes si cambia el modelo, la configuracion o el uso previsto.
- Incidentes: cualquier evento relevante debe registrarse via `POST /v1/ai/risk/report`.
- Estado operativo del riesgo: `active`, `monitoring`, `mitigated`, `closed`.
- Los endpoints publicos no deben exponer detalles sensibles de seguridad interna.

## Riesgos residuales

- El framework actual usa almacenamiento en memoria para el registro y eventos; es suficiente para fijar contrato y pruebas, pero no para retencion regulatoria productiva.
- La explicabilidad, fairness, supervision humana y model registry viven en subfases posteriores y deben reforzar este marco.
- Este documento no sustituye una DPIA ni un analisis legal formal externo.

## Siguiente endurecimiento esperado

1. Persistir `ai_risk_register` y `ai_risk_events` en DB con retencion y trazabilidad.
2. Integrar fairness y explicabilidad como evidencia automatica del riesgo.
3. Conectar supervision humana a flujos de consulta de mayor criticidad.
