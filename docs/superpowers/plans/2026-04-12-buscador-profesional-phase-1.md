# [HISTORICAL] Buscador Profesional Phase 1 Implementation Plan

> Documento historico. No usar como plan activo. La fuente activa unica de estado y ejecucion es `docs/master-execution-roadmap.md`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir en `apps/web` una primera capa de producto en Next.js que permita buscar legislacion y doctrina, ver cobertura operativa y abrir el detalle de doctrina enlazada usando la API real de `esdata`.

**Architecture:** El frontend sera un servicio Next.js 15 separado dentro del monorepo, renderizado del lado del servidor y consumiendo la API FastAPI via `fetch`. La fase 1 se limita a contratos que ya existen: home con buscador y cobertura, resultados para legislacion y doctrina, y detalle de doctrina. No se anaden endpoints nuevos salvo que aparezca un bloqueo pequeno y claramente justificado.

**Tech Stack:** Next.js 15 App Router, TypeScript, Tailwind CSS, Vitest, React Testing Library, Railway.

---

## File structure

- Create: `apps/web/package.json`
- Create: `apps/web/tsconfig.json`
- Create: `apps/web/next.config.ts`
- Create: `apps/web/postcss.config.mjs`
- Create: `apps/web/tailwind.config.ts`
- Create: `apps/web/eslint.config.mjs`
- Create: `apps/web/.env.example`
- Create: `apps/web/.gitignore`
- Create: `apps/web/Dockerfile`
- Create: `apps/web/vitest.config.ts`
- Create: `apps/web/tests/setup.ts`
- Create: `apps/web/lib/env.ts`
- Create: `apps/web/lib/types.ts`
- Create: `apps/web/lib/api.ts`
- Create: `apps/web/lib/search-params.ts`
- Create: `apps/web/lib/format.ts`
- Create: `apps/web/app/layout.tsx`
- Create: `apps/web/app/globals.css`
- Create: `apps/web/app/page.tsx`
- Create: `apps/web/app/buscar/page.tsx`
- Create: `apps/web/app/doctrina/[...referencia]/page.tsx`
- Create: `apps/web/app/not-found.tsx`
- Create: `apps/web/components/site-header.tsx`
- Create: `apps/web/components/search-box.tsx`
- Create: `apps/web/components/tab-switcher.tsx`
- Create: `apps/web/components/coverage-panel.tsx`
- Create: `apps/web/components/organism-badge.tsx`
- Create: `apps/web/components/confidence-badge.tsx`
- Create: `apps/web/components/legislacion-result-card.tsx`
- Create: `apps/web/components/doctrina-result-card.tsx`
- Create: `apps/web/components/doctrina-detail.tsx`
- Create: `apps/web/tests/lib/env.test.ts`
- Create: `apps/web/tests/lib/search-params.test.ts`
- Create: `apps/web/tests/components/confidence-badge.test.tsx`
- Create: `apps/web/tests/components/search-box.test.tsx`
- Create: `apps/web/tests/components/doctrina-detail.test.tsx`
- Modify: `railway.toml`
- Modify: `.github/workflows/deploy.yml`
- Modify: `README.md`
- Modify: `STRUCTURE.md`

## Implementation notes locked before coding

- Use a server-only API base variable: `ESDATA_API_BASE_URL`.
- Do not use `NEXT_PUBLIC_API_URL` because the data fetching in this slice is server-side.
- Do not add on-demand revalidation in phase 1. `revalidate = 3600` is enough.
- Do not add pagination UI that suggests a backend capability that does not exist.
- Keep route state in URL query params so every search is shareable.

## Task 1: Scaffold `apps/web` with minimal tooling

**Files:**
- Create: `apps/web/package.json`
- Create: `apps/web/tsconfig.json`
- Create: `apps/web/next.config.ts`
- Create: `apps/web/postcss.config.mjs`
- Create: `apps/web/tailwind.config.ts`
- Create: `apps/web/eslint.config.mjs`
- Create: `apps/web/.env.example`
- Create: `apps/web/.gitignore`
- Create: `apps/web/Dockerfile`
- Create: `apps/web/vitest.config.ts`
- Create: `apps/web/tests/setup.ts`
- Create: `apps/web/lib/env.ts`
- Test: `apps/web/tests/lib/env.test.ts`

- [ ] **Step 1: Write the failing env test**

```ts
import { describe, expect, it } from "vitest"
import { resolveApiBaseUrl } from "@/lib/env"

describe("resolveApiBaseUrl", () => {
  it("accepts Railway and local URLs without trailing slash", () => {
    expect(resolveApiBaseUrl("https://esdata-production.up.railway.app/")).toBe(
      "https://esdata-production.up.railway.app"
    )
  })
})
```

- [ ] **Step 2: Run the env test and verify it fails**

Run: `npm run test -- env.test.ts`
Expected: FAIL because `@/lib/env` or `resolveApiBaseUrl` does not exist yet.

- [ ] **Step 3: Scaffold the Next.js app and test tooling**

Run:

```bash
npx create-next-app@latest apps/web --typescript --tailwind --eslint --app --use-npm --import-alias "@/*"
```

Then replace the generated package configuration with a minimal runtime and explicit test scripts:

```json
{
  "name": "esdata-web",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "test": "vitest run"
  }
}
```

Add `apps/web/lib/env.ts` with the minimal implementation:

```ts
export function resolveApiBaseUrl(value: string | undefined): string {
  if (!value) {
    throw new Error("Missing ESDATA_API_BASE_URL")
  }

  return value.endsWith("/") ? value.slice(0, -1) : value
}

export const API_BASE_URL = resolveApiBaseUrl(process.env.ESDATA_API_BASE_URL)
```

Use standalone output for Railway in `apps/web/next.config.ts`:

```ts
import type { NextConfig } from "next"

const nextConfig: NextConfig = {
  output: "standalone",
}

export default nextConfig
```

Create `apps/web/.env.example`:

```env
ESDATA_API_BASE_URL=https://esdata-production.up.railway.app
```

Create a Dockerfile that runs the standalone server:

```dockerfile
FROM node:22-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
CMD ["node", "server.js"]
```

- [ ] **Step 4: Run the env test and verify it passes**

Run: `npm run test -- env.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit the scaffold**

```bash
git add apps/web
git commit -m "feat(web): scaffold Next.js frontend app"
```

## Task 2: Define API types and fetch wrappers

**Files:**
- Create: `apps/web/lib/types.ts`
- Create: `apps/web/lib/api.ts`
- Test: `apps/web/tests/lib/search-params.test.ts`

- [ ] **Step 1: Write the failing query helper test**

```ts
import { describe, expect, it } from "vitest"
import { buildSearchHref } from "@/lib/search-params"

describe("buildSearchHref", () => {
  it("preserves active tab in search navigation", () => {
    expect(buildSearchHref({ q: "prorrata general", tab: "teac" })).toBe(
      "/buscar?q=prorrata+general&tab=teac"
    )
  })
})
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `npm run test -- search-params.test.ts`
Expected: FAIL because the helper does not exist yet.

- [ ] **Step 3: Add API types and wrappers**

Create `apps/web/lib/types.ts` with only the response shapes that already exist in FastAPI:

```ts
export type SearchTab = "legislacion" | "dgt" | "teac"

export interface LegislacionSearchItem {
  tipo: string
  norma: string
  numero: string
  texto: string
  fragmento: string
  vigente_desde: string
  vigente_hasta: string | null
  rank: number | null
  confianza: {
    nivel: number
    fuentes: string[]
    aviso: string | null
  }
}

export interface DoctrinaSearchItem {
  referencia: string
  tipo_documento: string
  organismo_emisor: string
  fecha: string
  titulo: string | null
  nivel_enlace: number
  norma: string | null
  numero: string | null
  fragmento: string
}
```

Create `apps/web/lib/api.ts` as server-side wrappers:

```ts
import { API_BASE_URL } from "@/lib/env"

async function apiFetch<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    next: { revalidate: 3600 },
  })

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`)
  }

  return response.json() as Promise<T>
}
```

Also add functions for:

- `getCoverage()` -> `/v1/legislacion/cobertura`
- `getStatus()` -> `/status`
- `searchLegislacion(params)` -> `/v1/buscar`
- `searchDoctrina(params)` -> `/v1/doctrina/buscar`
- `getDoctrina(referencia)` -> `/v1/doctrina/${referencia}`

Create `apps/web/lib/search-params.ts`:

```ts
import type { SearchTab } from "@/lib/types"

export function buildSearchHref({ q, tab }: { q: string; tab: SearchTab }) {
  const params = new URLSearchParams({ q, tab })
  return `/buscar?${params.toString()}`
}
```

- [ ] **Step 4: Run the helper test and verify it passes**

Run: `npm run test -- search-params.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit API wiring**

```bash
git add apps/web/lib apps/web/tests/lib/search-params.test.ts
git commit -m "feat(web): add typed API client"
```

## Task 3: Build reusable visual primitives

**Files:**
- Create: `apps/web/lib/format.ts`
- Create: `apps/web/components/organism-badge.tsx`
- Create: `apps/web/components/confidence-badge.tsx`
- Test: `apps/web/tests/components/confidence-badge.test.tsx`

- [ ] **Step 1: Write the failing confidence badge test**

```tsx
import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { ConfidenceBadge } from "@/components/confidence-badge"

describe("ConfidenceBadge", () => {
  it("shows the strongest message for 1.0 confidence", () => {
    render(<ConfidenceBadge confidence={1} />)
    expect(screen.getByText("Enlace de confianza maxima")).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `npm run test -- confidence-badge.test.tsx`
Expected: FAIL because the component does not exist yet.

- [ ] **Step 3: Implement badge primitives**

Create `apps/web/components/confidence-badge.tsx`:

```tsx
export function ConfidenceBadge({ confidence }: { confidence: number }) {
  if (confidence >= 1) {
    return <span className="text-green-700">Enlace de confianza maxima</span>
  }

  if (confidence >= 0.85) {
    return <span className="text-amber-700">Enlace probable</span>
  }

  return <span className="text-stone-600">Enlace por revisar</span>
}
```

Create `apps/web/components/organism-badge.tsx`:

```tsx
export function OrganismBadge({ organismo }: { organismo: "DGT" | "TEAC" }) {
  const className =
    organismo === "DGT"
      ? "text-blue-700 bg-blue-50"
      : "text-violet-700 bg-violet-50"

  return <span className={`rounded-full px-2 py-1 text-xs font-medium ${className}`}>{organismo}</span>
}
```

Create `apps/web/lib/format.ts` for small shared helpers:

```ts
export function formatDate(value: string) {
  return new Intl.DateTimeFormat("es-ES", { dateStyle: "medium" }).format(new Date(value))
}
```

- [ ] **Step 4: Run the confidence test and verify it passes**

Run: `npm run test -- confidence-badge.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit the visual primitives**

```bash
git add apps/web/components apps/web/lib/format.ts apps/web/tests/components/confidence-badge.test.tsx
git commit -m "feat(web): add result badges and format helpers"
```

## Task 4: Implement the app shell and home page

**Files:**
- Create: `apps/web/app/layout.tsx`
- Create: `apps/web/app/globals.css`
- Create: `apps/web/app/page.tsx`
- Create: `apps/web/components/site-header.tsx`
- Create: `apps/web/components/search-box.tsx`
- Create: `apps/web/components/tab-switcher.tsx`
- Create: `apps/web/components/coverage-panel.tsx`
- Test: `apps/web/tests/components/search-box.test.tsx`

- [ ] **Step 1: Write the failing search box test**

```tsx
import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { SearchBox } from "@/components/search-box"

describe("SearchBox", () => {
  it("renders the editorial placeholder", () => {
    render(<SearchBox initialQuery="" activeTab="legislacion" />)
    expect(
      screen.getByPlaceholderText("Buscar legislacion, doctrina, criterios...")
    ).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `npm run test -- search-box.test.tsx`
Expected: FAIL because the component does not exist yet.

- [ ] **Step 3: Build the shell and home UI**

`apps/web/app/layout.tsx` should set title and typography:

```tsx
import type { Metadata } from "next"
import "./globals.css"

export const metadata: Metadata = {
  title: "esdata",
  description: "Buscador profesional de legislacion y doctrina fiscal espanola",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body className="bg-stone-50 text-stone-900 antialiased">{children}</body>
    </html>
  )
}
```

`apps/web/app/page.tsx` should fetch in parallel:

```tsx
import { getCoverage, getStatus } from "@/lib/api"

export default async function HomePage() {
  const [coverage, status] = await Promise.all([getCoverage(), getStatus()])
  return <main>{/* hero + examples + coverage + status */}</main>
}
```

The home examples should be hard-coded to proven searches:

- `deducciones inversion LIS`
- `entregas inmuebles IVA`
- `prorrata general`
- `criterio IRPF teletrabajo`

`apps/web/components/coverage-panel.tsx` should summarize:

- per-norma article counts from `/v1/legislacion/cobertura`
- total articles
- total versions
- status label from `/status`

Keep the home page server-rendered. The search form can be a tiny client component only if needed for tab-aware navigation.

- [ ] **Step 4: Run the search box test and verify it passes**

Run: `npm run test -- search-box.test.tsx`
Expected: PASS.

- [ ] **Step 5: Run lint and build for the first route**

Run:

```bash
npm run lint
npm run build
```

Expected: both commands PASS.

- [ ] **Step 6: Commit the home page**

```bash
git add apps/web/app apps/web/components apps/web/tests/components/search-box.test.tsx
git commit -m "feat(web): add search home and coverage view"
```

## Task 5: Implement the results page

**Files:**
- Create: `apps/web/app/buscar/page.tsx`
- Create: `apps/web/components/legislacion-result-card.tsx`
- Create: `apps/web/components/doctrina-result-card.tsx`
- Modify: `apps/web/components/tab-switcher.tsx`
- Modify: `apps/web/lib/api.ts`

- [ ] **Step 1: Write the failing results query test**

```ts
import { describe, expect, it } from "vitest"
import { buildSearchHref } from "@/lib/search-params"

describe("buildSearchHref", () => {
  it("keeps doctrine tabs explicit in the URL", () => {
    expect(buildSearchHref({ q: "entregas inmuebles IVA", tab: "dgt" })).toBe(
      "/buscar?q=entregas+inmuebles+IVA&tab=dgt"
    )
  })
})
```

- [ ] **Step 2: Run the test and verify it fails for the missing tab case**

Run: `npm run test -- search-params.test.ts`
Expected: FAIL until `buildSearchHref` fully supports the `tab` flow the page needs.

- [ ] **Step 3: Implement the results route**

In `apps/web/app/buscar/page.tsx`, read `searchParams` asynchronously and branch by tab:

```tsx
type BuscarPageProps = {
  searchParams: Promise<{ q?: string; tab?: string; norma?: string; tipo?: string; desde?: string; vigente_en?: string }>
}

export default async function BuscarPage({ searchParams }: BuscarPageProps) {
  const params = await searchParams
  const tab = params.tab === "dgt" || params.tab === "teac" ? params.tab : "legislacion"
  const query = params.q?.trim() ?? ""

  if (!query) {
    return <main>Falta una consulta.</main>
  }

  // branch to searchLegislacion or searchDoctrina
}
```

Implement `legislacion-result-card.tsx` and `doctrina-result-card.tsx` as presentational components.

For doctrine tabs:

- `dgt` calls `searchDoctrina({ q, organismo_emisor: "DGT" })`
- `teac` calls `searchDoctrina({ q, organismo_emisor: "TEAC" })`

For phase 1, show only filters that map directly to existing API params.

The results page must show:

- active tab
- total shown count
- note `Mostrando los primeros N resultados`

- [ ] **Step 4: Run lint and targeted tests**

Run:

```bash
npm run test -- search-params.test.ts
npm run lint
```

Expected: PASS.

- [ ] **Step 5: Commit the results page**

```bash
git add apps/web/app/buscar apps/web/components apps/web/lib
git commit -m "feat(web): add legislation and doctrine search results"
```

## Task 6: Implement doctrine detail

**Files:**
- Create: `apps/web/app/doctrina/[...referencia]/page.tsx`
- Create: `apps/web/components/doctrina-detail.tsx`
- Create: `apps/web/app/not-found.tsx`
- Test: `apps/web/tests/components/doctrina-detail.test.tsx`

- [ ] **Step 1: Write the failing doctrine detail test**

```tsx
import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { DoctrinaDetail } from "@/components/doctrina-detail"

describe("DoctrinaDetail", () => {
  it("shows linked article references", () => {
    render(
      <DoctrinaDetail
        doctrina={{
          referencia: "00/01454/2023/00/00",
          tipo_documento: "resolucion_teac",
          organismo_emisor: "TEAC",
          texto: "Texto",
          articulos_relacionados: [{ norma: "LIVA", numero: "104", metodo_enlace: "auto_link", confianza_enlace: 1 }],
          confianza: { nivel: 2, fuentes: ["00/01454/2023/00/00"], aviso: null },
        }}
      />
    )

    expect(screen.getByText("LIVA art. 104")).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `npm run test -- doctrina-detail.test.tsx`
Expected: FAIL because the component does not exist yet.

- [ ] **Step 3: Build the doctrine detail route**

`apps/web/app/doctrina/[...referencia]/page.tsx` should reconstruct the reference from the catch-all segment and call `getDoctrina(referencia)`.

```tsx
type DoctrinaPageProps = {
  params: Promise<{ referencia: string[] }>
}

export default async function DoctrinaPage({ params }: DoctrinaPageProps) {
  const { referencia } = await params
  const joined = referencia.join("/")
  const doctrina = await getDoctrina(joined)
  return <DoctrinaDetail doctrina={doctrina} />
}
```

`apps/web/components/doctrina-detail.tsx` must render:

- back link to `/buscar`
- referencia, tipo, organismo y fecha if present
- doctrinal text in the main column
- linked articles in the side column
- `ConfidenceBadge` per article or summary block

Use `notFound()` only for actual 404s.

- [ ] **Step 4: Run the doctrine detail test and build**

Run:

```bash
npm run test -- doctrina-detail.test.tsx
npm run build
```

Expected: PASS.

- [ ] **Step 5: Commit doctrine detail**

```bash
git add apps/web/app/doctrina apps/web/components apps/web/tests/components/doctrina-detail.test.tsx
git commit -m "feat(web): add doctrine detail page"
```

## Task 7: Add Railway deploy wiring and docs

**Files:**
- Modify: `railway.toml`
- Modify: `.github/workflows/deploy.yml`
- Modify: `README.md`
- Modify: `STRUCTURE.md`

- [ ] **Step 1: Write the failing deployment expectation as a checklist**

The new service is not deployed until all of these are true:

- `railway.toml` contains a `web` service rooted at `apps/web`
- GitHub Actions deploys `apps/web`
- README documents `ESDATA_API_BASE_URL`
- STRUCTURE lists `apps/web`

- [ ] **Step 2: Add the Railway service**

Append to `railway.toml`:

```toml
[[services]]
name = "web"
rootDirectory = "apps/web"

[services.deploy]
startCommand = "npm run build && npm run start"
healthcheckPath = "/"
healthcheckTimeout = 30
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

- [ ] **Step 3: Add deploy workflow support for `web`**

Add a new job step to `.github/workflows/deploy.yml` following the worker pattern:

```yaml
      - name: Deploy web a Railway
        shell: bash
        run: |
          set -euo pipefail
          if ! railway up apps/web --path-as-root --service web --project $RAILWAY_PROJECT_ID --environment $RAILWAY_ENVIRONMENT --detach; then
            railway add --service web --json
            railway up apps/web --path-as-root --service web --project $RAILWAY_PROJECT_ID --environment $RAILWAY_ENVIRONMENT --detach
          fi
```

Do not add frontend smoke tests in this commit unless the app is already implemented and deployable.

- [ ] **Step 4: Update docs**

Add to `README.md`:

- new `apps/web` app
- local commands:
  - `npm install`
  - `npm run dev`
  - `npm run test`
  - `npm run build`
- env variable: `ESDATA_API_BASE_URL`

Add to `STRUCTURE.md`:

- `apps/web`
- main routes and shared libs

- [ ] **Step 5: Run final verification**

Run:

```bash
npm run test
npm run lint
npm run build
pytest apps/api/tests/test_smoke.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit deploy wiring and docs**

```bash
git add railway.toml .github/workflows/deploy.yml README.md STRUCTURE.md
git commit -m "feat(web): add Railway deploy wiring"
```

## Manual verification checklist

- [ ] `GET /` shows the main search bar, tabs, examples, coverage and operational status.
- [ ] Searching `IVA` in `Legislacion` shows legislative results.
- [ ] Searching `entregas inmuebles IVA` in `DGT` shows doctrine results.
- [ ] Searching `prorrata general` in `TEAC` renders the TEAC path correctly even if no results appear.
- [ ] Opening `00/01454/2023/00/00` shows `LIVA art. 104` and `LIVA art. 8` as linked articles.
- [ ] The app survives an empty `q` on `/buscar` without crashing.
- [ ] Railway health check for `web` returns `200` on `/`.

## Spec coverage self-review

- Home with editorial search and real examples: covered by Task 4.
- Coverage and status block using real API data: covered by Task 4.
- Results page for legislation and doctrine with tab split: covered by Task 5.
- Doctrine detail with linked articles and confidence: covered by Task 6.
- Railway deploy in same project: covered by Task 7.
- Out-of-scope items like pagination, article-detail doctrine panel and radar are intentionally excluded from tasks.
