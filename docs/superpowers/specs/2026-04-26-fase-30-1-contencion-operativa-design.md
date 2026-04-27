# Fase 30.1 Contencion Operativa Inmediata Design

## Objetivo

Cerrar los fallos mas peligrosos del estado actual antes de seguir ampliando cobertura funcional: superficies expuestas por omision, rate limiting inefectivo y CI que aparenta controles que en realidad no bloquean nada.

Este corte no intenta resolver aun grounding fuerte, audit trail durable, conectividad cross-source ni observabilidad completa. Su trabajo es mas basico y mas urgente: convertir el sistema en `fail-closed` y dejar de mentirnos con pipelines blandos o rotos.

## Alcance aprobado

Incluye:

- hacer obligatoria la autenticacion de API en runtime normal
- hacer obligatoria la proteccion de `/mcp`
- mover el rate limiting para que actue antes del handler
- retirar `/metrics` de la superficie publica por defecto
- endurecer validacion de arranque para no permitir combinaciones inseguras de configuracion
- corregir CI para que lint y secret scanning fallen de verdad cuando corresponde
- anadir `permissions` minimos explicitos a workflows
- actualizar documentacion de variables e infra afectada

No incluye:

- persistencia durable de `ai_audit`, `data_lineage` o `human_review`
- score de faithfulness o grounding por claim
- reranker o cambios profundos del retrieval stack
- observabilidad avanzada
- rediseño de despliegue completo con artefactos inmutables

## Contexto actual

El estado actual tiene tres problemas graves y concretos:

1. La API general y `/mcp` pueden quedar abiertos por simple omision de variables de entorno.
2. El rate limiting actual se ejecuta despues del handler y por tanto no protege CPU, DB ni trabajo costoso.
3. CI contiene checks no bloqueantes o directamente rotos, lo que genera una falsa sensacion de seguridad.

Este diseno asume que romper flujos inseguros antiguos es aceptable. Si un flujo local dependia de `fail-open`, ese flujo estaba mal.

## Enfoque recomendado

Se adopta un enfoque de `corte duro` para runtime y CI, con una unica excepcion explicita: el entorno de tests puede usar una configuracion controlada de test o un bypass estrictamente acotado a test, pero no existira un modo generico de desarrollo inseguro por defecto.

La idea es simple:

- runtime normal: siempre cerrado salvo rutas deliberadamente publicas
- runtime de test: excepciones explicitas y limitadas
- CI: checks bloqueantes, sin `exit-zero` ni rutas de scripts inexistentes

## Arquitectura del corte

Patron:

`request -> auth -> rate limit -> handler -> response`

No debe existir ningun endpoint protegido donde el handler ejecute trabajo costoso antes de que auth y rate limiting hayan decidido si la peticion es valida.

## Cambios por componente

### 1. Auth API general

Archivo principal:

- `apps/api/middleware/api_key_auth.py`

Comportamiento objetivo:

- la API requiere `X-API-Key` para toda ruta no publica
- las rutas publicas deben minimizarse; la base segura es dejar publica solo salud minima
- si falta configuracion de auth requerida, la app no debe arrancar

Decision explicita:

- se elimina el comportamiento actual de "si auth no esta activada, dejar pasar todo"

### 2. Proteccion `/mcp`

Archivo principal:

- `apps/api/mcp_security.py`

Comportamiento objetivo:

- `/mcp` siempre requiere clave en runtime normal
- no se aceptara el modo actual "si hay `MCP_API_KEY` protejo; si no, dejo pasar"
- si falta la clave requerida, el arranque debe fallar o el endpoint no debe quedar operativo

### 3. Rate limiting pre-handler

Archivo principal:

- `apps/api/middleware/rate_limit.py`

Comportamiento objetivo:

- la decision de `429` ocurre antes de llamar a `call_next`
- auth y rate limiting deben proteger tanto API como `/mcp` sin ejecutar trabajo innecesario

Trade-off aceptado:

- se mantiene una implementacion sencilla mientras siga siendo correcta en el orden de ejecucion; la sofisticacion distribuida se difiere

### 4. Validacion de arranque y superficie publica

Archivo principal:

- `apps/api/main.py`

Comportamiento objetivo:

- arrancar debe fallar si faltan claves requeridas para runtime normal
- `/metrics` no debe quedar en la lista publica por defecto
- la configuracion insegura no debe expresarse como warning suave sino como error de arranque cuando aplique

### 5. CI veraz y bloqueante

Archivos principales:

- `.github/workflows/ci.yml`
- `.github/workflows/deploy-hetzner.yml`

Comportamiento objetivo:

- `ruff check` debe fallar si hay problemas
- secret scan debe invocar la ruta real del script o eliminarse si no existe sustituto fiable
- no debe haber comandos de CI que llamen scripts inexistentes
- workflows con `permissions` explicitos y minimos

### 6. Infra y documentacion operativa

Archivos principales:

- `infra/deploy/docker-compose.prod.yml`
- `docs/environment-variables.md`

Comportamiento objetivo:

- reflejar que las claves son obligatorias y no opcionales en runtime normal
- documentar defaults seguros y eliminar ambiguedad sobre modos inseguros heredados

## Compatibilidad con tests

No se mantendra compatibilidad con tests que consideren correcto el modo `fail-open` actual.

Regla:

- si un test espera acceso abierto por defecto, el test esta mal y debe cambiarse

Excepcion controlada:

- la suite puede usar una clave fija de test o una señal inequivoca de entorno de test para evitar ruido, pero esa excepcion no debe quedar reutilizable en runtime normal

## Contrato funcional esperado

### Request sin credenciales

- `GET /health`: permitido si sigue siendo publico
- cualquier otra ruta protegida: `401` sin ejecutar handler protegido

### Request con credenciales invalidas

- `401`

### Exceso de peticiones

- `429` antes del trabajo de negocio

### Configuracion incompleta en runtime normal

- la app falla al arrancar con mensaje claro

## Errores y limites

- este corte no resuelve todavia authz fina ni scopes por endpoint
- el rate limit puede seguir siendo simple en almacenamiento mientras el orden de ejecucion sea correcto
- el despliegue seguira siendo Compose; este corte no reescribe aun el pipeline de release completo

## Testing

Cobertura minima requerida:

1. **Auth middleware**
- ruta protegida sin key devuelve `401`
- ruta protegida con key invalida devuelve `401`
- ruta protegida con key valida ejecuta correctamente

2. **MCP guard**
- `/mcp` sin key valida devuelve `401`
- `/mcp` con key valida funciona

3. **Rate limiting**
- el middleware devuelve `429` antes de ejecutar el handler cuando el bucket esta agotado
- headers de rate limit siguen siendo coherentes

4. **Startup validation**
- arranque falla si faltan claves obligatorias en runtime normal

5. **CI**
- workflow actualizado no contiene rutas a scripts inexistentes
- lint deja de ser no bloqueante

## Trade-offs aceptados

- se rompe compatibilidad con flujos inseguros heredados
- se prioriza seguridad real sobre conveniencia local inmediata
- no se sobre-disena todavia un sistema distribuido de rate limiting

## Riesgos abiertos

- parte de la suite actual puede depender implicitamente del modo inseguro y exigir ajustes adicionales
- puede aparecer acoplamiento no obvio entre middlewares por el cambio de orden efectivo
- algunos docs historicos pueden seguir reflejando defaults viejos y necesitar limpieza posterior

## Criterio de exito del corte

1. la API no queda abierta por omision en runtime normal
2. `/mcp` no queda operativo sin proteccion
3. el rate limiting corta antes del handler
4. `/metrics` deja de ser publico por defecto
5. CI falla de verdad cuando lint o secret scan fallan
6. documentacion operativa y configuracion no contradicen el comportamiento real

## Archivos previsibles

Nuevos o modificados previsibles en implementacion:

- `apps/api/middleware/api_key_auth.py`
- `apps/api/mcp_security.py`
- `apps/api/middleware/rate_limit.py`
- `apps/api/main.py`
- `apps/api/tests/test_security.py`
- tests de middleware/MCP relacionados
- `.github/workflows/ci.yml`
- `.github/workflows/deploy-hetzner.yml`
- `infra/deploy/docker-compose.prod.yml`
- `docs/environment-variables.md`
- `docs/manual-usuario/04-operacion-tecnica.md` si cambia el setup visible para operar localmente

## Decision final

Se aprueba implementar `Fase 30.1` como corte duro de contencion operativa: runtime `fail-closed`, `/mcp` protegido, rate limiting pre-handler y CI bloqueante. La prioridad no es comodidad ni expansion funcional; la prioridad es dejar de operar sobre defaults inseguros y controles cosmeticos.
