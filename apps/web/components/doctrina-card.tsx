import Link from "next/link";
import OrganismBadge from "./organism-badge";
import ConfidenceBadge from "./confidence-badge";

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
    <article className="border-b border-stone-200 py-5 first:pt-4 last:border-b-0">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="mb-2 flex flex-wrap items-center gap-2 text-xs">
            <OrganismBadge organismo={organismo} />
            {fechaStr && <span className="text-stone-400">{fechaStr}</span>}
            {tipoDocumento && (
              <span className="text-stone-400">{tipoDocumento}</span>
            )}
          </div>
          <h3 className="mb-1 text-sm font-semibold text-stone-900">
            {titulo}
          </h3>
          <p
            className="font-serif text-sm leading-relaxed text-stone-700"
            dangerouslySetInnerHTML={{ __html: fragmento }}
          />
          {articulos && articulos.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-3">
              {articulos.map((a) => (
                <div key={a.norma + a.numero} className="flex items-center gap-1.5 text-xs">
                  <Link
                    href={`/articulo/${a.norma}/${a.numero}`}
                    className="font-mono font-medium text-stone-600 hover:text-stone-900 transition-colors"
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
      <div className="mt-2">
        <Link
          href={href}
          className="text-xs font-medium text-stone-500 hover:text-stone-900 transition-colors"
        >
          Ver criterio completo →
        </Link>
      </div>
    </article>
  );
}
