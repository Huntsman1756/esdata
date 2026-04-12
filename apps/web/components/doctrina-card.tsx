import Link from "next/link";
import OrganismBadge from "./organism-badge";
import ConfidenceBadge from "./confidence-badge";
import { ArrowRight, BookOpen } from "lucide-react";

interface DoctrinaCardProps {
  referencia: string;
  organismo: string;
  tipoDocumento: string;
  fecha?: string | null;
  titulo: string;
  fragmento: string;
  articulos?: Array<{
    norma: string;
    numero: string;
    confianza: number;
  }>;
  href: string;
}

export default function DoctrinaCard({
  referencia,
  organismo,
  tipoDocumento,
  fecha,
  titulo,
  fragmento,
  articulos,
  href,
}: DoctrinaCardProps) {
  const fechaStr = fecha
    ? new Date(fecha).toLocaleDateString("es-ES", {
        year: "numeric",
        month: "short",
        day: "numeric",
      })
    : null;

  return (
    <article className="group relative rounded-xl border border-stone-200 bg-white p-5 shadow-sm transition-all hover:border-stone-300 hover:shadow-md mb-4 last:mb-0">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="mb-3 flex flex-wrap items-center gap-2 text-xs">
            <OrganismBadge organismo={organismo} />
            {fechaStr && <span className="text-stone-500 font-medium">{fechaStr}</span>}
            {tipoDocumento && (
              <span className="rounded-full bg-stone-100 px-2.5 py-0.5 text-stone-600 font-medium">{tipoDocumento}</span>
            )}
          </div>
          <h3 className="mb-2 text-base font-bold text-stone-900 group-hover:text-blue-700 transition-colors">
            <Link href={href} className="before:absolute before:inset-0">
              {titulo}
            </Link>
          </h3>
          <div className="rounded-lg bg-stone-50 p-4 border border-stone-100 mb-4">
            <p
              className="font-serif text-sm leading-relaxed text-stone-700"
              dangerouslySetInnerHTML={{ __html: fragmento }}
            />
          </div>
          {articulos && articulos.length > 0 && (
            <div className="flex flex-wrap gap-2 items-center">
              <span className="text-xs font-semibold text-stone-400 uppercase tracking-wider mr-1 flex items-center gap-1">
                <BookOpen aria-hidden="true" className="h-3 w-3" /> Aplica a:
              </span>
              {articulos.map((a) => (
                <div key={a.norma + a.numero} className="flex items-center gap-1.5 text-xs bg-white border border-stone-200 rounded-md px-2 py-1 shadow-sm relative z-10">
                  <Link
                    href={`/articulo/${a.norma}/${a.numero}`}
                    className="font-mono font-medium text-stone-700 hover:text-stone-900 hover:underline transition-colors"
                  >
                    {a.norma} art. {a.numero}
                  </Link>
                  <ConfidenceBadge confianza={a.confianza} />
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
      <div className="mt-4 flex items-center text-sm font-semibold text-stone-500 transition-colors group-hover:text-blue-700">
        Ver criterio completo <ArrowRight aria-hidden="true" className="ml-1 h-4 w-4 transition-transform group-hover:translate-x-1" />
      </div>
    </article>
  );
}
