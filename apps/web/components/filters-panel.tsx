interface FiltersPanelProps {
  children: React.ReactNode;
}

export function FiltersPanel({ children }: FiltersPanelProps) {
  return (
    <aside className="shrink-0 w-56">
      <div className="sticky top-4 space-y-4">
        {children}
      </div>
    </aside>
  );
}

interface FilterGroupProps {
  label: string;
  children: React.ReactNode;
}

export function FilterGroup({ label, children }: FilterGroupProps) {
  return (
    <div>
      <p className="mb-2 text-xs font-semibold text-stone-500 uppercase tracking-wide">
        {label}
      </p>
      {children}
    </div>
  );
}
