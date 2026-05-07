# Diseno - Fase 6.2 tests de contrato documental MCP

## Objetivo

Anadir un gate automatizado y pequeno que detecte drift en la separacion documental fijada por `Fase 6.1` entre `REST/OpenAPI`, `HTTP MCP`, `stdio MCP` y la guia `OpenCode -> HTTP MCP`, sin introducir cambios de runtime ni wiring de CI en este slice.

## Problema confirmado

- `Fase 6.1` ya dejo alineados `docs/architecture.md`, `docs/manual-usuario/06-api-y-ejemplos.md`, `docs/manual-usuario/07-mcp-y-clientes.md` y `docs/integrations/opencode-local-and-vps.md`.
- Hoy esa alineacion se comprueba con lecturas manuales y comandos ad hoc, pero no existe un gate automatizado dedicado que falle si un cambio futuro vuelve a mezclar `REST/OpenAPI` con `/mcp`, borra los anchors de `HTTP_MCP_OPERATIONS`, o amplia la guia de `OpenCode` fuera de `HTTP MCP`.
- `docs/reference/mcp-remediation-plan.md` define explicitamente `6.2` como la fase para anadir esos tests de contrato documental.
- El repo ya tiene un patron util para este tipo de verificacion en `scripts/maintenance/verify-doc-artifacts.py` y `scripts/tests/test_verify_doc_artifacts.py`: un script pequeno en `scripts/maintenance/` y tests puros en `scripts/tests/`.

## Decision

- `Fase 6.2` vivira en `scripts/`, no en `apps/api/tests/`.
- Se anadira un script nuevo: `scripts/maintenance/verify-doc-contracts.py`.
- Se anadira un test nuevo: `scripts/tests/test_verify_doc_contracts.py`.
- El gate validara solo invariantes documentales estables del slice `6.1`; no intentara congelar parrafos completos ni texto exacto salvo donde el contrato requiera un token concreto.
- `Fase 6.2` no cablea CI ni edita workflow; ese paso queda para `6.4`.

## Alcance aprobado

Incluye:

- crear `scripts/maintenance/verify-doc-contracts.py`
- crear `scripts/tests/test_verify_doc_contracts.py`
- verificar de forma automatizada el boundary documental de estas rutas:
  - `docs/architecture.md`
  - `docs/manual-usuario/06-api-y-ejemplos.md`
  - `docs/manual-usuario/07-mcp-y-clientes.md`
  - `docs/integrations/opencode-local-and-vps.md`
- actualizar `docs/master-execution-roadmap.md` para reclamar y cerrar `6.2` cuando el slice termine

No incluye:

- cambios en runtime o routers MCP
- reabrir `6.1` con mas reescritura documental salvo que los tests descubran drift real durante la propia implementacion
- wiring en CI
- snapshot tests de markdown completo

## Contrato a fijar

### `docs/architecture.md`

Debe seguir dejando visible la separacion entre las tres superficies:

- `REST/OpenAPI`
- `HTTP MCP`
- `stdio MCP`

El test no exigira orden exacto de lineas ni copy identica, pero si la presencia de esos tres identificadores como minima prueba del boundary arquitectonico.

### `docs/manual-usuario/06-api-y-ejemplos.md`

Debe seguir siendo un capitulo `REST/OpenAPI` only.

El gate fallara si reaparece `/mcp` en este archivo, porque en este slice el boundary aprobado es que el capitulo `06` no ensene MCP ni lo mezcle con la API REST.

### `docs/manual-usuario/07-mcp-y-clientes.md`

Debe seguir explicitando el split `HTTP MCP` vs `stdio MCP` con anchors concretos:

- `apps/api/mcp_catalog.py`
- `HTTP_MCP_OPERATIONS`
- `apps/api/mcp_stdio.py`
- `consulta_fiscal`

El gate no intentara enumerar todo el catalogo HTTP ni todas las tools stdio; solo fijara los anchors minimos que impiden volver a un framing ambiguo.

### `docs/integrations/opencode-local-and-vps.md`

Debe seguir siendo una guia de `OpenCode` consumiendo `HTTP MCP` por `url` hacia `/mcp`.

Anchors minimos requeridos:

- `OpenCode`
- `HTTP MCP`
- `/mcp`
- `X-API-Key: <MCP_API_KEY>`
- una exclusion explicita de `stdio`, mediante `stdio MCP` en seccion de alcance o `No cubre`

## Diseno del script

### Archivo

- `scripts/maintenance/verify-doc-contracts.py`

### Estructura propuesta

- `ROOT` y rutas canonicas a los cuatro docs
- una funcion por contrato:
  - `verify_architecture_contract()`
  - `verify_manual_api_contract()`
  - `verify_manual_mcp_contract()`
  - `verify_opencode_contract()`
- `run()` agrega findings en una lista plana
- `main()` imprime findings y devuelve `0` si no hay errores, `1` si hay drift

### Estilo de validacion

- checks pequenos y semanticos basados en presencia/ausencia de tokens
- sin snapshots de bloques completos
- sin dependencia de herramientas externas
- mensajes de error directos y grep-friendly, por ejemplo:
  - `docs contract drift: manual 06 mentions /mcp`
  - `docs contract drift: chapter 07 missing HTTP_MCP_OPERATIONS reference`

## Diseno de tests

### Archivo

- `scripts/tests/test_verify_doc_contracts.py`

### Patron

- importar el script dinamicamente, igual que `scripts/tests/test_verify_doc_artifacts.py`
- sobrescribir rutas de docs con archivos temporales bajo un directorio de test
- probar contratos unitarios y agregacion de `run()`

### Casos minimos

- arquitectura valida pasa
- arquitectura sin una de las tres superficies falla
- capitulo `06` valido pasa
- capitulo `06` con `/mcp` falla
- capitulo `07` valido pasa
- capitulo `07` sin uno de los anchors requeridos falla
- guia `OpenCode` valida pasa
- guia `OpenCode` sin `X-API-Key: <MCP_API_KEY>` falla
- guia `OpenCode` sin exclusion de `stdio` falla
- `run()` agrega findings multiples cuando fallan varios docs

## Verificacion prevista

- `python -m pytest scripts/tests/test_verify_doc_contracts.py -q`
- `python scripts/maintenance/verify-doc-contracts.py`

## Aceptacion

- existe un gate automatizado pequeno y localizable para el contrato documental de `6.1`
- el gate falla si `06` vuelve a mezclar `/mcp` con REST
- el gate falla si `07` pierde los anchors minimos de `HTTP MCP` o `stdio MCP`
- el gate falla si la guia de `OpenCode` deja de estar centrada en `HTTP MCP` con `MCP_API_KEY`
- el gate pasa sobre el estado actual de la documentacion viva
- el roadmap queda listo para cerrar `6.2` y apuntar a `6.3`
