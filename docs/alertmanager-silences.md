# Alertmanager Silences

Estado verificado: `2026-05-13 06:48 Europe/Madrid`.

| active_silences | retained_silences | reason |
|---:|---:|---|
| 0 | 0 | No hay silencios activos en Alertmanager. No se conserva ningun silence como workaround de umbrales WorkerSilent. |

Comando de verificacion usado en VPS:

```bash
docker compose --env-file /etc/esdata/esdata.env -f /srv/esdata/infra/deploy/docker-compose.prod.yml \
  exec -T alertmanager wget -qO- http://127.0.0.1:9093/api/v2/silences
```
