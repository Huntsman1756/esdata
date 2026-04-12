import { Check, ShieldAlert, Shield } from "lucide-react";

interface ConfidenceBadgeProps {
  confianza: number;
}

export default function ConfidenceBadge({ confianza }: ConfidenceBadgeProps) {
  if (confianza >= 1.0) {
    return (
      <span className="inline-flex items-center gap-1 text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded text-xs font-medium border border-emerald-100" title="Enlace de confianza máxima">
        <Check aria-hidden="true" className="h-3 w-3" strokeWidth={3} />
        Verificado
      </span>
    );
  }
  if (confianza >= 0.85) {
    return (
      <span className="inline-flex items-center gap-1 text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded text-xs font-medium border border-amber-100" title="Enlace probable">
        <Shield aria-hidden="true" className="h-3 w-3" strokeWidth={2.5} />
        Probable ({Math.round(confianza * 100)}%)
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-stone-500 bg-stone-100 px-1.5 py-0.5 rounded text-xs font-medium border border-stone-200" title="Enlace por revisar">
      <ShieldAlert aria-hidden="true" className="h-3 w-3" strokeWidth={2.5} />
      Revisar ({Math.round(confianza * 100)}%)
    </span>
  );
}
