"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { ChevronDown, X } from "lucide-react";

import type { TabKey } from "@/lib/status";

const TAB_LABEL: Record<TabKey, string> = {
  scale: "Scale",
  watch: "Watch",
  rescue: "Rescue",
  cut: "Cut",
  explore: "Explore",
};

const VERTICALS = [
  "ecommerce",
  "entertainment",
  "fintech",
  "food_delivery",
  "gaming",
  "travel",
];
const FORMATS = ["banner", "interstitial", "native", "playable", "rewarded_video"];

/** Active-filter chip strip for the cockpit + explore tables. Vertical
 * and Format are wired to URL params (?vertical=…&format=…) — clicking
 * a pill opens a dropdown of options; selecting one routes with the new
 * param. Tab and Period are read-outs of state managed elsewhere
 * (TabBar at page top and PeriodPicker in TopBar respectively); their
 * chips show the current value but are clearable in-place. */
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
  const router = useRouter();
  const pathname = usePathname();
  const sp = useSearchParams();
  const vertical = sp.get("vertical") ?? undefined;
  const format = sp.get("format") ?? undefined;
  const dateLabel = formatRangeLabel(start, end);

  function setParam(key: string, value: string | null) {
    const next = new URLSearchParams(sp.toString());
    // Reset paging/sorting when a filter changes — those are downstream.
    next.delete("limit");
    if (value === null) next.delete(key);
    else next.set(key, value);
    const qs = next.toString();
    router.push(`${pathname}${qs ? `?${qs}` : ""}`);
  }

  function clearTab() {
    setParam("tab", null);
  }
  function clearPeriod() {
    const next = new URLSearchParams(sp.toString());
    next.delete("limit");
    next.delete("start");
    next.delete("end");
    const qs = next.toString();
    router.push(`${pathname}${qs ? `?${qs}` : ""}`);
  }

  return (
    <div className="filter-row">
      <span className="filter-pill">
        <span className="filter-pill-key">Tab</span>
        <span className="filter-pill-val">{TAB_LABEL[tab]}</span>
        {tab !== "scale" ? (
          <button
            type="button"
            onClick={clearTab}
            aria-label="Clear tab filter"
            className="filter-pill-x"
          >
            <X size={11} strokeWidth={2} aria-hidden />
          </button>
        ) : null}
      </span>

      <span className={`filter-pill${start || end ? "" : " ghost"}`}>
        <span className="filter-pill-key">Period</span>
        <span className="filter-pill-val">{dateLabel}</span>
        {start || end ? (
          <button
            type="button"
            onClick={clearPeriod}
            aria-label="Clear period filter"
            className="filter-pill-x"
          >
            <X size={11} strokeWidth={2} aria-hidden />
          </button>
        ) : null}
      </span>

      <FilterDropdown
        keyLabel="Vertical"
        currentValue={vertical}
        emptyLabel="Any"
        options={VERTICALS.map((v) => ({ value: v, label: v }))}
        onChange={(v) => setParam("vertical", v)}
      />
      <FilterDropdown
        keyLabel="Format"
        currentValue={format}
        emptyLabel="Any"
        options={FORMATS.map((v) => ({
          value: v,
          label: v.replace("_", " "),
        }))}
        onChange={(v) => setParam("format", v)}
      />

      <span className="filter-row-tail">
        <strong>{total}</strong> creatives
      </span>
    </div>
  );
}

function FilterDropdown({
  keyLabel,
  currentValue,
  emptyLabel,
  options,
  onChange,
}: {
  keyLabel: string;
  currentValue?: string;
  emptyLabel: string;
  options: Array<{ value: string; label: string }>;
  onChange: (value: string | null) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) return;
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const activeLabel =
    options.find((o) => o.value === currentValue)?.label ?? emptyLabel;
  const isActive = !!currentValue;

  return (
    <div ref={ref} style={{ position: "relative", display: "inline-flex" }}>
      <button
        type="button"
        className={`filter-pill${isActive ? "" : " ghost"}`}
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className="filter-pill-key">{keyLabel}</span>
        <span className="filter-pill-val">{activeLabel}</span>
        <ChevronDown size={11} strokeWidth={1.75} aria-hidden />
      </button>
      {open ? (
        <div className="filter-dropdown" role="menu">
          <button
            type="button"
            className={`filter-dropdown-item${!currentValue ? " active" : ""}`}
            onClick={() => {
              onChange(null);
              setOpen(false);
            }}
          >
            {emptyLabel}
          </button>
          {options.map((o) => (
            <button
              key={o.value}
              type="button"
              className={`filter-dropdown-item${currentValue === o.value ? " active" : ""}`}
              onClick={() => {
                onChange(o.value);
                setOpen(false);
              }}
            >
              {o.label}
            </button>
          ))}
        </div>
      ) : null}
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
