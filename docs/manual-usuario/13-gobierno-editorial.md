# Gobierno editorial y limites de uso

## Objetivo

Este documento define las reglas de gobierno para el uso de las tablas `nota_editorial_interna` y `posicion_interpretativa` (Fase 18). Establece quien puede crear, modificar y consultar contenido editorial, como se separa la fuente oficial del criterio interno, y que limites tiene este espacio.

## Que es la capa editorial interna

La capa editorial interna es un espacio de conocimiento propio que complementa las fuentes oficiales (BOE, DOUE, CNMV, etc.) con:

- **Notas editoriales internas** — resúmenes ejecutivos, contexto, impacto práctico y advertencias sobre normas, doctrina u obligaciones.
- **Posiciones interpretativas** — criterios internos versionados sobre como interpreta la empresa una norma o directiva.

Este contenido **no sustituye** la fuente oficial. Siempre debe citarse y enlazarse a ella.

## Separacion de fuentes

Todo contenido editorial debe clasificarse claramente como uno de estos tipos:

| Tipo | Origen | Uso |
|------|--------|-----|
| `fuente_oficial` | BOE, DOUE, CNMV, EU eurl, etc. | Texto legal vigente. Referencia inmutable. |
| `resumen_interno` | Equipo compliance/legal | Resumen operativo para uso interno. No vinculante. |
| `criterio_experto` | Equipo tecnico/juridico | Interpretacion de como aplicar una norma. No vinculante. |
| `nota_operativa` | Operaciones | Instrucciones de procedimiento derivadas de una obligacion. |

En las notas editoriales, el campo `tipo_contenido` distingue entre `resumen_interno`, `criterio_experto` y `nota_operativa`. En las posiciones interpretativas, el campo `estado` indica si la posicion es `borrador`, `vigente`, `revisar` u `obsoleto`.

## Reglas de autoria y revision

- Toda nota o posicion debe tener un `autor_id` no nulo. Identifica al responsable interno que crea el contenido.
- Todo contenido `vigente` debe tener un `revisor_id` no nulo. Identifica a la persona que lo revisó.
- El `revisor_id` no puede ser el mismo que el `autor_id` para contenido con estado `vigente`.
- Los identificadores internos (`autor_id`, `revisor_id`) son strings libres. No hay tabla de usuarios en este modelo.

## Estados y transiciones

### Notas editoriales

| Estado | Significado |
|--------|-------------|
| `borrador` | En redaccion. No visible en consultas sin filtro explícito. |
| `vigente` | Aprobado y activo. Visible en todas las consultas. |
| `revisar` | Requiere actualizacion. Sigue visible pero con indicador. |
| `obsoleto` | Reemplazado o caducado. No visible en listas por defecto. |

### Posiciones interpretativas

| Estado | Significado |
|--------|-------------|
| `borrador` | En redaccion. No aplicable a clientes externos. |
| `vigente` | Aprobado y activo. Referencia para decisiones de cumplimiento. |
| `revisar` | Requiere actualizacion por cambio normativo o criterio. |
| `obsoleto` | Reemplazado por una version superior. Archivado. |

## Versionado de posiciones interpretativas

Las posiciones interpretativas tienen versionado automatico:

- Cada vez que se crea una posicion con el mismo `documento_origen_referencia`, se asigna la siguiente version numerica.
- La columna `version_anterior_id` enlaza con la version anterior (FK autoreferencial).
- Cuando se actualiza una posicion existente, se mantiene la version anterior intacta y se crea una nueva version.
- La version 1 se asigna a la primera posicion para un documento dado.

## Trazabilidad

Todo contenido editorial debe enlazar a su fuente oficial:

- `fuente_oficial_referencia` — referencia al documento oficial (ej: `BOE-A-2009-133`).
- `documento_origen_id` — FK opcional a `documento_interpretativo.id` para trazabilidad tecnica.

Si un contenido editorial no tiene `fuente_oficial_referencia`, debe marcarse como `borrador` y no publicarse.

## Limites de uso

### Que NO es la capa editorial interna

- No sustituye la fuente oficial. Siempre consultar el BOE/DOUE directamente para texto legal vinculante.
- No es asesoramiento legal externo. El criterio interno no reemplaza opinion de abogados externos.
- No es un sistema de aprobacion juridica formal. La revision editorial no equivale a revision legal corporativa.
- No es historico de cambios del texto legal. El historial de articulos vive en `documento_interpretativo`, no aqui.

### Que SI es la capa editorial interna

- Un resumen operativo para que el equipo sepa rapidamente que implica una norma.
- Una interpretacion interna documentada sobre como aplicar una obligacion.
- Un recordatorio de impacto practico y advertencias operativas.
- Un espacio para capturar conocimiento que de otra forma se perderia.

### Reglas de consulta

- Las consultas por defecto (`GET /v1/editorial/notas/` y `GET /v1/editorial/posiciones/`) devuelven todo el contenido salvo `obsoleto`.
- Para ver borradores, filtrar por `estado=borrador` explícitamente.
- Para ver todo incluyendo obsoletos, filtrar por `estado=obsoleto`.
- La busqueda por texto (`q`) solo busca en el titulo.
- El filtro `fuente` busca por `fuente_oficial_referencia`.

### Limites tecnicos

- Maximo 100 resultados por pagina en listas (`limit=100` es el maximo).
- La busqueda por texto es `LIKE` case-insensitive, no full-text search.
- No hay versionado historico en notas editoriales (solo en posiciones interpretativas).
- No hay rollback ni undo en las actualizaciones.

## Flujo de trabajo recomendado

1. **Creacion** — El autor crea una nota o posicion con estado `borrador`.
2. **Revision** — El revisor verifica la precision y cambia el estado a `vigente` o `revisar`.
3. **Actualizacion** — Cuando cambia la normativa, se crea una nueva version (posiciones) o se actualiza la nota existente.
4. **Archivado** — Cuando una nota o posicion queda obsoleta, se marca como `obsoleto`.

## Relacion con otras fases

- **Fase 19 (Playbooks operativos)** — Los playbooks pueden referenciar posiciones interpretativas como base para los pasos operativos.
- **Fase 17 (Gobierno de corpus)** — La capa editorial se alimenta del corpus procesado por las fases anteriores.
- **Fase 21 (Gobierno de datos)** — Las reglas de acceso y retencion de contenido editorial pueden integrarse en el gobierno general.

## Propietario

- Responsable editorial: equipo compliance/legal
- Responsable tecnico: equipo engineering
- Revision de contenido: revisor designado por el responsable editorial
