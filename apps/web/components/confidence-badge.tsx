interface ConfidenceBadgeProps {
  confianza: number;
}

export default function ConfidenceBadge({ confianza }: ConfidenceBadgeProps) {
  if (confianza >= 1.0) {
    return (
      <span className="inline-flex items-center gap-1 text-xs font-medium text-green-700" title="Enlace de confianza máxima">
        <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
        </svg>
        Enlace de confianza máxima
      </span>
    );
  }
  if (confianza >= 0.85) {
    return (
      <span className="inline-flex items-center gap-1 text-xs font-medium text-amber-700" title="Enlace probable">
        Enlace probable
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-xs font-medium text-stone-500" title="Enlace por revisar">
      Enlace por revisar
    </span>
  );
}
