import Link from "next/link";

import type { CreativeRow } from "@/lib/api";
import { PhoneCard } from "./PhoneCard";

const TAB_OPTIONS = [
  { value: "all", label: "All" },
  { value: "scale", label: "Scale" },
  { value: "watch", label: "Watch" },
  { value: "rescue", label: "Rescue" },
  { value: "cut", label: "Cut" },
];

export function PhoneFeed({
  rows,
  activeTab,
  total,
}: {
  rows: CreativeRow[];
  activeTab: string;
  total: number;
}) {
  return (
    <div className="phone-shell">
      <header className="phone-header">
        <div className="phone-header-mark">
          <span className="mark">S</span>
          <span>Smadex Twin Copilot</span>
        </div>
        <p className="phone-header-sub">
          Swipe through {rows.length} of {total} creatives
        </p>
        <nav className="phone-tabs">
          {TAB_OPTIONS.map((opt) => (
            <Link
              key={opt.value}
              href={opt.value === "all" ? "/m" : `/m?tab=${opt.value}`}
              className={`phone-tab${activeTab === opt.value ? " active" : ""}`}
            >
              {opt.label}
            </Link>
          ))}
        </nav>
      </header>

      <main className="phone-feed">
        {rows.length === 0 ? (
          <div className="phone-empty">No creatives in this view.</div>
        ) : (
          rows.map((row) => <PhoneCard key={row.creative_id} row={row} />)
        )}
      </main>
    </div>
  );
}
