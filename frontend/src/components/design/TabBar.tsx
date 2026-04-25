"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";

import { TABS, type TabKey } from "@/lib/status";
import type { TabCounts } from "@/lib/api";

export function TabBar({ counts }: { counts: TabCounts }) {
  const pathname = usePathname();
  const search = useSearchParams();
  const activeTab = resolveActiveTab(pathname, search.get("tab"));

  return (
    <div className="tabbar">
      {TABS.map((tab) => {
        const href = tab.utility ? "/explore" : `/?tab=${tab.key}`;
        const count = counts[tab.key as keyof TabCounts] ?? 0;
        const isActive = activeTab !== null && tab.key === activeTab;
        return (
          <Link
            key={tab.key}
            href={href}
            className={`tab${isActive ? " active" : ""}${tab.utility ? " utility" : ""}`}
          >
            {tab.urgent && !isActive && <span className="urgent-dot" />}
            <span>{tab.label}</span>
            <span className="count">{count}</span>
          </Link>
        );
      })}
    </div>
  );
}

function resolveActiveTab(pathname: string, tabParam: string | null): TabKey | null {
  if (pathname.startsWith("/explore")) return "explore";
  // No tab is active when drilled into a creative — keeps the bar's underline
  // off so the user knows they're outside the cohort browser.
  if (pathname.startsWith("/creatives/") || pathname.startsWith("/debug/")) {
    return null;
  }
  const requested = tabParam as TabKey | null;
  if (requested && ["scale", "watch", "rescue", "cut"].includes(requested)) {
    return requested;
  }
  return "scale";
}
