# BOE recapture audit - 2026-06-03

Artefactos generados en VPS desde `/srv/esdata` usando la imagen `ops` y el
script read-only `scripts/maintenance/boe_recapture_audit.py` de la rama
`origin/audit/boe-recapture`.

Archivos:

- `boe_recapture_audit_20260603_203107.json`
- `boe_recapture_audit_20260603_203107.csv`

Resumen:

| Resultado | Conteo |
|---|---:|
| total | 195 |
| stable | 10 |
| hash_changed | 185 |
| download_failed | 0 |

Notas:

- No hubo fallos de descarga desde el VPS hacia `boe.es`.
- La unidad auditada fue `(BOE, URL, hash existente)`, no solo BOE unico; por eso
  aparecen 195 filas aunque haya menos BOE distintos.
- `BOE-A-2025-25389` salio `stable` para los modelos `182,184,193,195,199,282,345`.
- `BOE-A-2025-25390` salio `stable` para los modelos `190,270,347`.
- Los casos `hash_changed` requieren revision antes de cualquier promocion.
