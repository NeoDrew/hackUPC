"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";

import { TABS, type TabKey } from "@/lib/status";
import { type TabCounts } from "@/lib/api";

/**
 * Tabbed band switcher. Lives on the campaign detail page where bands
 * (scale/watch/rescue/cut) make sense; not rendered on the advertiser
 * overview at /. ``basePath`` defaults to "/" for back-compat but the
 * campaign page passes "/campaigns/{id}".
 */
export function TabBar({
  counts,
  basePath = "/",
}: {
  counts: TabCounts;
  basePath?: string;
}) {
  const pathname = usePathname();
  const search = useSearchParams();
  const activeTab = resolveActiveTab(pathname, search.get("tab"), basePath);

  const start = search.get("start");
  const end = search.get("end");
  const rangeQs = new URLSearchParams();
  if (start) rangeQs.set("start", start);
  if (end) rangeQs.set("end", end);
  const rangeStr = rangeQs.toString();

  const actionCount = (counts.rescue ?? 0) + (counts.cut ?? 0);
  const actionHref = rangeStr ? `${basePath}?${rangeStr}` : basePath;
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
        const baseHref = tab.utility
          ? "/explore"
          : `${basePath}?tab=${tab.key}`;
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

function resolveActiveTab(
  pathname: string,
  tabParam: string | null,
  basePath: string,
): ActiveTab {
  if (pathname.startsWith("/explore")) return "explore";
  if (pathname.startsWith("/creatives/") || pathname.startsWith("/debug/")) {
    return null;
  }
  if (!pathname.startsWith(basePath)) return null;
  const requested = tabParam as TabKey | null;
  if (requested && ["scale", "watch", "rescue", "cut"].includes(requested)) {
    return requested;
  }
  return "action";
}
