"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { ChevronDown, X } from "lucide-react";

/* Single horizontal filter bar for the Explore page. Filters group under
 * three semantic headers so 7 dropdowns in a row don't read as a wall:
 *
 *   Cohort   →  Vertical · Format
 *   Creative →  Theme · Hook
 *   Delivery →  Country · OS · Band
 *
 * Each pill opens a dropdown of options; selecting one updates the URL
 * (?vertical=… &format=… etc.) and the server component re-fetches with
 * the new filter set. "Reset" clears every filter at once.
 */

const VERTICALS = [
  "ecommerce",
  "entertainment",
  "fintech",
  "food_delivery",
  "gaming",
  "travel",
];
const FORMATS = ["banner", "interstitial", "native", "playable", "rewarded_video"];
const THEMES = [
  "celebrity",
  "combo",
  "competitive",
  "destination",
  "discount",
  "drama",
  "family",
  "fantasy",
  "feature-focus",
  "food-closeup",
  "gameplay",
  "minimalist",
  "product-focus",
  "reward",
  "testimonial",
];
const HOOKS = [
  "2-for-1",
  "before/after",
  "book now",
  "cashback",
  "challenge",
  "competition",
  "discover",
  "earn more",
  "escape",
  "exclusive",
  "fast",
  "free delivery",
  "free rewards",
  "free shipping",
  "last-minute deal",
  "late-night",
  "limited offer",
  "new collection",
  "new season",
  "power-up",
  "save smarter",
  "security",
  "trending",
  "watch now",
];
const COUNTRIES = ["BR", "CA", "DE", "ES", "FR", "IT", "JP", "MX", "UK", "US"];
const OSES = ["Android", "iOS", "Both"];
const BANDS = [
  { value: "scale", label: "Scale" },
  { value: "watch", label: "Watch" },
  { value: "rescue", label: "Rescue" },
  { value: "cut", label: "Cut" },
];

const FILTER_KEYS = [
  "vertical",
  "format",
  "theme",
  "hook_type",
  "country",
  "os",
  "band",
];

export function ExploreFilters() {
  const router = useRouter();
  const pathname = usePathname();
  const sp = useSearchParams();

  function setParam(key: string, value: string | null) {
    const next = new URLSearchParams(sp.toString());
    next.delete("limit"); // re-paginate from scratch on filter change
    if (value === null) next.delete(key);
    else next.set(key, value);
    const qs = next.toString();
    router.push(`${pathname}${qs ? `?${qs}` : ""}`);
  }

  function resetAll() {
    const next = new URLSearchParams(sp.toString());
    for (const k of FILTER_KEYS) next.delete(k);
    next.delete("limit");
    const qs = next.toString();
    router.push(`${pathname}${qs ? `?${qs}` : ""}`);
  }

  const anyActive = FILTER_KEYS.some((k) => !!sp.get(k));

  return (
    <div className="explore-filters">
      <FilterGroup label="Cohort">
        <FilterDropdown
          keyLabel="Vertical"
          paramKey="vertical"
          emptyLabel="Any"
          options={VERTICALS.map((v) => ({ value: v, label: v }))}
          onChange={(v) => setParam("vertical", v)}
        />
        <FilterDropdown
          keyLabel="Format"
          paramKey="format"
          emptyLabel="Any"
          options={FORMATS.map((v) => ({
            value: v,
            label: v.replace("_", " "),
          }))}
          onChange={(v) => setParam("format", v)}
        />
      </FilterGroup>

      <FilterGroup label="Creative">
        <FilterDropdown
          keyLabel="Theme"
          paramKey="theme"
          emptyLabel="Any"
          options={THEMES.map((v) => ({ value: v, label: v }))}
          onChange={(v) => setParam("theme", v)}
        />
        <FilterDropdown
          keyLabel="Hook"
          paramKey="hook_type"
          emptyLabel="Any"
          options={HOOKS.map((v) => ({ value: v, label: v }))}
          onChange={(v) => setParam("hook_type", v)}
        />
      </FilterGroup>

      <FilterGroup label="Delivery">
        <FilterDropdown
          keyLabel="Country"
          paramKey="country"
          emptyLabel="All"
          options={COUNTRIES.map((v) => ({ value: v, label: v }))}
          onChange={(v) => setParam("country", v)}
        />
        <FilterDropdown
          keyLabel="OS"
          paramKey="os"
          emptyLabel="Any"
          options={OSES.map((v) => ({ value: v, label: v }))}
          onChange={(v) => setParam("os", v)}
        />
        <FilterDropdown
          keyLabel="Band"
          paramKey="band"
          emptyLabel="All"
          options={BANDS}
          onChange={(v) => setParam("band", v)}
        />
      </FilterGroup>

      {anyActive ? (
        <button type="button" className="explore-filters-reset" onClick={resetAll}>
          Reset
        </button>
      ) : null}
    </div>
  );
}

function FilterGroup({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="explore-filter-group">
      <span className="explore-filter-group-label">{label}</span>
      <div className="explore-filter-group-pills">{children}</div>
    </div>
  );
}

function FilterDropdown({
  keyLabel,
  paramKey,
  emptyLabel,
  options,
  onChange,
}: {
  keyLabel: string;
  paramKey: string;
  emptyLabel: string;
  options: Array<{ value: string; label: string }>;
  onChange: (value: string | null) => void;
}) {
  const sp = useSearchParams();
  const currentValue = sp.get(paramKey) ?? undefined;
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
        {isActive ? (
          <span
            role="button"
            tabIndex={-1}
            aria-label={`Clear ${keyLabel}`}
            className="filter-pill-x"
            onClick={(e) => {
              e.stopPropagation();
              onChange(null);
            }}
          >
            <X size={11} strokeWidth={2} aria-hidden />
          </span>
        ) : (
          <ChevronDown size={11} strokeWidth={1.75} aria-hidden />
        )}
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
