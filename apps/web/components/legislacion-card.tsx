import Link from "next/link";
import { ArrowRight, Calendar, Scale } from "lucide-react";

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

  return (
    <article className="group relative rounded-xl border border-stone-200 bg-white p-5 shadow-sm transition-all hover:border-stone-300 hover:shadow-md mb-4 last:mb-0">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="mb-3 flex flex-wrap items-center gap-2 text-xs">
            <span className="inline-flex items-center gap-1.5 rounded-md bg-stone-900 px-2.5 py-1 font-mono font-medium text-white shadow-sm">
              <Scale aria-hidden="true" className="h-3 w-3 opacity-70" />
              {norma} art. {numero}
            </span>
            {vigencia && (
              <span className="inline-flex items-center gap-1.5 rounded-md bg-stone-100 border border-stone-200 px-2 py-1 text-stone-600 font-medium">
                <Calendar aria-hidden="true" className="h-3 w-3" />
                {vigencia}
              </span>
            )}
          </div>
          <div className="rounded-lg bg-stone-50 p-4 border border-stone-100">
            <p
              className="font-serif text-sm leading-relaxed text-stone-800"
              dangerouslySetInnerHTML={{ __html: fragmento }}
            />
          </div>
        </div>
      </div>
      <div className="mt-4 flex items-center text-sm font-semibold text-stone-500 transition-colors group-hover:text-blue-700">
        <Link href={href} className="before:absolute before:inset-0 flex items-center">
          Ver art\u00edculo completo <ArrowRight aria-hidden="true" className="ml-1 h-4 w-4 transition-transform group-hover:translate-x-1" />
        </Link>
      </div>
    </article>
  );
}
