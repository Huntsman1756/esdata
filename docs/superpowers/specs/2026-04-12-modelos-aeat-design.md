# Diseno: Capa Modelos AEAT — Fase 1

## Objetivo

Extender esdata para responder: "¿Qué modelo AEAT me afecta?" cuando un usuario consulta un artículo o criterio doctrinal. Convierte la plataforma de investigación fiscal en herramienta de acción profesional.

## Alcance de este corte

Incluye:
- Tabla `aeat_modelo` con metadata de 6 modelos AEAT principales
- Tabla `modelo_articulo` con relaciones explícitas y fuente oficial
- 3 nuevos endpoints API bajo `/v1/modelos`
- Sidebar "Modelos AEAT relacionados" en detalle de artículo
- Sidebar "Modelos AEAT relacionados" en detalle de doctrina (derivado de artículos enlazados)
- Página de detalle `/modelo/[codigo]`

No incluye:
- Scraping AEAT
- Calendario de plazos u obligaciones
- Más de 6 modelos
- Manuales AEAT completos
- Casillas detalladas exhaustivas

## Criterio de calidad para modelo_articulo

Cada relación modelo ↔ artículo DEBE tener:
- `fuente`: referencia a documento oficial (instrucción modelo, BOE, etc.)
- `url_fuente`: URL directa a la fuente

Si no hay fuente verificable, la relación NO entra en Fase 1.

## Modelos cubiertos

| Codigo | Nombre | Impuesto | Periodo |
| --- | --- | --- | --- |
| 100 | IRPF Declaración anual | IRPF | anual |
| 111 | IRPF Retenciones | IRPF | trimestral |
| 115 | IRPF Retenciones alquileres | IRPF | trimestral |
| 130 | IRPF Pago fraccionado | IRPF | trimestral |
| 303 | IVA Autoliquidación | IVA | trimestral |
| 390 | IVA Resumen anual | IVA | anual |

## Contratos API

### GET /v1/modelos
Lista todos los modelos disponibles.

Respuesta:
```json
{
  "modelos": [
    {
      "codigo": "100",
      "nombre": "IRPF Declaración anual",
      "periodo": "anual",
      "impuesto": "IRPF",
      "articulos_count": 12
    }
  ]
}
```

### GET /v1/modelos/{codigo}
Detalle de un modelo con artículos y doctrina relacionada.

Respuesta:
```json
{
  "codigo": "100",
  "nombre": "IRPF Declaración anual",
  "periodo": "anual",
  "impuesto": "IRPF",
  "url_info": "https://sede.agenciatributaria.gob.es/...",
  "articulos": [
    {
      "norma": "LIRPF",
      "numero": "9",
      "titulo": "Rendimientos del trabajo",
      "casilla": "0002",
      "nota": "Rendimientos trabajo",
      "fuente": "Instrucción Modelo 100 2025",
      "url_fuente": "https://..."
    }
  ],
  "doctrina_relacionada": [
    {
      "referencia": "V0000-26",
      "organismo_emisor": "DGT",
      "fecha": "2024-01-15",
      "via_articulos": [
        { "norma": "LIRPF", "numero": "9" }
      ]
    }
  ]
}
```

### GET /v1/modelos/{codigo}/articulos
Solo artículos enlazados (para paginación futura o filtros).

Respuesta:
```json
{
  "codigo": "100",
  "articulos": [
    {
      "norma": "LIRPF",
      "numero": "9",
      "casilla": "0002",
      "nota": "Rendimientos trabajo",
      "fuente": "Instrucción Modelo 100 2025"
    }
  ]
}
```

## Frontend

### Sidebar en detalle artículo
Debajo de "Artículos vinculados" (doctrina):
```
Modelos AEAT relacionados
  Modelo 100 — IRPF Declaración anual  →
  Modelo 130 — IRPF Pago fraccionado   →
```

### Sidebar en detalle doctrina
Debajo de artículos vinculados:
```
Modelos AEAT relacionados
  Modelo 100 — IRPF Declaración anual  →
```
(Derivado: los artículos que ya enlaza esta doctrina tienen relación con modelos)

### Detalle de modelo — /modelo/[codigo]
- Nombre, período, impuesto
- Link "Ver en sede AEAT →"
- Grid 2 columnas: artículos relacionados + doctrina que los menciona

## Arquitectura

```
apps/
├── api/
│   ├── routers/modelos.py        # 3 endpoints
│   └── services/modelos.py       # helpers de consulta
├── web/
│   ├── app/modelo/[codigo]/page.tsx
│   ├── components/modelo-badge.tsx
│   ├── components/modelo-list.tsx
│   ├── lib/api.ts                # +fetch wrappers
│   └── lib/types.ts              # +interfaces
infra/sql/003_modelos_aeat.sql    # migración
scripts/seed-modelos.py           # carga inicial con fuentes
```

## Migración

`infra/sql/003_modelos_aeat.sql`:
```sql
CREATE TABLE IF NOT EXISTS aeat_modelo (
    id SERIAL PRIMARY KEY,
    codigo TEXT NOT NULL UNIQUE,
    nombre TEXT NOT NULL,
    periodo TEXT,
    impuesto TEXT,
    url_info TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS modelo_articulo (
    modelo_id INTEGER REFERENCES aeat_modelo(id) ON DELETE CASCADE,
    articulo_id INTEGER REFERENCES articulo(id) ON DELETE CASCADE,
    casilla TEXT,
    nota TEXT,
    fuente TEXT NOT NULL,
    url_fuente TEXT,
    PRIMARY KEY (modelo_id, articulo_id)
);
```

## Seed

`scripts/seed-modelos.py`:
- Conecta a DB local o producción via `DATABASE_URL`
- Inserta 6 modelos en `aeat_modelo` (idempotente con UPSERT)
- Inserta relaciones en `modelo_articulo` solo con fuente explícita
- Imprime resumen: "X modelos, Y relaciones con fuente"

## Fases de ejecución

### Batch A: Schema + Seed
- `003_modelos_aeat.sql`
- `scripts/seed-modelos.py`
- Verificar en DB local

### Batch B: API
- `routers/modelos.py` — 3 endpoints
- `services/modelos.py` — helpers
- `main.py` — registrar router
- Tests de endpoints

### Batch C: Frontend — Sidebars
- Sidebar en detalle artículo
- Sidebar en detalle doctrina
- `modelo-badge.tsx` y `modelo-list.tsx`

### Batch D: Frontend — Detalle modelo
- `/modelo/[codigo]/page.tsx`
- Verificar build

## Criterio de éxito

1. `GET /v1/modelos` devuelve 6 modelos
2. `GET /v1/modelos/100` devuelve artículos con fuente
3. En `/articulo/LIRPF/9` aparece sidebar con modelos
4. En `/doctrina/[ref]` aparece sidebar si hay doctrina→artículo→modelo
5. `/modelo/100` renderiza correctamente
6. Cada relación `modelo_articulo` tiene `fuente` no nula

## Riesgos y decisiones

- Riesgo: pocas relaciones iniciales por requisito de fuente
  - Decision: mejor calidad que cantidad; Fase 2 ampliará
- Riesgo: URLs de fuentes AEAT cambian o se rompen
  - Decision: almacenar snapshot del texto de la instrucción en nota si es crítico
- Riesgo: el usuario espera calendario/plazos
  - Decision: comunicar en UX que es "modelos relacionados", no calendario
