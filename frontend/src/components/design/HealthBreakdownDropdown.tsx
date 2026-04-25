"use client";

import { useState } from "react";

import type { HealthBreakdown } from "@/lib/api";

/** Five surfaced components. We deliberately skip B (Reliability) — the
 * dataset has dense daily rows for every creative, so B is ~1.0 across
 * the portfolio and contributes no decision signal. The "How is this
 * calculated?" panel still lists it. */
type ChipKey = "S" | "C" | "T" | "R" | "E";

interface ChipDef {
  key: ChipKey;
  label: string;
  short: string; // displayed in the chip
  what: string; // plain-English explanation in the toggle
  weak: string; // narrative phrasing when this is the weakest component
}

const CHIPS: readonly ChipDef[] = [
  {
    key: "S",
    label: "Strength",
    short: "Strength",
    what: "How well it converts on its KPI goal, smoothed against its cohort.",
    weak: "raw conversion power is weak — even with healthy traffic it isn't earning enough returns",
  },
  {
    key: "C",
    label: "Confidence",
    short: "Confidence",
    what: "How sure we are in the score — narrows as more impressions and clicks come in.",
    weak: "we don't have enough data yet to be confident in the score",
  },
  {
    key: "T",
    label: "Trend",
    short: "Trend",
    what: "Whether daily performance is improving or fading over the recent window.",
    weak: "performance is fading day-over-day — it's burning out faster than peers",
  },
  {
    key: "R",
    label: "Cohort rank",
    short: "Cohort",
    what: "Where it ranks against creatives in the same vertical, format, country, and OS.",
    weak: "it's losing to its peers in the same vertical and format",
  },
  {
    key: "E",
    label: "Efficiency",
    short: "Efficiency",
    what: "Return per dollar spent — high ROAS or low cost-per-acquisition.",
    weak: "spend isn't converting into return — every dollar is buying less than peers",
  },
] as const;

const RELIABILITY_DESC =
  "A small bonus for creatives with enough data to be statistically meaningful. Not shown as a chip because every creative in this dataset already has plenty of data.";

const TREND_GATE_DAYS = 7;

export interface NarrativeInput {
  health: number;
  components: { S: number; C: number; T: number; R: number; E: number };
  daysActive?: number;
  trendGated: boolean;
}

/** Pure function — easy to test, no React deps. Returns the 1–2 sentence
 * narrative shown below the chips. Leads with the most actionable
 * signal (lowest-scoring component), skips trend when gated, and ends
 * with a fixed action verdict tied to health.
 */
export function generateNarrative(input: NarrativeInput): string {
  const { health, components, daysActive, trendGated } = input;

  const candidates = CHIPS.filter((c) => !(trendGated && c.key === "T"));
  const sorted = [...candidates].sort(
    (a, b) => components[a.key] - components[b.key],
  );
  const weakest = sorted[0];

  let lead: string;
  if (trendGated && daysActive !== undefined) {
    lead = `Active for ${daysActive} day${daysActive === 1 ? "" : "s"} — too early to assess trend, but ${weakest.weak}.`;
  } else if (weakest && components[weakest.key] < 0.5) {
    const cap = weakest.weak.charAt(0).toUpperCase() + weakest.weak.slice(1);
    lead = `${cap}.`;
  } else {
    lead = "All components are within healthy range — no single weakness stands out.";
  }

  let verdict: string;
  if (health >= 70) verdict = "Safe to scale.";
  else if (health >= 45) verdict = "Monitor closely.";
  else verdict = "Consider pausing or refreshing this creative.";

  return `${lead} ${verdict}`;
}

function tone(value: number): "good" | "warn" | "bad" {
  if (value >= 0.7) return "good";
  if (value >= 0.4) return "warn";
  return "bad";
}

export function HealthBreakdownDropdown({
  breakdown,
  daysActive,
  alwaysOpen = false,
}: {
  breakdown?: HealthBreakdown | null;
  daysActive?: number;
  alwaysOpen?: boolean;
}) {
  const [showHow, setShowHow] = useState(false);

  if (!breakdown?.components) return null;

  const c = breakdown.components;
  const components = {
    S: c.S ?? 0,
    C: c.C ?? 0,
    T: c.T ?? 0,
    R: c.R ?? 0,
    E: c.E ?? 0,
  };
  const trendGated =
    daysActive !== undefined && daysActive < TREND_GATE_DAYS;

  const narrative = generateNarrative({
    health: breakdown.health ?? 0,
    components,
    daysActive,
    trendGated,
  });

  return (
    <div className={`health-dropdown${alwaysOpen ? " always-open" : ""}`}>
      <div className="health-chip-row">
        {CHIPS.map((chip) => {
          const value = components[chip.key];
          const dimmed = trendGated && chip.key === "T";
          return (
            <span
              key={chip.key}
              className={`health-chip tone-${tone(value)}${dimmed ? " dim" : ""}`}
              title={chip.what}
            >
              <span className="health-chip-label">{chip.short}</span>
              <span className="health-chip-value">
                {dimmed ? "—" : Math.round(value * 100)}
              </span>
            </span>
          );
        })}
      </div>

      <p className="health-narrative">{narrative}</p>

      <button
        type="button"
        className="health-howto-toggle"
        onClick={() => setShowHow((v) => !v)}
        aria-expanded={showHow}
      >
        {showHow ? "Hide" : "How is this calculated?"}
      </button>

      {showHow ? (
        <ul className="health-howto-list">
          {CHIPS.map((chip) => (
            <li key={chip.key}>
              <strong>{chip.label}.</strong> {chip.what}
            </li>
          ))}
          <li>
            <strong>Reliability.</strong> {RELIABILITY_DESC}
          </li>
        </ul>
      ) : null}
    </div>
  );
}
