import { notFound } from "next/navigation";
import Link from "next/link";
import Header from "@/components/header";
import ModeloList from "@/components/modelo-list";
import { getArticulo, getArticuloHistorial } from "@/lib/api";

export default async function ArticuloPage({
  params,
  searchParams,
}: {
  params: Promise<{ norma: string; numero: string }>;
  searchParams: Promise<{ q?: string; tab?: string; vigente_en?: string }>;
}) {
  const { norma, numero } = await params;
  const sParams = await searchParams;
  const q = sParams.q || "";
  const tab = sParams.tab || "legislacion";
  const vigenteEn = sParams.vigente_en;

  let data;
  let historial;
  try {
    data = await getArticulo(norma, numero, vigenteEn);
    historial = await getArticuloHistorial(norma, numero);
  } catch {
    return notFound();
  }

  return (
    <div className="min-h-screen">
      <Header />
      <main className="mx-auto max-w-5xl px-6 py-8">
        {/* Breadcrumb */}
        <Link
          href={`/buscar?q=${encodeURIComponent(q)}&tab=${tab}`}
          className="mb-6 inline-block text-xs text-stone-500 hover:text-stone-900 transition-colors"
        >
          ← Volver a resultados
        </Link>

        {/* Identity */}
        <div className="mb-6 flex items-center gap-3">
          <span className="rounded bg-stone-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-stone-600">
            Legislación
          </span>
          <span className="font-mono text-sm text-stone-500">
            {data.norma} art. {data.numero}
          </span>
          {data.vigente_desde && (
            <span className="text-xs text-amber-600 font-medium">
              Vigente desde {data.vigente_desde}
              {data.vigente_hasta ? ` hasta ${data.vigente_hasta}` : " (Actual)"}
            </span>
          )}
        </div>

        <div className="grid gap-8 md:grid-cols-3">
          {/* Main content */}
          <div className="md:col-span-2">
            <h1 className="mb-8 font-serif text-2xl font-semibold leading-tight text-stone-900">
              Artículo {data.numero}
            </h1>
            <div className="font-serif text-sm leading-relaxed whitespace-pre-line text-stone-800">
              {data.texto}
            </div>
          </div>

          {/* Sidebar: History */}
          <aside className="shrink-0">
            <div className="rounded-md border border-stone-200 bg-white p-4">
              <h2 className="mb-3 text-sm font-semibold text-stone-900">
                Historial de versiones
              </h2>
              {historial.historial.length <= 1 ? (
                <p className="text-xs text-stone-400">
                  No hay versiones históricas registradas.
                </p>
              ) : (
                <ul className="space-y-4">
                  {historial.historial.map((v, i) => {
                    const isActive = v.vigente_desde === data.vigente_desde;
                    return (
                      <li key={i} className="relative pl-4 border-l-2 border-stone-100">
                        <div className={`absolute -left-[9px] top-1 h-4 w-4 rounded-full border-4 border-white ${isActive ? 'bg-amber-500' : 'bg-stone-200'}`} />
                        <Link
                          href={`/articulo/${norma}/${numero}?vigente_en=${v.vigente_desde}&q=${encodeURIComponent(q)}&tab=${tab}`}
                          className={`text-xs font-medium ${isActive ? 'text-stone-900' : 'text-stone-500 hover:text-stone-900'} transition-colors`}
                        >
                          Versión {v.vigente_desde}
                        </Link>
                        {v.vigente_hasta && (
                          <p className="text-[10px] text-stone-400">Hasta {v.vigente_hasta}</p>
                        )}
                        {isActive && <span className="text-[10px] text-amber-600 block mt-0.5 font-semibold">Visualizando</span>}
                      </li>
                    );
                  })}
                </ul>
              )}
              <ModeloList articuloNorma={norma} articuloNumero={numero} />
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}
