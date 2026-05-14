# CNMV Coverage Map - 2026-05-14

## Production Snapshot

`documento_interpretativo` rows where `organismo_emisor='CNMV'` and `tipo_fuente='cnmv'`:

| tipo_documento | total | vigente | vigente_modificado | derogado |
|---|---:|---:|---:|---:|
| circular_cnmv | 65 | 16 | 22 | 27 |
| documento_cnmv | 7 | 3 | 1 | 3 |
| **total** | **72** | **19** | **23** | **30** |

The user-visible count "65 archivos" is therefore only the loaded circular subset,
not the full CNMV universe.

Related structured tables currently loaded:

| table | rows |
|---|---:|
| documento_cnmv_version | 72 |
| cnmv_regulation_link | 155 |
| cnmv_obligation_link | 47 |

## Source Families

| family | official source | current ESData status | contract |
|---|---|---|---|
| Circulares CNMV | https://www.cnmv.es/portal/Legislacion/Circulares | partial_loaded | Loaded partially. Counts do not prove complete CNMV coverage. |
| Generic CNMV documents | https://www.cnmv.es/Portal/Menu/Legislacion?lang=es | partial_generic | Loaded rows are official but not a complete family inventory. |
| Guias tecnicas | https://www.cnmv.es/portal/Legislacion/Guias-Tecnicas | configured_but_unavailable | Official family identified; no dedicated ingestion yet. |
| Preguntas y respuestas sobre normas | https://www.cnmv.es/Portal/Menu/Legislacion?lang=es | configured_but_unavailable | Official family identified from CNMV legislation menu; no dedicated ingestion yet. |
| Documentos a consulta | https://www.cnmv.es/portal/publicaciones/documentos-fase-consulta?tDoc=1 | configured_but_unavailable | Official paginated family identified; no dedicated ingestion yet. |
| Modelos normalizados | https://www.cnmv.es/portal/Legislacion/ModelosN/ModelosN | configured_but_unavailable | Official family identified; forms/models are not loaded in the current CNMV corpus. |
| Registros oficiales | https://www.cnmv.es/Portal/Menu/Legislacion?lang=es | configured_but_unavailable | Entity and market registers are not part of the CNMV document corpus. |

## API Contract

`GET /v1/cnmv/coverage` exposes the loaded count and the known missing CNMV
source families. MCP/GPT consumers should inspect this endpoint before treating
CNMV no-results as meaningful.

Operational rules:

- Default `/v1/cnmv` and `/v1/cnmv/buscar` are current-only: `vigente` and
  `vigente_modificado`.
- Historical/deprecated documents require explicit `vigencia=all` or
  `vigencia=derogado`.
- A no-result response in CNMV can mean "not loaded", not "does not exist".
- `vigente_modificado` does not imply consolidated text. Use
  `es_consolidado=true` and `consolidated_verification_status='consolidated'`
  before citing a modified document as current consolidated evidence.

## Expansion Priority

1. Guias tecnicas CNMV.
2. Documentos a consulta.
3. Modelos normalizados.
4. Registers that are useful for regulated entities, but as separate structured
   domains rather than mixed into `documento_interpretativo`.
5. Additional communications and Q&A families only when the official source is
   deterministic enough to parse without heuristic inference.
