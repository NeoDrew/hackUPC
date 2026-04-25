"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { TABS, type TabKey } from "@/lib/status";
import { api, type TabCounts } from "@/lib/api";

export function TabBar({ counts: initialCounts }: { counts: TabCounts }) {
  const pathname = usePathname();
  const search = useSearchParams();
  const activeTab = resolveActiveTab(pathname, search.get("tab"));

  const start = search.get("start");
  const end = search.get("end");
  const [counts, setCounts] = useState<TabCounts>(initialCounts);

  useEffect(() => {
    // Layout-rendered initialCounts are lifetime. When a window is set,
    // refetch so the badges reflect the windowed band distribution.
    if (!start && !end) {
      setCounts(initialCounts);
      return;
    }
    let cancelled = false;
    api
      .tabCounts({ start: start ?? undefined, end: end ?? undefined })
      .then((c) => {
        if (!cancelled) setCounts(c);
      })
      .catch(() => {
        // Network blip — keep the prior counts rather than zeroing the badges.
      });
    return () => {
      cancelled = true;
    };
  }, [start, end, initialCounts]);

  const rangeQs = new URLSearchParams();
  if (start) rangeQs.set("start", start);
  if (end) rangeQs.set("end", end);
  const rangeStr = rangeQs.toString();

  const actionCount = (counts.rescue ?? 0) + (counts.cut ?? 0);
  const actionHref = rangeStr ? `/?${rangeStr}` : "/";
  const isActionActive = activeTab === "action";

  return (
    <div className="tabbar">
      <Link
        href={actionHref}
        className={`tab${isActionActive ? " active" : ""}`}
      >
        <span>Action</span>
        <span className="count">{actionCount}</span>
      </Link>
      {TABS.map((tab) => {
        const baseHref = tab.utility ? "/explore" : `/?tab=${tab.key}`;
        const href = rangeStr
          ? `${baseHref}${baseHref.includes("?") ? "&" : "?"}${rangeStr}`
          : baseHref;
        const count = counts[tab.key as keyof TabCounts] ?? 0;
        const isActive = activeTab !== null && tab.key === activeTab;
        return (
          <Link
            key={tab.key}
            href={href}
            className={`tab${isActive ? " active" : ""}${tab.utility ? " utility" : ""}`}
          >
            <span>{tab.label}</span>
            <span className="count">{count}</span>
          </Link>
        );
      })}
    </div>
  );
}

type ActiveTab = TabKey | "action" | null;

function resolveActiveTab(pathname: string, tabParam: string | null): ActiveTab {
  if (pathname.startsWith("/explore")) return "explore";
  // No tab is active when drilled into a creative; keeps the bar's underline
  // off so the user knows they're outside the cohort browser.
  if (pathname.startsWith("/creatives/") || pathname.startsWith("/debug/")) {
    return null;
  }
  const requested = tabParam as TabKey | null;
  if (requested && ["scale", "watch", "rescue", "cut"].includes(requested)) {
    return requested;
  }
  // "/" without a tab param → the Action page is the new default landing.
  return "action";
}
