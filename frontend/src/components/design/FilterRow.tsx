import Link from "next/link";
import { ChevronDown, Plus, X } from "lucide-react";

import type { TabKey } from "@/lib/status";

const TAB_LABEL: Record<TabKey, string> = {
  scale: "Scale",
  watch: "Watch",
  rescue: "Rescue",
  cut: "Cut",
  explore: "Explore",
};

// Demo filter row inspired by AppsFlyer's Creative Optimization view: each
// active filter is a removable chip; inactive dimensions sit as ghost
// dropdowns to suggest the filter surface even before they are wired.
export function FilterRow({
  tab,
  start,
  end,
  total,
}: {
  tab: TabKey;
  start?: string;
  end?: string;
  total: number;
}) {
  const dateLabel = formatRangeLabel(start, end);
  // Tab chip removes ?tab and resets to /
  const removeTabHref = "/";
  return (
    <div className="filter-row">
      <span className="filter-pill">
        <span className="filter-pill-key">Tab</span>
        <span className="filter-pill-val">{TAB_LABEL[tab]}</span>
        {tab !== "scale" ? (
          <Link href={removeTabHref} aria-label="Clear tab filter" className="filter-pill-x">
            <X size={11} strokeWidth={2} aria-hidden />
          </Link>
        ) : null}
      </span>
      <span className="filter-pill">
        <span className="filter-pill-key">Period</span>
        <span className="filter-pill-val">{dateLabel}</span>
      </span>
      <span className="filter-pill ghost">
        <span className="filter-pill-key">Vertical</span>
        <span className="filter-pill-val">Any</span>
        <ChevronDown size={11} strokeWidth={1.75} aria-hidden />
      </span>
      <span className="filter-pill ghost">
        <span className="filter-pill-key">Format</span>
        <span className="filter-pill-val">Any</span>
        <ChevronDown size={11} strokeWidth={1.75} aria-hidden />
      </span>
      <span className="filter-pill ghost">
        <span className="filter-pill-key">Country</span>
        <span className="filter-pill-val">All</span>
        <ChevronDown size={11} strokeWidth={1.75} aria-hidden />
      </span>
      <button type="button" className="filter-add" aria-label="Add filter">
        <Plus size={12} strokeWidth={2} aria-hidden />
        Add filter
      </button>
      <span className="filter-row-tail">
        <strong>{total}</strong> creatives
      </span>
    </div>
  );
}

function formatRangeLabel(start?: string, end?: string): string {
  if (!start && !end) return "Last 75 days";
  if (start && end) {
    return `${start} → ${end}`;
  }
  if (start) return `From ${start}`;
  if (end) return `Through ${end}`;
  return "All time";
}
