# Sprint M - MiCA CASP Report

## CELEX Verification Results

### Accepted (loaded into norma)

| CELEX | Title | Status | Verification |
|-------|-------|--------|--------------|
| `32023R1114` | MiCA - Reglamento (UE) 2023/1114 | Loaded as `reglamento_ue` | EUR-Lex HTTP 200, content: `2023/1114` x3 |
| `32025R0305` | RTS solicitud autorizaci\u00f3n CASP, art. 62 | Loaded as `reglamento_delegado_ue` | EUR-Lex HTTP 200, content: `2023/1114` x3 |
| `32025R0299` | RTS continuidad y regularidad, art. 81 | Loaded as `reglamento_delegado_ue` | EUR-Lex HTTP 200, content: `2023/1114` x3 |
| `32025R0306` | ITS plantillas solicitud CASP, art. 62 | Loaded as `reglamento_delegado_ue` | EUR-Lex HTTP 200, content: `2023/1114` x3 |

### Not loaded (not required for Sprint M scope)

| CELEX | Title | Reason |
|-------|-------|--------|
| `32025R0304` | RTS - verified HTTP 200, content match | Not needed for base CASP scope |
| `32025R0300` | RTS intercambio informaci\u00f3n autoridades | Not needed for base CASP scope |

### Not loaded (excluded per PRD)

| CELEX | Title | Reason |
|-------|-------|--------|
| `32024R1681` | Reglamento construcci\u00f3n productos | Non-MiCA, construction-products regulation |
| `32024R2656` | No aceptado | No independent proof of MiCA relevance |

## Deferrals

- `emisor_token` profile deferred to Sprint N (per PRD decision)

## Sprint M Summary

- M-01: Canonical `32023R1114` loaded, `MICA_2023_1114` removed
- M-02: Perfil `casp` created (CNMV supervisor)
- M-03: 8 MiCA CASP obligations seeded (arts. 59, 62, 65, 66, 70, 72, 81, 94)
- M-04: 3 MiCA RTS/ITS loaded (32025R0305, 32025R0299, 32025R0306)
- M-05: Pending - fail-closed MCP behavior
- M-06: Pending - validation suite updates
- M-07: Pending - final verification
