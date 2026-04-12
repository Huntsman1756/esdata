import Link from "next/link";
import SearchBox from "@/components/search-box";
import Coverage from "@/components/coverage";
import OperationalStatus from "@/components/operational-status";

export default function Home() {
  return (
    <div className="mx-auto max-w-5xl px-6 py-16">
      {/* Brand */}
      <h1 className="mb-8 text-2xl font-semibold tracking-tight text-stone-900">
        <Link href="/" className="hover:underline">esdata</Link>
      </h1>

      {/* Search */}
      <SearchBox />

      {/* Coverage + Status */}
      <Coverage />
      <OperationalStatus />
    </div>
  );
}
