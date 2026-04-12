interface OrganismBadgeProps {
  organismo: "DGT" | "TEAC" | string;
}

export default function OrganismBadge({ organismo }: OrganismBadgeProps) {
  const cls = organismo === "DGT"
    ? "bg-blue-700 text-white"
    : organismo === "TEAC"
      ? "bg-violet-600 text-white"
      : "bg-stone-600 text-white";

  return (
    <span className={`inline-flex rounded-sm px-1.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${cls}`}>
      {organismo}
    </span>
  );
}
