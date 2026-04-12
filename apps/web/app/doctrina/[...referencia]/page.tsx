import { notFound } from "next/navigation";
import Link from "next/link";
import Header from "@/components/header";
import OrganismBadge from "@/components/organism-badge";
import ConfidenceBadge from "@/components/confidence-badge";
import { getDoctrina } from "@/lib/api";
import { formatDocumentType, formatLinkMethod } from "@/lib/labels";

export default async function DoctrinaPage({
  params,
  searchParams,
}: {
  params: Promise<{ referencia: string[] }>;
  searchParams: Promise<{ q?: string; tab?: string }>;
}) {
  const { referencia } = await params;
  const sParams = await searchParams;
  const q = sParams.q || "";
  const tab = sParams.tab || "dgt";

  const refPath = referencia.join("/");

  let data: Awaited<ReturnType<typeof getDoctrina>> | null = null;
  try {
    data = await getDoctrina(refPath);
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
          <OrganismBadge organismo={data.organismo_emisor} />
          <span className="font-mono text-sm text-stone-500">
            {data.referencia}
          </span>
          <span className="text-sm text-stone-300">·</span>
          <span className="text-sm text-stone-400">
            {formatDocumentType(data.tipo_documento)}
          </span>
        </div>

        <h1 className="mb-8 font-serif text-xl leading-relaxed text-stone-900">
          {data.texto.split("\n").slice(0, 1).join("\n")}
        </h1>

        {/* Two-column layout */}
        <div className="grid gap-8 md:grid-cols-3">
          {/* Main text */}
          <div className="md:col-span-2">
            <div className="font-serif text-sm leading-relaxed whitespace-pre-line text-stone-800">
              {data.texto}
            </div>
          </div>

          {/* Sidebar: linked articles */}
          <aside className="shrink-0">
            <div className="rounded-md border border-stone-200 bg-white p-4">
              <h2 className="mb-3 text-sm font-semibold text-stone-900">
                Artículos vinculados
              </h2>
              {data.articulos_relacionados.length === 0 ? (
                <p className="text-xs text-stone-400">
                  Sin artículos vinculados.
                </p>
              ) : (
                <ul className="space-y-3">
                  {data.articulos_relacionados.map((a, i) => (
                    <li key={i} className="flex items-start justify-between gap-2">
                      <div>
                        <Link
                          href={`/articulo/${a.norma}/${a.numero}`}
                          className="font-mono text-sm font-medium text-stone-700 hover:text-stone-900 transition-colors"
                        >
                          {a.norma} art. {a.numero}
                        </Link>
                        <p className="text-[11px] text-stone-400">
                          {formatLinkMethod(a.metodo_enlace)}
                        </p>
                      </div>
                      <ConfidenceBadge confianza={a.confianza_enlace} />
                    </li>
                  ))}
                </ul>
              )}

              {/* Confidence message */}
              {data.articulos_relacionados.length > 0 && (
                <div className="mt-4 border-t border-stone-100 pt-3">
                  {data.articulos_relacionados.some((a) => a.confianza_enlace >= 1.0) ? (
                    <p className="text-xs text-green-700">
                      Enlace de confianza máxima
                    </p>
                  ) : data.articulos_relacionados.some((a) => a.confianza_enlace >= 0.85) ? (
                    <p className="text-xs text-amber-700">
                      Enlace probable
                    </p>
                  ) : (
                    <p className="text-xs text-stone-500">
                      Enlace por revisar
                    </p>
                  )}
                </div>
              )}
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}
