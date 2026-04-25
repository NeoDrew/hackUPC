"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

const DATASET_START = "2026-01-01";
const DATASET_END = "2026-03-16";

const PRESETS: Array<{ key: string; label: string; days: number | "all" }> = [
  { key: "7d", label: "Last 7 days", days: 7 },
  { key: "30d", label: "Last 30 days", days: 30 },
  { key: "75d", label: "Last 75 days", days: 75 },
  { key: "all", label: "All time", days: "all" },
];

function isoSubtractDays(end: string, days: number): string {
  const d = new Date(`${end}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() - (days - 1));
  return d.toISOString().slice(0, 10);
}

function summarise(start: string | null, end: string | null): string {
  if (!start && !end) return "Last 75 days";
  const s = start ?? DATASET_START;
  const e = end ?? DATASET_END;
  if (s === DATASET_START && e === DATASET_END) return "All time";
  for (const p of PRESETS) {
    if (p.days === "all") continue;
    if (s === isoSubtractDays(DATASET_END, p.days as number) && e === DATASET_END) {
      return p.label;
    }
  }
  return `${s} → ${e}`;
}

export function PeriodPicker() {
  const router = useRouter();
  const pathname = usePathname();
  const sp = useSearchParams();
  const startParam = sp.get("start");
  const endParam = sp.get("end");

  const [open, setOpen] = useState(false);
  const [customStart, setCustomStart] = useState(startParam ?? DATASET_START);
  const [customEnd, setCustomEnd] = useState(endParam ?? DATASET_END);
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    setCustomStart(startParam ?? DATASET_START);
    setCustomEnd(endParam ?? DATASET_END);
  }, [startParam, endParam]);

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

  function applyRange(start: string | null, end: string | null) {
    const next = new URLSearchParams(sp.toString());
    // Page-specific params (limit, sort, tab) should reset when the window
    // changes — the underlying band assignment changes, so a "tab=scale&limit=300"
    // from the previous window is meaningless.
    next.delete("limit");
    if (start) next.set("start", start);
    else next.delete("start");
    if (end) next.set("end", end);
    else next.delete("end");
    const qs = next.toString();
    router.push(`${pathname}${qs ? `?${qs}` : ""}`);
    setOpen(false);
  }

  function applyPreset(p: (typeof PRESETS)[number]) {
    if (p.days === "all") return applyRange(null, null);
    const start = isoSubtractDays(DATASET_END, p.days as number);
    applyRange(start, DATASET_END);
  }

  const summary = summarise(startParam, endParam);

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <button
        type="button"
        className={`filter-chip${open ? " active" : ""}`}
        onClick={() => setOpen((v) => !v)}
        style={{ cursor: "pointer" }}
      >
        <span className="muted">Period</span>
        <strong>{summary}</strong>
      </button>
      {open && (
        <div className="period-popover">
          <div className="period-popover-presets">
            {PRESETS.map((p) => (
              <button
                key={p.key}
                type="button"
                className="period-preset"
                onClick={() => applyPreset(p)}
              >
                {p.label}
              </button>
            ))}
          </div>
          <div className="period-popover-divider" />
          <div className="period-popover-custom">
            <span className="t-micro">Custom range</span>
            <div className="row gap-2 center">
              <input
                type="date"
                value={customStart}
                min={DATASET_START}
                max={DATASET_END}
                onChange={(e) => setCustomStart(e.target.value)}
                className="period-date"
              />
              <span className="muted">→</span>
              <input
                type="date"
                value={customEnd}
                min={DATASET_START}
                max={DATASET_END}
                onChange={(e) => setCustomEnd(e.target.value)}
                className="period-date"
              />
            </div>
            <button
              type="button"
              className="btn dense primary"
              onClick={() => applyRange(customStart, customEnd)}
            >
              Apply
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
