# CLAUDE.md

## Ralph - problemas conocidos

- CRLF en Windows: los prompt files deben guardarse con LF, no CRLF. Antes de lanzar `ralph.sh`: `dos2unix scripts/ralph/*.md`.
- Seeds de datos: Ralph genera los commits locales pero no aplica seeds al VPS automaticamente. Aplicar manualmente antes de M-06/M-07.
- Si Ralph no actualiza `prd.json` correctamente: editar manualmente y commitear con `"[STORY-ID] fix prd.json passes=true"`.
