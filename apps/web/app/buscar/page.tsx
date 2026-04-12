import { Suspense } from "react";
import { notFound } from "next/navigation";
import Header from "@/components/header";
import Tabs from "@/components/tabs";
import ResultCard from "@/components/legislacion-card";
import DoctrinaCard from "@/components/doctrina-card";
import { searchLegislacion, searchDoctrina } from "@/lib/api";

type TabKey = "legislacion" | "dgt" | "teac";

function tabToOrganismo(tab: TabKey): string | undefined {
  if (tab === "dgt") return "DGT";
  if (tab === "teac") return "TEAC";
  return undefined;
}

export default async function BuscarPage({
  searchParams,
}: {
  searchParams: Promise<{
    q?: string;
    tab?: string;
    norma?: string;
    fuente?: string;
    ambito?: string;
    tipo?: string;
    vigente_en?: string;
    desde?: string;
  }>;
}) {
  const params = await searchParams;
  const q = params.q?.trim() || "";
  const tab = (params.tab === "dgt" || params.tab === "teac" ? params.tab : "legislacion") as TabKey;

  return (
    <div className="min-h-screen">
      <Header query={q} />
      <main className="mx-auto max-w-5xl px-6 py-8">
        <div className="mb-6">
          <Tabs
            active={tab}
            href={(t) => `/buscar?q=${encodeURIComponent(q)}&tab=${t}`}
          />
        </div>
        {!q ? (
          <div className="py-20 text-center">
            <h2 className="text-xl font-serif text-stone-900 mb-2">Buscador experto</h2>
            <p className="text-stone-500 text-sm">Introduce un término para comenzar la búsqueda legal.</p>
          </div>
        ) : (
          <Suspense
            fallback={
              <div className="space-y-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-20 animate-pulse rounded-md bg-stone-200" />
                ))}
              </div>
            }
          >
            <Results q={q} tab={tab} params={params} />
          </Suspense>
        )}
      </main>
    </div>
  );
}

async function Results({
  q,
  tab,
  params,
}: {
  q: string;
  tab: TabKey;
  params: { norma?: string; fuente?: string; ambito?: string; tipo?: string; vigente_en?: string; desde?: string };
}) {
  // Legislacion search
  if (tab === "legislacion") {
    let data: Awaited<ReturnType<typeof searchLegislacion>> | null = null;
    try {
      data = await searchLegislacion(q, {
        norma: params.norma,
        fuente: params.fuente,
        ambito: params.ambito,
        tipo: params.tipo,
        vigenteEn: params.vigente_en,
      });
    } catch {
      /* empty */
    }

    if (!data || data.resultados.length === 0) {
      return (
        <p className="py-12 text-center text-sm text-stone-400">
          No se encontraron resultados para &ldquo;{q}&rdquo; en legislación.
        </p>
      );
    }

    return (
      <div>
        <p className="mb-4 text-xs text-stone-400">
          {data.resultados.length} resultado{data.resultados.length !== 1 ? "s" : ""} en legislación
        </p>
        <div className="divide-y divide-stone-200">
          {data.resultados.map((r) => (
            <ResultCard
              key={r.norma + r.numero + r.vigente_desde}
              norma={r.norma}
              numero={r.numero}
              fragmento={r.fragmento}
              vigenteDesde={r.vigente_desde}
              vigenteHasta={r.vigente_hasta}
              confianzaNivel={r.confianza.nivel}
              href={`/articulo/${r.norma}/${r.numero}?vigente_en=${r.vigente_desde}`}
            />
          ))}
        </div>
        <p className="mt-6 text-center text-xs text-stone-400">
          Mostrando los primeros {data.resultados.length} resultados.
        </p>
      </div>
    );
  }

  // Doctrina search (DGT or TEAC)
  const organismo = tabToOrganismo(tab);
  let data: Awaited<ReturnType<typeof searchDoctrina>> | null = null;
  try {
    data = await searchDoctrina(q, {
      organismoEmisor: organismo,
      desde: params.desde,
    });
  } catch {
    /* empty */
  }

  if (!data || data.resultados.length === 0) {
    return (
      <p className="py-12 text-center text-sm text-stone-400">
        No se encontraron resultados para &ldquo;{q}&rdquo; en {organismo}.
      </p>
    );
  }

  return (
    <div>
      <p className="mb-4 text-xs text-stone-400">
        {data.resultados.length} resultado{data.resultados.length !== 1 ? "s" : ""} en {organismo}
      </p>
      <div className="divide-y divide-stone-200">
        {data.resultados.map((r) => (
          <DoctrinaCard
            key={r.referencia}
            referencia={r.referencia}
            organismo={r.organismo_emisor}
            tipoDocumento={r.tipo_documento}
            fecha={r.fecha}
            titulo={r.titulo}
            fragmento={r.fragmento}
            href={`/doctrina/${r.referencia}`}
          />
        ))}
      </div>
      <p className="mt-6 text-center text-xs text-stone-400">
        Mostrando los primeros {data.resultados.length} resultados.
      </p>
    </div>
  );
}
