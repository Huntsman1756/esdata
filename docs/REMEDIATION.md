# Remediation Backlog

## Week 1

- secretos: eliminar `.env` runtime del repo y workspace normal, rotar valores expuestos y dejar politica fail-closed en CI
- auditoria: cablear `query_audit` en retrieval, `consulta` y MCP antes de responder
- doc truthfulness: corregir cualquier afirmacion de estado no soportada por runtime activo
- parsing seguro: definir wrapper de cuarentena/sandbox y bloquear nuevo parsing directo de PDF remoto

## Month 1

- grounding duro: citas por claim, abstencion, threshold explicito y reranker activo
- ledger de ingestion: `etag`/`last-modified`/`sha256`, delta summary, version de chunking y embeddings por fuente
- roles DB: separar API, workers, migraciones y lectura
- observabilidad: P95/P99 retrieval, token count, coste aproximado y error rate por componente

## Month 3

- parser sandbox operativo para workers documentales
- hardening de bootstrap reproducible con checklist y smoke tests de seguridad
- grafo derivado local despues de cerrar secretos, audit, parsing seguro y grounding duro
