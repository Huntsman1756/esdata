# Sprint G Bugfix Report

Fecha: 2026-05-17

## Resultado

Sprint G corrige la separacion entre catalogo AEAT y obligaciones verificadas por perfil, y anade calendario trimestral basado en datos estructurados.

Estado productivo tras el sprint:

| Perfil | Total | Verified | Evidence limited | % verified |
|---|---:|---:|---:|---:|
| agencia_valores | 27 | 27 | 0 | 100.0 |
| eaf | 21 | 21 | 0 | 100.0 |
| empresa_servicios_pago | 11 | 11 | 0 | 100.0 |
| entidad_credito | 28 | 28 | 0 | 100.0 |
| sgiic | 22 | 22 | 0 | 100.0 |
| sociedad_valores | 29 | 29 | 0 | 100.0 |

Total: `138/138 verified`, `0 evidence_limited`.

## Bugs corregidos

### BUG-1: Modelo 202 ausente

Root cause: `aeat_modelo` contenia el Modelo 202, pero `obligacion_perfil` no lo asignaba a los perfiles sujetos a IS.

Fix: `scripts/data/seed_sprint_g_01_modelo_202.sql` inserta Modelo 202 para los seis perfiles, con `LIS art. 40`, periodicidad trimestral y plazo `Del 1 al 20 de abril, octubre y diciembre`.

Verificacion: `modelo_aeat='202'` aparece en 6 perfiles con `verified=true`.

### BUG-2: Mezcla catalogo/perfil

Root cause: consultas de obligaciones podian mezclar candidatos de `aeat_modelo` con obligaciones verificadas de `obligacion_perfil`.

Fix: `obtener_obligaciones_perfil` queda cubierto como fuente estricta de perfil, y se crea `buscar_modelos_aeat_catalogo` para busqueda de catalogo sin `verified` ni `evidence_notice`.

Verificacion: `sociedad_valores/FISCAL` no devuelve `123` ni `124`; el catalogo si puede devolver `123`.

### BUG-3: Evidence notice de formulario vs obligacion

Root cause: `/v1/modelos/aeat/{codigo}` exponia completitud de formulario y podia confundirse con la verificacion legal de la obligacion por perfil.

Fix: el detalle AEAT separa `form_completeness`/`form_evidence_notice` de `obligation_context[]`, que procede de `obligacion_perfil`.

Verificacion: Modelo 289 puede tener formulario parcial y, a la vez, obligacion verificada para `sociedad_valores` con aviso `Verificado ... (condicional)`.

### BUG-4: Calendario trimestral semantico

Root cause: la pregunta "este trimestre" dependia de ranking semantico en vez de `periodicidad` y `plazo_descripcion`.

Fix: `calendario_obligaciones_perfil` acepta `quarter`; `GET /v1/perfil/{codigo}/obligaciones/calendario/{quarter}` devuelve vencimientos trimestrales por datos estructurados.

Verificacion: Q3 2026 para `sociedad_valores` incluye `303` y excluye `202` porque este vence en Q2/Q4.

## Verificacion final

- Local: `pytest apps/ -q --basetemp .pytest-tmp` => `3101 passed, 2 skipped`.
- VPS: `mcp_validation_suite.py --read-only --base-url http://api:8000` => `ok=true`.
- VPS: `mcp_deep_contract_audit.py --base-url http://api:8000` => `ok=true`.
- VPS: API healthy.
- Alertmanager: `amtool alert query` sin alertas activas.
