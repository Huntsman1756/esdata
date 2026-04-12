import Link from "next/link";

interface ResultCardProps {
  norma: string;
  numero: string;
  titulo?: string;
  fragmento: string;
  vigenteDesde?: string | null;
  vigenteHasta?: string | null;
  rank?: number;
  confianzaNivel: number;
  href: string;
}

export default function ResultCard({
  norma,
  numero,
  fragmento,
  vigenteDesde,
  vigenteHasta,
  confianzaNivel,
  href,
}: ResultCardProps) {
  const vigencia = vigenteHasta
    ? `Hasta ${vigenteHasta}`
    : vigenteDesde
      ? `Desde ${vigenteDesde}`
      : null;

  const confColor = confianzaNivel >= 1.0
    ? "text-green-700"
    : confianzaNivel >= 0.85
      ? "text-amber-700"
      : "text-stone-500";

  return (
    <article className="border-b border-stone-200 py-5 first:pt-4 last:border-b-0">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="mb-1 flex flex-wrap items-center gap-2 text-xs">
            <span className="font-mono font-medium text-stone-700">
              {norma} art. {numero}
            </span>
            {vigencia && (
              <span className="text-stone-400">{vigencia}</span>
            )}
            <span className={confColor}>
              {confianzaNivel.toFixed(2)}
            </span>
          </div>
          <p
            className="font-serif text-sm leading-relaxed text-stone-800"
            dangerouslySetInnerHTML={{ __html: fragmento }}
          />
        </div>
      </div>
      <div className="mt-2">
        <Link
          href={href}
          className="text-xs font-medium text-stone-500 hover:text-stone-900 transition-colors"
        >
          Ver art\u00edculo completo \u2192
        </Link>
      </div>
    </article>
  );
}
