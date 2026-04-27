# Runbook: Actualizacion de datasets de screening

## Objetivo

Procedimiento para actualizar las listas de screening (sanciones, PEPs, watchlists) en la base de datos de esdata.

## Contexto

- Tablas: `screening_lists`, `screening_entries`, `screening_matches`
- Worker: `apps/workers/screening.py`
- En el MVP, el dataset es ficticio (datos de ejemplo)
- Las fuentes reales a integrar: OFAC SDN, EU Sanctions, UN Sanctions, SEPBLAC, ES PEPs
- Los workers se ejecutan via `uv run screening --run-once` o `uv run screening --interval 3600`

---

## Actualizacion manual de dataset ficticio

Para cambios rapidos en el dataset de prueba:

1. Editar `apps/workers/screening.py`
2. Modificar las listas en `SCREENING_LISTS` o los entries en `SCREENING_ENTRIES`
3. Ejecutar el worker:

```bash
uv run screening --run-once
```

4. Verificar con el endpoint:

```bash
curl http://localhost:8000/v1/screening/entries
```

---

## Integracion de fuente real: OFAC SDN

### Fuente
- URL: https://www.treasury.gov/ofac/downloads/sdn.csv
- Formato: CSV con columnas fijas

### Pasos

1. Descargar el CSV mas reciente
2. Parsear y mapear campos a `screening_entries`:
   - `nombre` → nombre de entidad/persona
   - `entidad_id` → generar UUID o usar ID de OFAC
   - `nif` → Tax ID si disponible
   - `fecha_nacimiento` → DOB si disponible
   - `aliases` → Array de aliases
   - `categorias` → tags de categoria
   - `pais` → pais de origen
3. Ejecutar worker con fuente real:

```bash
uv run screening --source ofac_sdn --run-once
```

4. Verificar conteo:

```bash
curl "http://localhost:8000/v1/screening/entries?codigo=OFAC_SDN&limit=1" | python -m json.tool
```

---

## Integracion de fuente real: EU Sanctions

### Fuente
- URL: https://data.consilium.europa.eu/api/download/latest.json
- Formato: JSON (lista de personas y entidades sancionadas)

### Pasos

1. Descargar el JSON mas reciente
2. Parsear y mapear campos a `screening_entries`
3. Ejecutar worker con fuente real:

```bash
uv run screening --source eu_sanctions --run-once
```

---

## Integracion de fuente real: UN Sanctions

### Fuente
- URL: https://www.un.org/security/council/committees/1267/sanctions-list-consolidated-docs
- Formato: PDF/JSON

### Pasos

1. Descargar la lista consolidada mas reciente
2. Parsear y mapear campos
3. Ejecutar worker con fuente real:

```bash
uv run screening --source un_sanctions --run-once
```

---

## Integracion de fuente real: SEPBLAC

### Fuente
- URL: https://www.sepblac.es
- Formato: HTML/PDF

### Pasos

1. Scraping o descarga de listas actualizadas
2. Parsear y mapear campos
3. Ejecutar worker con fuente real:

```bash
uv run screening --source sepblac --run-once
```

---

## Integracion de fuente real: ES PEPs

### Fuente
- URL: https://www.boe.es
- Busqueda: lista de personas fisicas y juridicas de interes politico

### Pasos

1. Recopilar lista de PEPs espanoles del BOE
2. Parsear y mapear campos
3. Ejecutar worker con fuente real:

```bash
uv run screening --source es_peps --run-once
```

---

## Verificacion de actualizacion

### Conteo por lista

```bash
curl "http://localhost:8000/v1/screening/entries?limit=1" | python -c "
import json, sys
data = json.load(sys.stdin)
print(f'Total entries: {data[\"total\"]}')
"
```

### Verificar ultimo update

```bash
curl "http://localhost:8000/v1/screening/entries?codigo=OFAC_SDN&limit=1" | python -c "
import json, sys
data = json.load(sys.stdin)
if data['entries']:
    print(f'Last entry: {data[\"entries\"][0][\"nombre\"]}')
    print(f'List updated: {data[\"entries\"][0][\"lista\"][\"actualizada\"]}')
"
```

### Test de screening

```bash
curl -X POST http://localhost:8000/v1/screening/ \
  -H "Content-Type: application/json" \
  -d '{"nombre": "TEST ENTITY", "nif": "TEST-NIF"}' | python -m json.tool
```

---

## Eliminacion de entries

Para eliminar entries de baja:

1. Marcar como inactivo en la fuente original
2. El worker deberia actualizar `activo = 0` en `screening_entries`
3. O manualmente:

```sql
UPDATE screening_entries SET activo = 0 WHERE entidad_id = 'OFAC-25001';
```

---

## Notas importantes

- **NUNCA** usar datos reales de screening sin validacion legal previa
- **NUNCA** exponer resultados de screening directamente sin campo "revisado"
- Los resultados de screening son **coincidencias evaluables**, no hechos definitivos
- Mantener trazabilidad a fuente original en `metadata_json`
- Aplicar rate limiting en endpoints de screening (ya implementado en middleware)
