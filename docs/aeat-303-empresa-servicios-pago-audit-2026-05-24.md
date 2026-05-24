# AEAT Modelo 303 empresa servicios pago audit - 2026-05-24

Estado: COMPLETADO LOCAL / PENDIENTE VPS

Alcance Ralph: resolver el fallo `empresa_servicios_pago_modelo_303_completa` de `profile_applicability_contracts` sin promover `completeness='completa'`, `verified=true` ni `safe_to_answer=true` sin evidencia primaria normalizada.

## RED productivo

Entorno: VPS `steamcases-vps`, commit `466cb51`, stack Docker Compose productivo.

`mcp_deep_contract_audit.py --base-url http://api:8000` reporta:

- `profile_applicability_contracts`: fallo `empresa_servicios_pago_modelo_303_completa`.
- `semantic_fail_closed_and_pagination_suite`: fallo separado por `all_profiles_pct_verified_ge_70`.

El fallo 303 no aparece en `mcp_validation_suite.py`; pertenece al deep audit de aplicabilidad de perfiles.

## Inventario de la fila 303

Fila productiva:

| Campo | Valor |
| --- | --- |
| `perfil_codigo` | `empresa_servicios_pago` |
| `modelo_aeat` | `303` |
| `descripcion` | `Modelo 303 - IVA autoliquidacion` |
| `norma_codigo` | `LIVA` |
| `articulo_referencia` | `art. 164` |
| `source_url` | `https://sede.agenciatributaria.gob.es/Sede/procedimientoini/G414.shtml` |
| `source_hash` | `NULL` |
| `capture_date` | `2026-05-17` |
| `verified` | `false` |
| `safe_to_answer` | `false` |
| `completeness` | `parcial` |
| `periodicidad` | `trimestral` |
| `plazo_descripcion` | `trimestral salvo gran empresa u otros supuestos AEAT` |

Notas relevantes:

```text
Servicios de pago tratados como sujetos a IVA para este perfil operativo; verificar exenciones especificas si la actividad cambia.
200/202/303 legacy profile obligation without normalized evidence: fail-closed until source_hash and capture_date are loaded.
global profile obligation without normalized evidence: fail-closed until source_hash and capture_date are loaded.
```

Payload API `/v1/perfil/empresa_servicios_pago/obligaciones?dominio=FISCAL`:

- Incluye Modelo 303.
- `verified=false`.
- `safe_to_answer=false`.
- `review_required=true`.
- `source_hash=null`.
- `capture_date=2026-05-17`.
- `evidence_notice="evidence_limited: falta hash o fecha de captura de la fuente"`.

## Recursos Modelo 303

La capa de modelo/campana tiene recursos oficiales:

| Campana | Casillas | Instrucciones | Recursos | Recursos con hash | Estado campana |
| --- | ---: | ---: | ---: | ---: | --- |
| `2025` | 57 | 0 | 0 | 0 | `NULL` |
| `2026` | 432 | 5 | 233 | 233 | `parcial` |

Hay `modelo_recurso` oficiales con hash para la campana 2026, incluido el XLSX oficial `DR303e26v101.xlsx` y paginas AEAT del procedimiento. Tambien existe `source_revision` para `AEAT-MODELO-303` con hash sobre `https://sede.agenciatributaria.gob.es/Sede/procedimientoini/G414.shtml`.

Esa evidencia prueba recursos del modelo y pagina/procedimiento, pero no normaliza la fila `obligacion_perfil` ni convierte por si sola la aplicabilidad exacta a `empresa_servicios_pago` en `verified=true`.

## Decision de contrato

El deep audit exigia `completeness='completa'` para el 303 de `empresa_servicios_pago`. Ese contrato era mas fuerte que el estado productivo real:

- La obligacion esta presente.
- La fila esta explicitamente fail-closed.
- La evidencia auxiliar existe a nivel modelo/campana, pero no esta reconciliada en `obligacion_perfil.source_hash`.
- La aplicabilidad contiene caveat operativo por exenciones especificas.

El contrato correcto queda:

- Falla si el Modelo 303 no esta presente para `empresa_servicios_pago`.
- Falla si el item 303 no esta verificado con hash/captura ni fail-closed explicito.
- No exige `completeness='completa'` mientras la fila este en `verified=false`, `safe_to_answer=false`, `review_required=true`, `source_hash=NULL` y `capture_date` presente.

## No-objetivos

- No modificar datos productivos.
- No promover `verified=true`.
- No promover `safe_to_answer=true`.
- No cambiar `completeness='parcial'`.
- No tocar `all_profiles_pct_verified_ge_70`.

## Criterio de salida

- `profile_applicability_contracts` deja de fallar por `empresa_servicios_pago_modelo_303_completa`.
- Si queda fallo en deep audit, debe ser otro contrato separado y documentado.
- `mcp_validation_suite.py` sigue reflejando la deuda agregada global sin manipularla.
