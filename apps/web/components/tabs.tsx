import Link from "next/link";
import { Scale, FileText, Landmark } from "lucide-react";

const TABS: { key: "legislacion" | "dgt" | "teac"; label: string; icon: React.ElementType }[] = [
  { key: "legislacion", label: "Legislaci\u00f3n", icon: Scale },
  { key: "dgt", label: "DGT", icon: FileText },
  { key: "teac", label: "TEAC", icon: Landmark },
];

interface TabsProps {
  active: "legislacion" | "dgt" | "teac";
  href: (tab: string) => string;
}

export default function Tabs({ active, href }: TabsProps) {
  return (
    <nav className="flex flex-wrap gap-2 mb-6" role="tablist">
      {TABS.map((tab) => {
        const isActive = tab.key === active;
        const Icon = tab.icon;
        return (
          <Link
            key={tab.key}
            href={href(tab.key)}
            role="tab"
            aria-selected={isActive}
            className={`flex items-center gap-1.5 rounded-full px-4 py-2 text-sm font-medium transition-colors
              ${isActive
                ? "bg-stone-900 text-white shadow-md ring-1 ring-stone-900"
                : "bg-white border border-stone-200 text-stone-600 hover:border-stone-300 hover:bg-stone-50 hover:text-stone-900 shadow-sm"
              }`}
          >
            <Icon aria-hidden="true" className="h-4 w-4" />
            {tab.label === "Legislaci\u00f3n" ? tab.label : tab.label.toUpperCase()}
          </Link>
        );
      })}
    </nav>
  );
}
