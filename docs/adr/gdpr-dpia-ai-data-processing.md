# GDPR DPIA — AI Data Processing

## Estado

- Tipo: `ACTIVE`
- Fase: `26.10`
- Alcance: evaluacion de impacto en proteccion de datos para procesamiento de datos personales por componentes de IA

## Objetivo

Documentar la evaluacion de impacto en proteccion de datos (DPIA) para el tratamiento de datos personales en los componentes de IA de `esdata`, identificando riesgos, derechos ARCO+ y medidas de mitigacion conforme al RGPD y la LOPDGDD.

`esdata` procesa datos personales de solicitantes de consultas AI (email, nombre, ip_address, user_agent) con fines de deteccion de contenido generado por IA, evaluacion de equidad y explicabilidad. Esta DPIA fija el registro de riesgos de privacidad, las garantias implementadas y las limitaciones actuales del sistema.

## Contexto regulatorio

- Reglamento General de Proteccion de Datos (UE) 2016/679 (RGPD).
- Ley Organica 3/2018 de Proteccion de Datos Personales y garantia de derechos digitales (LOPDGDD).
- Tratamiento de datos personales en componentes de IA: `email`, `nombre`, `ip_address`, `user_agent`.
- Base legal: consentimiento del interesado, interes legitimo (seguridad y deteccion de abuso).
- Datos especializados: ningun dato especial (categoria especial) se procesa en esta fase.
- Transferencias internacionales: no aplicable en esta fase.

## Datos personales tratados

| Campo | Categoria | Finalidad | Retencion |
|---|---|---|---|
| `email` | Identificador de contacto | Respuesta a consulta y comunicacion con el solicitante | Limitada segun politica de logs |
| `nombre` | Identidad | Personalizacion de la respuesta | Limitada segun politica de logs |
| `ip_address` | Identificador tecnico | Deteccion de abuso, seguridad y auditoria | Limitada segun politica de logs |
| `user_agent` | Identificador tecnico | Analisis de origen de la peticion y deteccion de IA | Limitada segun politica de logs |

## Componentes de alto riesgo

| Componente | Descripcion | Riesgo principal | Nivel |
|---|---|---|---|
| `adversarial_detection` | Deteccion de contenido generado por IA o intentos de evasion | Falsos positivos en clasificacion, discriminacion indirecta | alto |
| `fairness_evaluation` | Evaluacion de equidad en resultados de clasificacion por subgrupos | Sesgo en la medicion de fairness, resultados no representativos | alto |
| `xai` | Explicabilidad de las decisiones del modelo de IA | Revelacion excesiva del modelo, interpretacion erronea por el usuario | medio |
| `human_review` | Supervision humana de decisiones automatizadas criticas | Cuello de botella operativo, inconsistencia en revisiones | medio |
| `ai_risk` | Gestion de riesgos AI con registro y seguimiento | Datos de solicitantes expuestos en registros de riesgo | alto |

## Derechos ARCO+

| Derecho | Implementacion | Servicio | Endpoint | Tests |
|---|---|---|---|---|
| Acceso | Listado de datos personales procesados | `apps/api/services/gdpr.py` | `POST /v1/gdpr/solicitud` | `apps/api/tests/test_gdpr.py` (23 tests) |
| Rectificacion | Actualizacion de datos inexactos | `apps/api/services/gdpr.py` | `POST /v1/gdpr/solicitud` | `apps/api/tests/test_gdpr.py` (23 tests) |
| Supresion | Borrado de datos personales | `apps/api/services/gdpr.py` | `POST /v1/gdpr/solicitud` | `apps/api/tests/test_gdpr.py` (23 tests) |
| Oposicion | Oposicion al tratamiento | `apps/api/services/gdpr.py` | `POST /v1/gdpr/solicitud` | `apps/api/tests/test_gdpr.py` (23 tests) |
| Limitacion | Limitacion del procesamiento | `apps/api/services/gdpr.py` | `POST /v1/gdpr/solicitud` | `apps/api/tests/test_gdpr.py` (23 tests) |
| Portabilidad | Exportacion de datos en formato estructurado | `apps/api/services/gdpr.py` | `POST /v1/gdpr/solicitud` | `apps/api/tests/test_gdpr.py` (23 tests) |

## Registro de riesgos de privacidad

| Risk ID | Categoria | Descripcion | Prob. | Impacto | Score | Severidad | Mitigacion principal | Responsable | Revision |
|---|---|---|---:|---:|---:|---|---|---|---|
| `RISK-PD-001` | `falso_positivo_ia` | Clasificacion erronea de contenido humano como generado por IA | 0.40 | 0.80 | 0.64 | high | Revision humana obligatoria, umbral conservador | equipo AI | mensual |
| `RISK-PD-002` | `sesgo_clasificacion` | Sesgo en la deteccion de IA hacia regiones, lenguas o estilos concretos | 0.30 | 0.70 | 0.58 | high | Evaluacion periodica de fairness, dataset diverso | equipo datos | trimestral |
| `RISK-PD-003` | `retencion_excesiva` | Conservacion prolongada de datos de solicitantes en logs | 0.50 | 0.60 | 0.54 | medium | Politicas de retencion limitadas, purga automatica | seguridad | mensual |
| `RISK-PD-004` | `acceso_no_autorizado` | Acceso a datos personales de solicitantes por terceros | 0.10 | 0.95 | 0.55 | critical | Cifrado en transito y reposo, acceso minimo, signed URLs | seguridad | mensual |
| `RISK-PD-005` | `derechos_arco` | Incumplimiento en respuesta a solicitudes ARCO+ | 0.25 | 0.70 | 0.53 | high | Servicio centralizado con tests, SLA de respuesta | equipo legal | semestral |
| `RISK-PD-006` | `data_leakage_ai` | Filtrado de datos de solicitantes en respuestas o logs del modelo AI | 0.15 | 0.90 | 0.57 | critical | Sanitizacion de inputs/outputs, no log de PII | seguridad | mensual |

Score calculado como `probability * 0.4 + impact * 0.6`.

## Medidas de mitigacion implementadas

- **Minimizacion de datos**: solo se recogen los campos estrictamente necesarios (`email`, `nombre`, `ip_address`, `user_agent`).
- **Pseudonimizacion**: los identificadores directos se separan de los datos de analisis en el procesamiento interno.
- **Cifrado en transito**: TLS obligatorio para todas las comunicaciones externas.
- **Cifrado en reposo**: datos almacenados cifrados con claves gestionadas por infraestructura.
- **Revision humana**: las decisiones automatizadas de alto riesgo pasan por `human_review` antes de ser finales.
- **Retencion limitada de logs**: politica de purga automatica configurada; los logs no retienen PII mas alla del periodo necesario.
- **Validacion de input**: todo dato personal se valida con esquema antes de ser procesado (mass assignment protection).
- **Acceso minimo**: solo componentes autorizados acceden a datos personales; RLS zero policy en base de datos.

## Controles implementados en codigo

- Servicio GDPR: `apps/api/services/gdpr.py`
- Router GDPR: `apps/api/routers/gdpr.py`
- Tests GDPR: `apps/api/tests/test_gdpr.py` (23 tests)
- Seguridad AI: `apps/api/services/adversarial.py`, `apps/api/middleware/ai_safety.py`, `apps/api/routers/ai_safety.py`
- Gestion de riesgos AI: `apps/api/services/ai_risk.py`, `apps/api/routers/ai_risk.py`
- Auditoria AI: `apps/api/services/ai_audit.py`, `apps/api/routers/ai_audit_log.py`

## Monitoreo y operacion

- Revision ordinaria de esta DPIA: semestral, o antes si cambian los componentes de IA, las bases legales o el volumen de tratamiento.
- Incidentes de privacidad: cualquier evento relevante debe registrarse y evaluarse para determinar si requiere notificacion a la autoridad.
- Estado operativo de un riesgo de privacidad: `active`, `monitoring`, `mitigated`, `closed`.
- Los endpoints publicos no deben exponer datos personales ni detalles sensibles de seguridad interna.

## Limitaciones actuales

- Implementacion en memoria: el servicio GDPR y los registros de riesgos viven en memoria, no persistidos en DB. Esto es suficiente para fijar contrato y pruebas, pero no para retencion regulatoria productiva.
- Sin politica de retencion automatizada en almacenamiento persistente: los logs de datos de solicitantes dependen de la configuracion externa de purga.
- Sin registro de consentimientos: no se almacena evidencia del consentimiento otorgado por el interesado.
- Sin mecanismo de portabilidad en formato estructurado: la exportacion de datos no esta implementada.
- Esta DPIA no sustituye un analisis legal formal externo ni una aprobacion del delegado de proteccion de datos.

## Siguientes endurecimientos esperados

1. Persistir registros GDPR y consentimiento en DB con retencion y trazabilidad completa.
2. Implementar exportacion de datos en formato estructurado para portabilidad.
3. Conectar revision humana a flujos de consulta de mayor criticidad con SLA definido.
4. Registrar evidencia de consentimientos y bases legales por tratamiento.
5. Integrar monitoreo automatico de fairness como evidencia continua de la DPIA.
