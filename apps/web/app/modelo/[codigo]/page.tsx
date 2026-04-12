import { notFound } from "next/navigation";
import Link from "next/link";
import Header from "@/components/header";
import ConfidenceBadge from "@/components/confidence-badge";
import { getModelo } from "@/lib/api";

export default async function ModeloPage({
  params,
}: {
  params: Promise<{ codigo: string }>;
}) {
  const { codigo } = await params;

  let data;
  try {
    data = await getModelo(codigo);
  } catch {
    return notFound();
  }

  return (
    <div className="min-h-screen">
      <Header />
      <main className="mx-auto max-w-5xl px-6 py-8">
        {/* Breadcrumb */}
        <Link
          href="/"
          className="mb-6 inline-block text-xs text-stone-500 hover:text-stone-900 transition-colors"
        >
          ← Volver al buscador
        </Link>

        {/* Identity */}
        <div className="mb-2 flex items-center gap-3">
          <span className="rounded bg-stone-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-stone-600">
            AEAT
          </span>
          <span className="font-mono text-sm text-stone-500">
            Modelo {data.codigo}
          </span>
          <span className="text-sm text-stone-300">·</span>
          <span className="text-sm text-stone-400">{data.impuesto}</span>
          {data.periodo && (
            <>
              <span className="text-sm text-stone-300">·</span>
              <span className="text-sm text-stone-400">{data.periodo}</span>
            </>
          )}
        </div>

        <h1 className="mb-2 font-serif text-2xl font-semibold leading-tight text-stone-900">
          {data.nombre}
        </h1>

        {data.url_info && (
          <a
            href={data.url_info}
            target="_blank"
            rel="noopener noreferrer"
            className="mb-8 inline-block text-xs text-blue-700 hover:text-blue-900 transition-colors"
          >
            Ver en sede AEAT →
          </a>
        )}

        {/* Two-column layout */}
        <div className="grid gap-8 md:grid-cols-3">
          {/* Articles */}
          <div className="md:col-span-2">
            <h2 className="mb-4 text-sm font-semibold text-stone-900">
              Artículos relacionados ({data.articulos.length})
            </h2>
            {data.articulos.length === 0 ? (
              <p className="text-sm text-stone-400">
                No hay artículos vinculados a este modelo todavía.
              </p>
            ) : (
              <ul className="divide-y divide-stone-200">
                {data.articulos.map((a) => (
                  <li key={a.norma + a.numero} className="py-3">
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0 flex-1">
                        <Link
                          href={`/articulo/${a.norma}/${a.numero}`}
                          className="font-mono text-sm font-medium text-stone-700 hover:text-stone-900 transition-colors"
                        >
                          {a.norma} art. {a.numero}
                        </Link>
                        {a.titulo && (
                          <p className="text-xs text-stone-500 mt-0.5">
                            {a.titulo}
                          </p>
                        )}
                        {a.casilla && (
                          <p className="text-xs text-stone-400 mt-0.5">
                            Casilla {a.casilla}
                            {a.nota ? ` — ${a.nota}` : ""}
                          </p>
                        )}
                        {a.fuente && (
                          <p className="text-[11px] text-stone-400 mt-1">
                            {a.fuente}
                            {a.url_fuente && (
                              <>
                                {" "}
                                ·{" "}
                                <a
                                  href={a.url_fuente}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-blue-600 hover:text-blue-800 underline"
                                >
                                  fuente
                                </a>
                              </>
                            )}
                          </p>
                        )}
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Sidebar: Related doctrine */}
          <aside className="shrink-0">
            <div className="rounded-md border border-stone-200 bg-white p-4">
              <h2 className="mb-3 text-sm font-semibold text-stone-900">
                Doctrina que lo menciona
              </h2>
              {data.doctrina_relacionada.length === 0 ? (
                <p className="text-xs text-stone-400">
                  No hay doctrina vinculada a los artículos de este modelo.
                </p>
              ) : (
                <ul className="space-y-3">
                  {data.doctrina_relacionada.map((d) => (
                    <li key={d.referencia}>
                      <Link
                        href={`/doctrina/${d.referencia}`}
                        className="block text-xs font-medium text-stone-700 hover:text-stone-900 transition-colors"
                      >
                        {d.referencia}
                      </Link>
                      <p className="text-[11px] text-stone-400 mt-0.5">
                        {d.organismo_emisor}
                        {d.fecha && ` · ${d.fecha}`}
                      </p>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {d.via_articulos.slice(0, 3).map((va) => (
                          <span
                            key={va.norma + va.numero}
                            className="font-mono text-[10px] text-stone-500 bg-stone-50 px-1 rounded"
                          >
                            {va.norma} {va.numero}
                          </span>
                        ))}
                        {d.via_articulos.length > 3 && (
                          <span className="text-[10px] text-stone-400">
                            +{d.via_articulos.length - 3}
                          </span>
                        )}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}
