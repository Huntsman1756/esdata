import { notFound } from "next/navigation";
import Link from "next/link";
import Header from "@/components/header";
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
          {data.campana_activa && (
            <>
              <span className="text-sm text-stone-300">·</span>
              <span className="text-sm text-stone-400">
                Campaña {data.campana_activa}
              </span>
            </>
          )}
          {data.impuesto && (
            <>
              <span className="text-sm text-stone-300">·</span>
              <span className="text-sm text-stone-400">{data.impuesto}</span>
            </>
          )}
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

        {/* Campaign selector */}
        {data.campanas.length > 1 && (
          <div className="mb-6 flex items-center gap-2">
            <span className="text-xs font-semibold text-stone-600">Campañas:</span>
            {data.campanas.map((c) => (
              <span
                key={c.campana}
                className={`rounded px-2 py-0.5 text-xs ${
                  c.activo
                    ? "bg-green-100 text-green-800 font-semibold"
                    : "bg-stone-100 text-stone-400"
                }`}
              >
                {c.campana} {c.activo ? "(activa)" : ""}
              </span>
            ))}
          </div>
        )}

        {/* Quick stats */}
        <div className="mb-8 flex flex-wrap gap-4 text-xs text-stone-500">
          <span>
            <strong className="text-stone-700">{data.articulos.length}</strong>{" "}
            artículos
          </span>
          <span>
            <strong className="text-stone-700">{data.casillas.length}</strong>{" "}
            casillas
          </span>
          {data.claves.length > 0 && (
            <span>
              <strong className="text-stone-700">{data.claves.length}</strong>{" "}
              claves
            </span>
          )}
          <span>
            <strong className="text-stone-700">{data.normativa.length}</strong>{" "}
            normativa{data.normativa.length !== 1 ? "s" : ""}
          </span>
        </div>

        {/* Tabs */}
        <div className="mb-6 border-b border-stone-200">
          <div className="flex gap-4 text-sm">
            <TabLink href="#instrucciones" label="Instrucciones" />
            <TabLink href="#casillas" label={`Casillas (${data.casillas.length})`} />
            {data.claves.length > 0 && (
              <TabLink href="#claves" label={`Claves (${data.claves.length})`} />
            )}
            <TabLink href="#articulos" label={`Artículos (${data.articulos.length})`} />
            <TabLink href="#normativa" label="Normativa" />
          </div>
        </div>

        {/* Instructions */}
        <section id="instrucciones" className="mb-10">
          <h2 className="mb-4 text-sm font-semibold text-stone-900">
            Instrucciones
          </h2>
          {data.instrucciones.length === 0 ? (
            <p className="text-sm text-stone-400">
              Instrucciones no disponibles para este modelo. Consulte la sede AEAT.
            </p>
          ) : (
            <div className="space-y-6">
              {data.instrucciones.map((inst) => (
                <div key={inst.seccion + inst.orden} className="rounded-lg border border-stone-200 bg-white p-5">
                  <h3 className="mb-2 font-semibold text-stone-800">
                    {inst.titulo}
                  </h3>
                  <div className="whitespace-pre-line text-sm text-stone-600 leading-relaxed">
                    {inst.contenido}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Casillas */}
        <section id="casillas" className="mb-10">
          <h2 className="mb-4 text-sm font-semibold text-stone-900">
            Casillas ({data.casillas.length})
          </h2>
          {data.casillas.length === 0 ? (
            <p className="text-sm text-stone-400">
              No hay casillas registradas para este modelo.
            </p>
          ) : (
            <ul className="divide-y divide-stone-200">
              {data.casillas.map((c) => (
                <li key={c.codigo} className="py-3">
                  <div className="flex items-start gap-3">
                    <span className="font-mono text-xs font-bold text-stone-700 bg-stone-100 px-2 py-0.5 rounded shrink-0">
                      {c.codigo}
                    </span>
                    <div className="min-w-0 flex-1">
                      <span className="text-sm font-medium text-stone-700">
                        {c.etiqueta}
                      </span>
                      {c.descripcion && (
                        <p className="text-xs text-stone-500 mt-0.5">
                          {c.descripcion}
                        </p>
                      )}
                      {c.tipo_casilla && (
                        <span className="inline-block mt-1 text-[10px] text-stone-400 bg-stone-50 px-1.5 py-0.5 rounded">
                          {c.tipo_casilla}
                        </span>
                      )}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* Claves */}
        {data.claves.length > 0 && (
          <section id="claves" className="mb-10">
            <h2 className="mb-4 text-sm font-semibold text-stone-900">
              Claves ({data.claves.length})
            </h2>
            <ul className="divide-y divide-stone-200">
              {data.claves.map((c) => (
                <li key={c.codigo} className="py-3">
                  <div className="flex items-start gap-3">
                    <span className="font-mono text-xs font-bold text-stone-700 bg-amber-50 px-2 py-0.5 rounded shrink-0">
                      {c.codigo}
                    </span>
                    <div className="min-w-0 flex-1">
                      <span className="text-sm font-medium text-stone-700">
                        {c.etiqueta}
                      </span>
                      {c.descripcion && (
                        <p className="text-xs text-stone-500 mt-0.5">
                          {c.descripcion}
                        </p>
                      )}
                      {c.tipo_clave && (
                        <span className="inline-block mt-1 text-[10px] text-stone-400 bg-stone-50 px-1.5 py-0.5 rounded">
                          {c.tipo_clave}
                        </span>
                      )}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* Articles */}
        <section id="articulos" className="mb-10">
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
        </section>

        {/* Normativa */}
        <section id="normativa" className="mb-10">
          <h2 className="mb-4 text-sm font-semibold text-stone-900">
            Normativa ({data.normativa.length})
          </h2>
          {data.normativa.length === 0 ? (
            <p className="text-sm text-stone-400">
              No hay normativa registrada para este modelo.
            </p>
          ) : (
            <ul className="divide-y divide-stone-200">
              {data.normativa.map((n) => (
                <li key={n.boe_id || n.titulo} className="py-3">
                  <div className="min-w-0">
                    {n.url_boe ? (
                      <a
                        href={n.url_boe}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-semibold text-sm text-blue-700 hover:text-blue-900 transition-colors"
                      >
                        {n.titulo}
                      </a>
                    ) : (
                      <span className="font-semibold text-sm text-stone-700">
                        {n.titulo}
                      </span>
                    )}
                    {n.fecha && (
                      <p className="text-xs text-stone-400 mt-0.5">{n.fecha}</p>
                    )}
                    {n.resumen && (
                      <p className="text-xs text-stone-500 mt-0.5">{n.resumen}</p>
                    )}
                    {n.boe_id && (
                      <span className="inline-block mt-1 text-[10px] font-mono text-stone-400 bg-stone-50 px-1.5 py-0.5 rounded">
                        {n.boe_id}
                      </span>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* Sidebar: Related doctrine */}
        {data.doctrina_relacionada.length > 0 && (
          <div className="rounded-md border border-stone-200 bg-white p-4">
            <h2 className="mb-3 text-sm font-semibold text-stone-900">
              Doctrina que lo menciona ({data.doctrina_relacionada.length})
            </h2>
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
          </div>
        )}
      </main>
    </div>
  );
}

function TabLink({ href, label }: { href: string; label: string }) {
  return (
    <a
      href={href}
      className="border-b-2 border-transparent py-2 text-stone-500 hover:border-stone-300 hover:text-stone-700 transition-colors"
    >
      {label}
    </a>
  );
}
