import Link from "next/link";

const TABS: { key: "legislacion" | "dgt" | "teac"; label: string }[] = [
  { key: "legislacion", label: "Legislaci\u00f3n" },
  { key: "dgt", label: "DGT" },
  { key: "teac", label: "TEAC" },
];

interface TabsProps {
  active: "legislacion" | "dgt" | "teac";
  href: (tab: string) => string;
}

export default function Tabs({ active, href }: TabsProps) {
  return (
    <nav className="flex gap-1" role="tablist">
      {TABS.map((tab) => {
        const isActive = tab.key === active;
        return (
          <Link
            key={tab.key}
            href={href(tab.key)}
            role="tab"
            aria-selected={isActive}
            className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors
              ${isActive
                ? "bg-stone-900 text-white"
                : "text-stone-600 hover:bg-stone-200 hover:text-stone-900"
              }`}
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
