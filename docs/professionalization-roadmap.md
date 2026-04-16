# Roadmap de profesionalizacion

## Objetivo

Profesionalizar `esdata` para tres metas simultaneas:

- seguir creciendo sin aumentar deuda tecnica de forma descontrolada
- dejar el sistema listo para operacion por un equipo de infraestructura externo al equipo de producto
- mantener una migracion gradual desde Railway hacia un despliegue empresarial portable

## Estado actual resumido

Base actual del repo:

- `apps/api`: API FastAPI publica
- `apps/workers`: workers Python de ingesta y sincronizacion
- `apps/web`: frontend Next.js 15
- `infra/sql`: esquema y migraciones SQL manuales
- `docker-compose.yml`: entorno local con Postgres, Redis, API y workers parciales
- `railway.toml`: despliegue monorepo actual en Railway
- `.github/workflows/ci.yml`: tests Python y lint basico

Fortalezas actuales:

- separacion clara entre API, workers y web
- despliegue real en produccion
- documentacion funcional ya existente
- Dockerfiles por servicio
- workers separados por fuente y responsabilidad

Gaps principales para un entorno mas profesional:

- falta una capa compartida clara entre `apps/api` y `apps/workers`
- configuracion y variables de entorno todavia dispersas
- migraciones de base de datos manuales y sin framework formal
- documentacion operativa todavia orientada al autor original
- despliegue portable incompleto fuera de Railway
- observabilidad y runbooks poco formalizados

## Principios de ejecucion

- no romper produccion actual en Railway
- hacer cambios pequenos y reversibles
- separar claramente documentacion de producto, documentacion tecnica y documentacion operativa
- preparar el repo para dos modos de despliegue: actual en Railway y futuro en servidor empresarial
- evitar refactors grandes sin beneficio operativo inmediato

## Estructura objetivo

Objetivo de estructura a medio plazo:

```text
esdata/
|-- apps/
|   |-- api/
|   |-- workers/
|   `-- web/
|-- libs/
|   `-- python/
|       `-- esdata_common/
|           |-- config.py
|           |-- db.py
|           |-- logging.py
|           |-- http.py
|           `-- ...
|-- infra/
|   |-- sql/
|   |-- docker/
|   `-- deploy/
|-- docs/
|   |-- architecture.md
|   |-- repository-structure.md
|   |-- environment-variables.md
|   |-- database.md
|   |-- infrastructure-handoff.md
|   |-- deployment/
|   `-- operations/
|-- scripts/
`-- tests/
```

Notas:

- `libs/python/esdata_common` puede introducirse de forma gradual sin mover toda la logica al principio
- `infra/deploy` debe quedar desacoplado de Railway y preparado para Compose empresarial o futura adaptacion a Kubernetes
- `docs/operations` debe convertirse en la referencia principal para el equipo de infraestructura

## Roadmap por fases

### Fase 1. Baseline tecnico y documental

Objetivo:

- dejar claro como funciona hoy el sistema y reducir dependencia de conocimiento implicito

Entregables:

- `docs/architecture.md`
- `docs/repository-structure.md`
- `docs/environment-variables.md`
- `docs/infrastructure-handoff.md`
- inventario de servicios, cron jobs, puertos, dependencias externas y secretos
- decision documentada sobre estrategia de migraciones futura

Cambios recomendados:

- mapear flujos principales: ingesta BOE, ingesta DGT, ingesta TEAC, modelos AEAT, API publica y frontend
- documentar cada servicio de `railway.toml` con su equivalente conceptual fuera de Railway
- consolidar variables de entorno reales usadas por API, workers y web
- diferenciar documentacion de arranque, despliegue y operacion

Resultado esperado:

- cualquier persona tecnica nueva entiende arquitectura, dependencias y operacion minima del sistema

### Fase 2. Estandarizacion interna

Objetivo:

- reducir duplicacion y preparar el repo para crecimiento de codigo y equipo

Entregables:

- capa comun Python inicial en `libs/python/esdata_common`
- convencion unica de configuracion para Python
- logging unificado para API y workers
- comandos repetibles de desarrollo y validacion

Cambios recomendados:

- extraer utilidades compartidas de configuracion, DB, retries HTTP y logging
- definir una convencion de settings por entorno
- revisar dependencias Python compartidas y versionarlas de forma coherente
- introducir `Makefile` o script equivalente para tareas operativas comunes

Quick wins:

- crear `make test`, `make lint`, `make api`, `make worker-modelos`, `make bootstrap-db`
- anadir `.env.example` realmente completo y alineado con docs
- documentar contratos internos entre web, API y workers

Resultado esperado:

- menos fragilidad al tocar varios servicios y mejor base para nuevas fuentes de datos

### Fase 3. Base de datos y cambios de esquema

Objetivo:

- profesionalizar la evolucion de schema y reducir riesgo en despliegues

Opciones viables:

- mantener SQL manual muy disciplinado
- migrar a Alembic sobre el estado actual

Recomendacion:

- introducir Alembic de forma gradual y tomar el schema actual como baseline, manteniendo SQL historico como referencia

Entregables:

- estrategia de migraciones documentada
- flujo de alta de nuevas tablas/campos
- guia de bootstrap, upgrade y rollback de base de datos
- validaciones automatizadas de schema en CI si el coste compensa

Cambios recomendados:

- crear una fotografia base del estado actual de produccion
- definir como se aplica una migracion en local, staging y produccion
- separar claramente seeds de esquema

Resultado esperado:

- el equipo de infraestructura puede desplegar y evolucionar la BD con menos riesgo y mas trazabilidad

### Fase 4. Despliegue portable y handoff a infraestructura

Objetivo:

- permitir despliegue fuera de Railway con artefactos y pasos estandarizados

Entregables:

- `infra/deploy/docker-compose.prod.yml` o estructura equivalente
- documentacion de instalacion en servidor
- documentacion de actualizacion y rollback
- checklist de handoff a infraestructura

Cambios recomendados:

- endurecer Dockerfiles para uso productivo
- revisar persistencia, networking, healthchecks y arranque ordenado
- definir como ejecutar cron jobs fuera de Railway
- separar configuracion de build y runtime

Contenido minimo del handoff:

- recursos requeridos por servicio
- dependencias de red y DNS
- variables y secretos obligatorios
- estrategia de backups y restauracion
- healthchecks y criterios de aceptacion
- flujo de despliegue y rollback

Resultado esperado:

- el sistema puede montarse en VM o plataforma corporativa sin depender del dashboard de Railway

### Fase 5. Operacion, observabilidad y soporte

Objetivo:

- hacer el sistema operable por terceros en el dia a dia

Entregables:

- `docs/operations/README.md`
- runbooks por incidencia y tarea recurrente
- logging estructurado
- verificacion operativa automatizable

Cambios recomendados:

- definir formato unico de logs
- documentar fallos habituales por worker
- anadir scripts de smoke y comprobaciones post deploy
- definir indicadores minimos: salud API, salud workers, ejecucion de crons, cobertura de datos, errores de ingesta

Resultado esperado:

- infraestructura puede operar el sistema con autonomia razonable

### Fase 6. Calidad de ingenieria y escalado

Objetivo:

- cerrar huecos que se vuelven caros a medida que el producto crece

Entregables:

- CI mas completa
- estrategia de tests ampliada
- controles de calidad y seguridad basicos

Cambios recomendados:

- anadir tests de integracion con DB realista
- anadir build del frontend y tests del web en CI
- introducir chequeos de formateo y tipado si el coste compensa
- preparar backlog de hardening: Sentry, metricas, rate limiting, auditoria de secretos

Resultado esperado:

- el repo gana fiabilidad para cambios frecuentes y crecimiento del equipo

## Priorizacion recomendada

Orden sugerido de ejecucion:

1. Fase 1 completa
2. Quick wins de Fase 2
3. Definicion de estrategia de migraciones de Fase 3
4. Artefactos de despliegue portable de Fase 4
5. Runbooks y observabilidad minima de Fase 5
6. Ampliacion de CI y calidad de Fase 6

## Quick wins de alto impacto

Cambios con buena relacion impacto/esfuerzo:

1. Crear `docs/architecture.md`
2. Crear `docs/environment-variables.md`
3. Crear `docs/infrastructure-handoff.md`
4. Unificar configuracion compartida Python
5. Anadir `Makefile` o comandos raiz equivalentes
6. Incorporar tests del frontend al CI
7. Documentar bootstrap, backup y restore de Postgres
8. Estandarizar logs y healthchecks por servicio

## Riesgos principales

### Riesgo 1. Refactor estructural demasiado grande

Impacto:

- puede frenar desarrollo funcional y abrir regresiones innecesarias

Mitigacion:

- extraer primero solo piezas compartidas de bajo riesgo
- no mover logica de negocio si no aporta valor inmediato

### Riesgo 2. Documentacion que se queda desactualizada

Impacto:

- el handoff pierde valor y genera confianza falsa

Mitigacion:

- ligar docs a archivos reales del repo
- incluir la actualizacion documental en el flujo de cambios relevantes

### Riesgo 3. Migraciones de BD mal gobernadas

Impacto:

- riesgo de inconsistencia entre entornos y despliegues delicados

Mitigacion:

- decidir una estrategia unica pronto
- documentar bootstrap, upgrade y rollback antes de crecer mucho mas

### Riesgo 4. Portabilidad incompleta fuera de Railway

Impacto:

- sorpresa operativa al mover el sistema a un entorno corporativo

Mitigacion:

- preparar despliegue portable antes de depender de servicios o supuestos exclusivos de Railway

## Documentacion objetivo

Conjunto documental minimo para handoff profesional:

- `README.md`: vista general y quickstart
- `docs/architecture.md`: componentes, flujos y dependencias
- `docs/repository-structure.md`: mapa del repo y responsabilidades
- `docs/environment-variables.md`: variables por servicio
- `docs/database.md`: esquema, migraciones, seeds, backup y restore
- `docs/deployment/overview.md`: estrategia de despliegue
- `docs/deployment/server-installation.md`: instalacion en servidor
- `docs/deployment/rollback.md`: rollback
- `docs/operations/README.md`: operacion recurrente
- `docs/operations/runbooks/*.md`: incidentes y procedimientos
- `docs/infrastructure-handoff.md`: paquete de traspaso al equipo de infra

## Definicion de terminado para esta profesionalizacion

Se puede considerar que la base esta lista para crecimiento serio y handoff cuando se cumpla esto:

- arquitectura y estructura documentadas con precision
- variables y secretos documentados por servicio
- estrategia de migraciones decidida y documentada
- despliegue portable fuera de Railway definido y probado al menos en un entorno controlado
- runbooks minimos disponibles
- CI cubre backend y frontend de forma coherente
- el equipo de infraestructura puede instalar, arrancar, verificar y recuperar el sistema sin depender del autor original

## Propuesta de siguiente fase ejecutable en este repo

Siguiente iteracion recomendada:

1. crear documentacion base de arquitectura, estructura, variables y handoff
2. revisar codigo compartible entre `apps/api` y `apps/workers`
3. proponer estructura minima de `libs/python/esdata_common`
4. mejorar `docker-compose.yml` y preparar una variante mas cercana a produccion
5. ampliar CI para incluir `apps/web`

Ese bloque deja al proyecto en un punto mucho mas serio sin introducir aun una migracion grande ni acoplar el despliegue a una plataforma concreta.
