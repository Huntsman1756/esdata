# Master Execution Roadmap

## Estado del documento

- Tipo: `ACTIVE`
- Proposito: unica fuente activa de roadmap, estado actual y siguiente paso exacto
- Autoridad: este documento manda sobre cualquier roadmap, handoff o plan historico del repo, salvo conflicto con `AGENTS.md`

---

## Objetivo del producto

`esdata` es una capa de datos y consulta fiscal-regulatoria con trazabilidad a fuente oficial.

El objetivo no es convertir `esdata` en un copiloto legal generalista. El objetivo es fortalecer la base fiscal y regulatoria ya existente para soportar:

- investigacion fiscal con trazabilidad oficial
- workflows de compliance operativo
- agentes internos y copilots con contexto fiable
- futuras capas privadas superpuestas sobre corpus publico

Entidad regulada prioritaria actual:

- `sociedad de valores` en Espana

Fuera de alcance inicial:

- legal horizontal generalista
- litigacion civil/laboral amplia
- mezclar conocimiento privado del cliente con corpus publico base

---

## Estado ejecutivo actual

- Profesionalizacion del repo: `COMPLETA`
- Retrieval, chunking y evaluacion: `COMPLETO` con gate aprobado
- Corpus regulatorio prioritario: `PARCIAL PERO OPERATIVO`
- Perfil regulatorio y aplicabilidad inicial: `OPERATIVO`
- Obligaciones operativas enriquecidas: `OPERATIVO`
- Change impact: `EN CURSO`
- Workflow de compliance: `PENDIENTE`
- UI interna minima: `PENDIENTE`

Estado tecnico consolidado:

- despliegue de referencia: Docker Compose
- Railway: `DEPRECATED` e historico
- migraciones: Alembic como via oficial
- arquitectura: workers por fuente + routers FastAPI + PostgreSQL + MCP/API

---

## Decisiones estructurales vigentes

- `AGENTS.md` define seguridad, disciplina de trabajo y restricciones operativas.
- Este documento es la unica fuente activa de roadmap y handoff.
- `sociedad de valores` es la entidad regulada objetivo para la ola actual.
- La arquitectura actual se preserva: workers por fuente, routers por dominio/fuente, almacenamiento compartido y trazabilidad oficial.
- Nuevas capas deben favorecer cambios minimos y reversibles.
- No se debe introducir persistencia nueva prematuramente si el contrato funcional aun no esta estable.
- La documentacion del repo debe poder ser consumida por modelos pequenos, medianos o grandes sin depender de ventanas de contexto masivas.

---

## Norma fija de trabajo del repo

Este repositorio debe poder ser trabajado por cualquier LLM o agente sin depender de memoria conversacional larga ni de grandes ventanas de contexto.

Reglas permanentes:

1. una sola fuente activa de estado y ejecucion
2. una sola fase activa cada vez
3. un solo siguiente paso exacto
4. contexto minimo suficiente, no contexto maximo
5. slices pequenos, verificables y reversibles
6. toda afirmacion de exito requiere verificacion fresca
7. el estado actual se actualiza en un unico sitio

### Jerarquia obligatoria de lectura

Orden obligatorio:

1. `AGENTS.md`
2. `docs/master-execution-roadmap.md`
3. archivos de codigo directamente afectados
4. una documentacion tecnica adicional solo si la fase actual lo requiere
5. documentos historicos solo si hay bloqueo real

### Politica de contexto minima

- no cargar documentos completos por defecto
- no cargar mas de una fase completa a la vez
- no cargar mas de un documento historico por iteracion
- no arrastrar handoffs completos entre sesiones
- siempre resumir antes de expandir

Antes de empezar cualquier tarea, el agente debe reducir el contexto a:

- fase actual
- tarea actual
- criterio de exito
- archivos afectados
- restricciones no negociables

### Slice minimo obligatorio

Secuencia obligatoria por iteracion:

1. identificar fase y siguiente paso exacto
2. anadir o ejecutar verificacion
3. hacer el cambio minimo
4. volver a verificar
5. actualizar el resumen vivo
6. dejar el siguiente paso exacto

### Confirmaciones obligatorias

Se requiere confirmacion explicita del usuario antes de:

- pasar a una nueva fase
- introducir migraciones no triviales
- tocar auth, autorizacion, tenancy o seguridad sensible
- eliminar documentos o mover historicos
- ejecutar operaciones destructivas en git

### Antipatrones prohibidos

- empezar leyendo varios roadmaps a la vez
- usar el handoff mas reciente como sustituto del roadmap maestro
- mantener el mismo estado operativo en varios documentos activos
- cargar contexto completo "por si acaso"
- trabajar varias fases en paralelo sin control
- afirmar exito sin evidencia fresca
- crear nuevos planes activos sin integrarlos aqui

---

## Resumen vivo

- Objetivo actual: cerrar la capa minima de `change impact` y preparar la transicion hacia workflow de compliance
- Estado actual: `/v1/cambios` existe con contrato minimo, enlace a obligaciones afectadas y filtros operativos por `fuente`, `estado` y `prioridad`
- Decisiones tomadas:
  - no persistir cambios en DB todavia
  - extraer el payload del router a `apps/api/change_impact_data.py`
  - mantener el trabajo en slices pequenos con tests especificos
  - consolidar el contrato minimo antes de introducir persistencia o workflow
- Restricciones no negociables:
  - no reabrir profesionalizacion ya cerrada salvo bug real
  - no usar Railway
  - no repartir el estado actual entre varios markdowns
- Archivos relevantes:
  - `apps/api/routers/cambios.py`
  - `apps/api/change_impact_data.py`
  - `apps/api/tests/test_change_impact.py`
  - `apps/api/obligaciones_metadata.py`
  - `apps/api/applicability.py`
- Riesgos o dudas abiertas:
  - decidir cuando pasar de semilla a persistencia real
  - decidir si el siguiente filtro debe ser `obligacion_afectada`
  - definir el primer slice de workflow de compliance sin inflar scope
- Siguiente paso exacto:
  - anadir filtro por `obligacion_afectada` en `/v1/cambios` con tests primero y sin introducir persistencia aun

---

## Roadmap maestro por fases

## Fase 0 — Reglas operativas y contexto

### Estado
- `ACTIVA COMO NORMA PERMANENTE`

### Objetivo
- reducir coste de contexto
- eliminar ambiguedad documental
- permitir trabajo estable con cualquier LLM

### Entregables
- este documento maestro
- jerarquia documental unica
- resumen vivo obligatorio
- protocolo permanente de trabajo

### Criterio de exito
1. el repo puede retomarse leyendo solo `AGENTS.md` y este documento
2. el estado actual no depende de handoffs largos
3. cualquier agente puede identificar fase activa y siguiente paso exacto sin explorar varios planes

### Instrucciones para agentes
- leer solo esta fase, el resumen vivo y la fase activa
- no abrir docs historicos salvo bloqueo real

---

## Fase 1 — Baseline tecnico y profesionalizacion

### Estado
- `COMPLETA`

### Objetivo
- dejar arquitectura, DB, despliegue, operaciones y calidad en estado profesionalizable y portable

### Entregables consolidados
- arquitectura documentada
- estructura del repo documentada
- variables de entorno documentadas
- despliegue portable con Docker Compose
- estrategia de migraciones con Alembic
- runbooks operativos
- CI reforzada
- evaluacion final aprobada

### Criterio de exito
1. infraestructura puede operar el sistema con autonomia razonable
2. el despliegue no depende de Railway
3. la base tecnica no necesita reabrirse salvo bug o necesidad de infraestructura real

### Instrucciones para agentes
- no releer esta fase salvo tareas de infra, ops, DB, CI o deployment
- usar `docs/database.md`, `docs/deployment/*` y `docs/operations/*` solo si la tarea cae en ese dominio

---

## Fase 2 — Retrieval, chunking y evaluacion

### Estado
- `COMPLETA`

### Objetivo
- consolidar chunking, mejora de recuperacion y evaluacion reproducible del sistema

### Entregables consolidados
- plan de chunking ejecutado
- retrieval mejorado
- evaluacion final aprobada
- observabilidad avanzada integrada

### Criterio de exito
1. existe base estable de retrieval/eval
2. no hace falta releer el plan tecnico salvo tareas de busqueda, ranking, embeddings o chunks

### Instrucciones para agentes
- consultar `docs/plan-fase2-chunking.md` solo si la tarea afecta a chunking o retrieval
- no usar esta fase para justificar cambios ajenos a busqueda/evaluacion

---

## Fase 3 — Scope y taxonomia de sociedad de valores

### Estado
- `COMPLETA`

### Objetivo
- fijar entidad regulada objetivo y vocabulario regulatorio base

### Entregables consolidados
- `docs/sociedad-valores-scope.md`
- `docs/controlled-vocabulary-regulatorio.md`
- `apps/api/taxonomies.py`
- baseline de tests regulatorio recuperado

### Criterio de exito
1. `sociedad de valores` fijada como entidad objetivo actual
2. vocabulario controlado base definido
3. harness de tests utilizable y verde

### Instrucciones para agentes
- tomar esta fase como fuente unica del vocabulario de negocio regulatorio
- no redefinir taxonomias sin reflejarlo en docs y tests

---

## Fase 4 — Corpus regulatorio prioritario

### Estado
- `PARCIAL`

### Objetivo
- endurecer corpus y metadatos de las fuentes regulatorias prioritarias para `sociedad de valores`

### Alcance prioritario
- `CNMV`
- `SEPBLAC`
- `CENDOJ`
- `EUR-Lex`
- siguiente ola: `Banco de Espana`, `AEPD`

### Entregables actuales
- workers endurecidos para `CNMV`, `SEPBLAC`, `CENDOJ`, `EUR-Lex`
- tests de worker para `CENDOJ` y `EUR-Lex`
- router `CENDOJ` corregido

### Gap abierto
- tests especificos de router para `CENDOJ` y `EUR-Lex`
- densificar corpus de `BDE` y `AEPD`

### Criterio de exito
1. corpus P1 fiable y trazable
2. referencias canonicas estables
3. tests de worker y router suficientes para las fuentes principales

### Instrucciones para agentes
- trabajar fuente por fuente
- no mezclar varias fuentes en la misma iteracion salvo necesidad real
- usar el manifest `docs/source-manifests/sociedad-valores-wave-1.md` solo como referencia de prioridad, no como estado vivo

---

## Fase 5 — Perfil regulatorio, aplicabilidad y obligaciones operativas

### Estado
- `OPERATIVA MINIMA COMPLETADA`

### Objetivo
- convertir corpus regulatorio en obligaciones utiles y aplicables a una entidad concreta

### Entregables actuales
- perfil base `sociedad_valores`
- motor minimo de aplicabilidad
- endpoint `/v1/obligaciones/aplicables`
- metadata operativa enriquecida en obligaciones
- exposicion por API y MCP

### Criterio de exito
1. existe perfil regulatorio base
2. se puede calcular aplicabilidad inicial
3. las obligaciones tienen metadata operativa minima usable

### Instrucciones para agentes
- si se anaden nuevas reglas, hacerlo en slices pequenos y verificables
- una regla de aplicabilidad por iteracion cuando haya ambiguedad de negocio
- verificar siempre impacto en tests especificos o smoke

---

## Fase 6 — Change impact

### Estado
- `EN CURSO`

### Objetivo
- introducir una capa minima de cambios regulatorios conectada con obligaciones afectadas

### Entregables actuales
- `GET /v1/cambios`
- router `apps/api/routers/cambios.py`
- modulo `apps/api/change_impact_data.py`
- contrato minimo de cambio
- enlace `cambio -> obligaciones_afectadas`
- campos operativos:
  - `accion_recomendada`
  - `prioridad`
  - `fecha_detectado`
  - `estado`
- filtros basicos:
  - `fuente`
  - `estado`
  - `prioridad`

### Gap abierto
1. filtro por `obligacion_afectada`
2. decidir cuando pasar a persistencia real
3. preparar transicion hacia workflow de compliance

### Archivos clave
- `apps/api/routers/cambios.py`
- `apps/api/change_impact_data.py`
- `apps/api/tests/test_change_impact.py`

### Criterio de exito
1. `/v1/cambios` devuelve contrato estable
2. permite filtrar por dimensiones operativas basicas
3. existe vinculo explicito con obligaciones afectadas
4. tests verdes

### Instrucciones para agentes
- no introducir migracion aun salvo contrato estable y necesidad real
- primero contrato + tests + filtros
- luego persistencia si sigue teniendo sentido

---

## Fase 7 — Workflow de compliance

### Estado
- `PENDIENTE`

### Objetivo
- pasar de cambio detectado a accion gestionada con trazabilidad operativa

### Alcance recomendado
- estado interno del caso
- owner responsable
- evidencia requerida
- checklist minima
- trazabilidad `cambio -> obligacion -> accion`

### Criterio de exito
1. existe una unidad operativa minima de seguimiento
2. el cambio deja de ser solo informativo y pasa a ser accionable
3. el modelo se puede exponer por API antes de UI

### Instrucciones para agentes
- no empezar por interfaz
- empezar por contrato y API minima
- mantener workflow corto y explicito

---

## Fase 8 — Seguridad y tenancy de la capa interna

### Estado
- `PENDIENTE`

### Objetivo
- endurecer la superficie interna si aparece una capa privada real de operaciones/compliance

### Criterio de exito
1. auth y permisos claros
2. validaciones y separacion de datos correctamente definidas
3. sin concesiones a reglas S-TIER

### Instrucciones para agentes
- cualquier cambio de auth, tenancy o schema sensible requiere confirmacion explicita
- aplicar checklist S-TIER de `AGENTS.md`

---

## Fase 9 — UI interna minima

### Estado
- `PENDIENTE`

### Objetivo
- exponer workflow y cambios mediante una interfaz minima interna

### Criterio de exito
1. la UI consume una API ya estable
2. no introduce logica de negocio en frontend
3. sigue el workflow ya definido en backend

### Instrucciones para agentes
- no abrir esta fase hasta que la fase 7 tenga contrato estable
- preservar backend-first

---

## Fase 10 — Hardening final

### Estado
- `PENDIENTE`

### Objetivo
- cerrar deuda residual de observabilidad, tests, docs y operacion

### Criterio de exito
1. gaps relevantes de tests cerrados
2. documentacion activa limpia y coherente
3. operacion y trazabilidad finales consistentes

### Instrucciones para agentes
- usar esta fase solo cuando el flujo principal ya sea operativo

---

## Fase activa

- Fase activa: `Fase 6 — Change impact`
- Estado: `EN CURSO`
- Archivos principales:
  - `apps/api/routers/cambios.py`
  - `apps/api/change_impact_data.py`
  - `apps/api/tests/test_change_impact.py`

---

## Siguiente paso exacto

Anadir filtro por `obligacion_afectada` en `/v1/cambios` con tests primero y sin introducir persistencia todavia.

---

## Criterios de cierre por fase

Toda fase se considera correctamente cerrada cuando:

1. el contrato funcional de la fase esta definido y estable a su nivel de detalle
2. los tests relevantes del bloque estan en verde
3. el `Resumen vivo` esta actualizado
4. el siguiente paso exacto de la siguiente fase o subfase queda escrito aqui

---

## Indice de documentos REFERENCE / HISTORICAL

| Documento | Estado | Uso permitido |
|---|---|---|
| `docs/master-execution-roadmap.md` | `ACTIVE` | fuente principal |
| `docs/professionalization-roadmap.md` | `REFERENCE` | solo contexto de infra, ops, DB, CI y calidad |
| `docs/fiscal-regulatory-expansion-roadmap.md` | `REFERENCE` | solo estrategia regulatoria |
| `docs/regulatory-compliance-expansion-plan.md` | `REFERENCE` | canon conceptual del bloque compliance |
| `docs/plan-fase2-chunking.md` | `REFERENCE` | solo retrieval, chunks y ranking |
| `docs/next-session-handoff-2026-04-25.md` | `REFERENCE` | detalle historico reciente si hace falta |
| `docs/next-session-handoff-2026-04-22.md` | `HISTORICAL` | no leer por defecto |
| `docs/next-session-handoff-2026-04-16.md` | `HISTORICAL` | no leer por defecto |
| `docs/next-session-handoff-2026-04-12.md` | `HISTORICAL` | no leer por defecto |
| `docs/dgt-mvp-implementation-plan.md` | `HISTORICAL` | no usar como plan activo |
| `docs/superpowers/plans/2026-04-25-sociedad-valores-compliance-implementation.md` | `REFERENCE` | detalle de la ola `sociedad de valores` |
| `docs/superpowers/plans/2026-04-25-mcp-privado-fiable.md` | `REFERENCE` | workstream lateral MCP |
| `docs/superpowers/plans/2026-04-12-itpajd-classification.md` | `HISTORICAL` | no leer por defecto |
| `docs/superpowers/plans/2026-04-12-buscador-profesional-phase-1.md` | `HISTORICAL` | no leer por defecto |
| `docs/superpowers/plans/2026-04-10-esdata-v0-1-5.md` | `HISTORICAL` | bootstrap historico |

---

## Regla final del repo

Este repositorio no debe depender de modelos con ventanas de contexto grandes.

Toda su documentacion operativa y de ejecucion debe poder ser consumida por modelos pequenos, medianos o grandes con el mismo flujo de trabajo: leer poco, actuar con precision, verificar y actualizar un unico estado vivo.
