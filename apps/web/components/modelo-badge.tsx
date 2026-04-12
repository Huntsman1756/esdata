import Link from "next/link";
import { FileSpreadsheet, ArrowRight } from "lucide-react";

interface ModeloBadgeProps {
  codigo: string;
  nombre: string;
  periodo?: string | null;
  href?: string;
}

export default function ModeloBadge({
  codigo,
  nombre,
  periodo,
  href,
}: ModeloBadgeProps) {
  const content = (
    <span className="flex items-center gap-1.5 text-sm">
      <FileSpreadsheet aria-hidden="true" className="h-3.5 w-3.5 text-stone-400" />
      <span className="font-mono font-medium text-stone-700 group-hover:text-stone-900 transition-colors">
        Modelo {codigo}
      </span>
      {periodo && (
        <span className="text-[11px] font-medium text-stone-400 bg-stone-100 px-1.5 py-0.5 rounded ml-1">
          {periodo}
        </span>
      )}
    </span>
  );

  if (href) {
    return (
      <Link
        href={href}
        className="group flex w-fit items-center gap-1 rounded-md border border-transparent hover:border-stone-200 hover:bg-white px-2 py-1.5 -ml-2 transition-colors"
        title={nombre}
      >
        {content}
        <ArrowRight aria-hidden="true" className="h-3.5 w-3.5 text-stone-300 opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 group-hover:text-stone-500 transition-transform" />
      </Link>
    );
  }

  return <div className="flex items-center gap-1 px-2 py-1.5 -ml-2">{content}</div>;
}
