import Link from "next/link";

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
    <span className="text-sm">
      <span className="font-mono font-medium text-stone-700 hover:text-stone-900 transition-colors">
        Modelo {codigo}
      </span>
      {periodo && (
        <span className="text-[11px] text-stone-400 ml-1">
          ({periodo})
        </span>
      )}
    </span>
  );

  if (href) {
    return (
      <Link
        href={href}
        className="flex items-center gap-1 group"
        title={nombre}
      >
        {content}
        <span className="text-stone-300 group-hover:text-stone-500 transition-colors">→</span>
      </Link>
    );
  }

  return <div className="flex items-center gap-1">{content}</div>;
}
