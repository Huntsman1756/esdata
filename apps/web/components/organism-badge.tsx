interface OrganismBadgeProps {
  organismo: "DGT" | "TEAC" | string;
}

export default function OrganismBadge({ organismo }: OrganismBadgeProps) {
  const cls = organismo === "DGT"
    ? "bg-blue-50 text-blue-700 border-blue-200"
    : organismo === "TEAC"
      ? "bg-violet-50 text-violet-700 border-violet-200"
      : "bg-stone-100 text-stone-700 border-stone-200";

  return (
    <span className={`inline-flex items-center rounded-md border px-2 py-0.5 text-[11px] font-bold uppercase tracking-wider shadow-sm ${cls}`}>
      {organismo}
    </span>
  );
}
