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
        const isActive = tab.key === activeTab;
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

function resolveActiveTab(pathname: string, tabParam: string | null): TabKey {
  if (pathname.startsWith("/explore")) return "explore";
  const requested = tabParam as TabKey | null;
  if (requested && ["scale", "watch", "rescue", "cut"].includes(requested)) {
    return requested;
  }
  return "scale";
}
