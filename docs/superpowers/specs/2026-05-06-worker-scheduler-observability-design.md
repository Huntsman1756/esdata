# Diseno: remediacion de WorkerSilent, cron semanales y documentacion DTA viva

## Objetivo

Cerrar el incidente operativo de `WorkerSilent` con el menor cambio correcto y dejar el repo alineado con el runtime ya recuperado en produccion.

El corte tambien debe cerrar una laguna documental real: el repo ya expone endpoints de convenios DTA y calculo de retenciones, pero el manual vivo no describe hoy ese contrato con precision suficiente para un uso fiscal-regulatorio serio.

Este trabajo no redisenya el scheduler ni introduce una nueva capa de orquestacion visual. El objetivo es dejar:

- ejecucion `cron-*` reproducible y sin drift silencioso
- observabilidad alineada con el contrato real de stale
- una remediacion operativa guiada, explicita y auditable
- documentacion viva de convenios DTA por pais que no sobreprometa cobertura

## Diagnostico confirmado

### 1. Causa raiz historica del incidente

La causa raiz confirmada del fallo simultaneo en los `cron-*` semanales fue un drift manual en el unit instalado de `systemd`:

```ini
ExecStart=/usr/bin/docker compose --env-file /etc/esdata/esdata.env -f /srv/esdata/infra/deploy/docker-compose.prod.yml run --rm --no-deps %i
```

Evidencia operativa confirmada:

- `journalctl` registra una edicion manual del unit el `2026-05-05` para anadir `--no-deps`
- `dockerd` registra errores repetidos en las horas exactas de los timers: `container ... is not connected to the network deploy_esdata-internal`
- los fallos ocurren antes de arrancar el proceso Python del worker, por lo que no se genera fila nueva en `sync_log`

Conclusiones cerradas:

- no fue un fallo individual de cada worker
- no fue un problema de escritura SQL dentro del worker
- no fue un error de calculo de timestamps en la API como causa raiz principal
- si fue un fallo comun en el borde `systemd -> docker compose run`

### 2. Estado actual real de produccion

La produccion ya esta recuperada a nivel operativo basico:

- los `esdata-*.timer` estan `enabled`
- los contenedores persistentes relevantes estan `Up` y `healthy`
- los `esdata-job@cron-*.service` recientes cierran con `Result=success` y `ExecMainStatus=0`
- `/metrics` expone `worker_stale_status{worker="cron-..."} 0`
- Prometheus no tiene `WorkerSilent` activo ahora mismo

Esto importa porque el repo local y la documentacion siguen atras respecto al runtime corregido. El corte debe alinear el repo con ese estado recuperado, no reintroducir el drift historico.

### 3. Drift restante entre repo, runtime y docs

El drift confirmado que sigue abierto es:

- `infra/observability/alerts.yml` en el repo aun usa `worker_lag_seconds > 172800`
- el template local `infra/deploy/systemd/esdata-job@.service` aun apunta a `/srv/esdata/infra/deploy/.env.prod`
- el VPS usa hoy una materializacion externa de entorno: `/etc/esdata/esdata.env`
- los runbooks actuales no explican con suficiente claridad la diferencia entre la fuente documental del repo y la materializacion operativa instalada en el host
- no existe hoy un check operativo del repo que detecte automaticamente el drift mas peligroso del incidente: `--no-deps` en el unit o la vuelta a una alerta de `48h` fija

### 4. Gap documental DTA y contradicciones internas

La capacidad DTA existe realmente en codigo:

- router `apps/api/routers/dta_convenios.py`
- schemas en `apps/api/schemas.py`
- tests `apps/api/tests/test_dta_convenios.py`

Pero la documentacion viva para usuario e integracion no esta al mismo nivel. Hoy el repo muestra tres fuentes internas con afirmaciones no totalmente alineadas:

- el roadmap de la Fase 25.8 cita un set de convenios y fixtures que no coincide exactamente con los fixtures actuales
- `apps/api/tests/conftest.py` usa hoy `DTA_US_ES`, `ES_US_DTA` y `DTA_US_FR`
- `scripts/data/seed_irs_fiscal.py` contiene un set mas amplio de seeds por pais (`ES_US_DTA`, `ES_GB_DTA`, `ES_DE_DTA`, `ES_FR_DTA`, `ES_IT_DTA`, `ES_PT_DTA`, `ES_JP_DTA`, `ES_KR_DTA`, `ES_BR_DTA`, `ES_MX_DTA`, etc.)

Conclusiones cerradas para este corte:

- si hay capacidad funcional DTA verificable
- no hay hoy documentacion viva suficiente sobre convenios DTA por pais
- no es seguro documentar una matriz completa de paises solo a partir del roadmap o de seeds sin verificar el contrato expuesto
- la doc viva debe describir el contrato HTTP real y sus limites, no vender una cobertura internacional mas amplia de la verificada

## Alcance aprobado

Incluye:

- alinear `infra/deploy/systemd/esdata-job@.service` con la materializacion operativa soportada en el VPS recuperado
- corregir `infra/observability/alerts.yml` para que `WorkerSilent` use `worker_stale_status == 1`
- actualizar `docs/deployment/server-installation.md` y `docs/operations/runbooks/deploy-compose.md`
- registrar el hallazgo reusable en `docs/operations/agent-notes.md`
- anadir un script operativo en `scripts/ops/` para `check`, `fix-drift` y `rerun` con ejecucion explicita y auditable
- documentar DTA de forma viva en el manual de usuario y en la referencia de endpoints
- dejar claros los limites actuales de cobertura DTA por pais
- reconciliar cualquier afirmacion documental activa que contradiga el contrato DTA realmente verificado en codigo

No incluye:

- una UI tipo `hermes-war-room`
- un agente/daemon autonomo que modifique `systemd` o relance cron jobs por su cuenta
- redisenar el scheduler completo
- sustituir `systemd` por otro mecanismo
- ampliar la cobertura funcional DTA con nuevos convenios o nueva ingestión por pais
- prometer una matriz internacional completa no verificada en runtime

## Opciones evaluadas

### Opcion 1. Alinear repo, endurecer checks y documentar DTA real

Corregir el unit, alinear alertas, anadir una utilidad operativa auditable y cerrar la documentacion viva DTA con limites explicitos.

Ventajas:

- ataca la causa raiz confirmada
- reduce la probabilidad de reintroducir el mismo drift
- no mete automatismos opacos en un sistema regulatorio sensible
- resuelve una carencia real de documentacion funcional

Inconvenientes:

- mantiene la dualidad `worker-*` continuo + `cron-*` one-shot
- la remediacion sigue siendo operador-driven, no autonoma

### Opcion 2. Introducir una capa tipo war room o multiagente de incidentes

Inspirarse en `hermes-war-room` para crear una nueva capa de coordinacion visual u orquestacion de respuesta.

Se descarta para este corte:

- es un proyecto propio, no un fix proporcional
- mete otra pila operativa encima de una incidencia ya entendida
- diluye el objetivo principal de cerrar el drift real del scheduler

### Opcion 3. Documentacion DTA solamente

Actualizar el manual DTA y dejar el incidente resuelto solo en produccion, sin endurecer el repo.

Se descarta porque deja abierta la recurrencia exacta que ya ocurrio: drift entre repo y runtime.

## Enfoque recomendado

Se aprueba la opcion 1.

El corte se organiza en cuatro capas:

1. alinear el contrato de ejecucion del scheduler
2. alinear el contrato de observabilidad
3. anadir una remediacion operativa guiada y segura
4. cerrar la documentacion viva DTA sin sobreprometer cobertura

## Diseno por capa

### 1. Contrato de ejecucion del scheduler

El unit file del repo debe reflejar el contrato operativo soportado en produccion, no una ruta local de ejemplo.

Patron esperado:

```ini
ExecStart=/usr/bin/docker compose --env-file /etc/esdata/esdata.env -f /srv/esdata/infra/deploy/docker-compose.prod.yml run --rm %i
```

Propiedades del contrato:

- sin `--no-deps`
- `WorkingDirectory=/srv/esdata`
- ruta de Compose estable y real
- fichero de entorno externalizado fuera del repo en el host

La documentacion debe explicar explicitamente que:

- `infra/deploy/.env.prod` sigue siendo la referencia de ejemplo dentro del repo
- `/etc/esdata/esdata.env` es la materializacion operativa instalada en el VPS
- esa diferencia es intencional y soportada, no drift silencioso

### 2. Contrato de observabilidad

La alerta `WorkerSilent` del repo debe quedar alineada con la API y con Prometheus cargado en produccion:

```yaml
expr: worker_stale_status == 1
for: 1h
```

Reglas de este corte:

- no volver a inferir stale con una ventana fija de `48h`
- `worker_lag_seconds` puede seguir expuesto para diagnostico, pero no sera la base canonica de la alerta de silencio
- el criterio canonico de stale queda centralizado en `apps/api/routers/status.py`

### 3. Remediacion operativa guiada

Se anadira una utilidad en `scripts/ops/` con un nombre orientado a accion concreta, por ejemplo `worker_scheduler_guard.py`.

Modo esperado:

- `check`
  - compara el unit esperado con el instalado
  - detecta `--no-deps`
  - detecta si la regla `WorkerSilent` activa no usa `worker_stale_status == 1`
  - resume timers, jobs y workers stale visibles
- `fix-drift`
  - solo con `--apply`
  - instala/copia el unit esperado o imprime la secuencia exacta a ejecutar
  - recarga `systemd`
  - valida la definicion cargada
  - recarga reglas de Prometheus o imprime la secuencia exacta si el entorno no permite hacerlo directamente
- `rerun`
  - acepta lista explicita de workers `cron-*`
  - ejecuta de forma secuencial
  - valida cada rerun antes de pasar al siguiente

Restricciones deliberadas:

- sin ejecucion automatica en background
- sin hardcodear alias SSH del operador en el script
- sin side effects por defecto; `--apply` o equivalente debe ser obligatorio para acciones destructivas o mutantes

### 4. Documentacion viva DTA por pais

La doc viva DTA no debe intentar enumerar toda la cobertura potencial del repo. Debe documentar con precision el contrato estable y los limites actuales.

Capitulos a tocar:

- `docs/manual-usuario/06-api-y-ejemplos.md`
- `docs/manual-usuario/09-referencia-de-endpoints.md`
- `docs/manual-usuario/05-limites-alcance-y-estado-actual.md`

Contenido esperado:

- endpoints DTA disponibles hoy:
  - `GET /v1/internacional/convenios`
  - `GET /v1/internacional/convenios/{codigo}`
  - `GET /v1/internacional/convenios/retenciones`
  - `GET /v1/internacional/convenios/retenciones/{codigo}`
  - `POST /v1/internacional/convenios/retencion`
- ejemplos practicos con consultas por pais y por tipo de renta
- explicacion de que el calculo de `retencion` cruza reglas de withholding con convenio DTA vigente cuando existe
- advertencia clara de que la cobertura por pais depende del dataset sembrado en la instancia y no debe asumirse exhaustiva solo por existir seeds en el repo
- explicacion de que hay codigos legacy/alias en fixtures (`DTA_US_ES` y `ES_US_DTA`) y que la documentacion debe usar solo ejemplos realmente verificados por el contrato expuesto

Regla de veracidad para este corte:

- si no se verifica un convenio concreto en el contrato expuesto o en la base sembrada objetivo, no se documenta como disponible para usuario final

### 5. Reconciliacion documental activa

Si durante la implementacion se confirma que el roadmap activo afirma un set de convenios DTA incompatible con el contrato hoy verificado, ese punto del roadmap debe corregirse o matizarse para no contradecir el manual vivo.

La prioridad documental en este corte es:

1. contrato HTTP realmente implementado
2. manual vivo de usuario
3. roadmap activo sin contradicciones factuales

## SQL y contrato de `sync_log`

No se propone cambio de esquema para este corte.

El contrato actual sigue siendo suficiente:

- `started_at` y `finished_at` en `timestamp with time zone`
- indices sobre `worker`, `started_at DESC` y `(worker, started_at DESC)`
- consulta de ultima fila por worker mediante `ROW_NUMBER() OVER (PARTITION BY worker ORDER BY started_at DESC)`

Conclusiones cerradas para este corte:

- no hay evidencia de race condition SQL como causa raiz principal
- no hay evidencia de transacciones colgadas o `idle in transaction` como causa raiz principal
- el incidente exige alinear ejecucion y observabilidad, no redisenar `sync_log`

## Secuencia de implementacion esperada

1. actualizar `infra/deploy/systemd/esdata-job@.service`
2. actualizar `infra/observability/alerts.yml`
3. anadir la utilidad operativa en `scripts/ops/`
4. anadir tests del script si la logica lo requiere
5. actualizar docs de despliegue, runbooks y `agent-notes`
6. actualizar el manual vivo DTA y la referencia de endpoints
7. reconciliar cualquier contradiccion documental activa detectada
8. verificar localmente el scope afectado
9. verificar en el VPS con evidencia fresca

## Verificacion requerida

### Repo local

- `ruff check` sobre los archivos Python tocados
- `python -m pytest apps/api/tests/test_dta_convenios.py -q`
- `python -m pytest scripts/tests/test_<script>.py -q` si se crea test dedicado
- `docker compose --env-file infra/deploy/.env.prod -f infra/deploy/docker-compose.prod.yml config`

### VPS

- `systemctl cat esdata-job@.service`
- `systemctl list-timers --all 'esdata-*'`
- `systemctl show esdata-job@cron-<worker>.service -p Result -p ExecMainStatus -p ActiveState -p SubState`
- `journalctl -u esdata-job@cron-<worker>.service -n 80 --no-pager`
- `docker ps`
- ausencia del error `not connected to the network deploy_esdata-internal` en nuevos runs
- `/metrics` con `worker_stale_status{worker="cron-..."} 0` para los weekly sanos
- Prometheus sin `WorkerSilent` espurio

### Documentacion DTA

- el manual incluye endpoints y ejemplos reales de DTA
- el manual no promete una matriz completa de paises no verificada
- si se mencionan codigos de convenio, coinciden con ejemplos realmente verificados en tests o en la instancia objetivo

## Riesgos abiertos

- la utilidad operativa puede requerir adaptar comandos segun el host si se intenta soportar ejecucion remota y local con una sola interfaz
- la coexistencia `worker-*` + `cron-*` sigue siendo una fuente potencial de confusion operativa
- la cobertura DTA por pais puede seguir variando entre fixtures, seeds y entornos desplegados; la documentacion debe mantenerse conservadora
- algun rerun futuro puede fallar por fuente externa aunque el scheduler quede bien

## Criterio de exito

1. el repo deja de permitir volver al drift `--no-deps` sin una senal clara
2. `WorkerSilent` del repo queda alineado con `worker_stale_status == 1`
3. existe una utilidad operativa explicita para detectar drift y ejecutar la remediacion de forma guiada
4. el manual vivo documenta DTA por pais de forma util y veraz
5. la documentacion activa no contradice el contrato funcional realmente verificado
6. no se introduce una nueva capa war-room ni automatismos opacos fuera de alcance

## Archivos previstos

- `infra/deploy/systemd/esdata-job@.service`
- `infra/observability/alerts.yml`
- `scripts/ops/worker_scheduler_guard.py`
- `scripts/tests/test_worker_scheduler_guard.py`
- `docs/deployment/server-installation.md`
- `docs/operations/runbooks/deploy-compose.md`
- `docs/operations/agent-notes.md`
- `docs/manual-usuario/06-api-y-ejemplos.md`
- `docs/manual-usuario/09-referencia-de-endpoints.md`
- `docs/manual-usuario/05-limites-alcance-y-estado-actual.md`
- `docs/master-execution-roadmap.md` si durante la implementacion se confirma contradiccion factual activa sobre DTA

## Decision final

Se aprueba un corte acotado y verificable: consolidar en el repo la remediacion real del incidente `WorkerSilent`, anadir una guardia operativa explicita contra el drift que lo provoco y cerrar la documentacion viva de convenios DTA por pais con un criterio conservador de veracidad. No se cambia la arquitectura general del scheduler ni se introduce una nueva capa tipo war room en esta iteracion.
