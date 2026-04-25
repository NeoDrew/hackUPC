"use client";

import { useState } from "react";

import type { HealthBreakdown } from "@/lib/api";
import { formatPct } from "@/lib/format";

/* ------------------------------------------------------------------
   Q1 Health Breakdown — unified panel.

   Replaces both HealthBreakdownCard (the rich row-with-bars layout) and
   HealthBreakdownDropdown (chips + narrative). The table layout is kept
   because the user prefers it; each row is now expandable to reveal the
   exact math the backend uses to derive that component, populated with
   this creative's actual numbers. The point: a sceptical judge clicking
   "Strength" should see real arithmetic, not an LLM rationalisation.
   ------------------------------------------------------------------ */

const TREND_GATE_DAYS = 7;

type ObjectiveMode = "ctr" | "cvr" | "roas" | "cpa";

interface RawPayload {
  selected_objective_value?: number;
  credible_interval_width?: number;
  effective_sample_size?: number;
  efficiency_value?: number;
}

interface CohortMeta {
  level?: string;
  size?: number;
  keys?: Record<string, unknown>;
}

interface RowData {
  total_impressions?: number;
  total_clicks?: number;
  total_conversions?: number;
  total_spend_usd?: number;
  total_revenue_usd?: number;
  total_days_active?: number;
}

interface ComponentDef {
  key: "S" | "C" | "T" | "R" | "E" | "B";
  weightKey: string;
  label: string;
  short: string;
  description: string;
  weakNarrative: string;
}

const COMPONENTS: readonly ComponentDef[] = [
  {
    key: "S",
    weightKey: "w1",
    label: "Strength",
    short: "Strength",
    description: "Posterior performance on this creative's KPI goal",
    weakNarrative:
      "raw conversion power is weak — even with healthy traffic it isn't earning enough returns",
  },
  {
    key: "C",
    weightKey: "w2",
    label: "Confidence",
    short: "Confidence",
    description: "How narrow the 95% credible interval around the score is",
    weakNarrative:
      "we don't have enough data yet to be confident in the score",
  },
  {
    key: "T",
    weightKey: "w3",
    label: "Trend",
    short: "Trend",
    description: "Whether daily performance is improving or fading recently",
    weakNarrative:
      "performance is fading day-over-day — it's burning out faster than peers",
  },
  {
    key: "R",
    weightKey: "w4",
    label: "Cohort rank",
    short: "Cohort",
    description: "Percentile rank against peers in the same vertical / format / country / OS",
    weakNarrative:
      "it's losing to its peers in the same vertical and format",
  },
  {
    key: "E",
    weightKey: "w5",
    label: "Efficiency",
    short: "Efficiency",
    description: "Return per dollar spent — ROAS, or inverse CPA when the goal is cost",
    weakNarrative:
      "spend isn't converting into return — every dollar is buying less than peers",
  },
  {
    key: "B",
    weightKey: "w6",
    label: "Reliability",
    short: "Reliability",
    description: "Bonus for creatives with a statistically meaningful sample",
    weakNarrative:
      "we don't have enough volume to call this score reliable",
  },
] as const;

const MODE_KPI: Record<ObjectiveMode, string> = {
  ctr: "CTR (clicks / impressions)",
  cvr: "CVR (conversions / clicks)",
  roas: "ROAS (revenue / spend)",
  cpa: "1 / CPA (conversions / spend)",
};

const MODE_NUM: Record<ObjectiveMode, string> = {
  ctr: "clicks",
  cvr: "conversions",
  roas: "revenue ($)",
  cpa: "conversions",
};
const MODE_DEN: Record<ObjectiveMode, string> = {
  ctr: "impressions",
  cvr: "clicks",
  roas: "spend ($)",
  cpa: "spend ($)",
};

const MODE_SAMPLE_FIELD: Record<ObjectiveMode, string> = {
  ctr: "impressions",
  cvr: "clicks",
  roas: "spend",
  cpa: "conversions",
};

interface NarrativeInput {
  health: number;
  components: { S: number; C: number; T: number; R: number; E: number; B: number };
  daysActive?: number;
  trendGated: boolean;
}

export function generateNarrative(input: NarrativeInput): string {
  const { health, components, daysActive, trendGated } = input;

  const candidates = COMPONENTS.filter(
    (c) => c.key !== "B" && !(trendGated && c.key === "T"),
  );
  const sorted = [...candidates].sort(
    (a, b) => components[a.key] - components[b.key],
  );
  const weakest = sorted[0];

  // "Data-bottlenecked" case: low Confidence (or low Reliability) is the
  // dominant problem — every other component is reasonably healthy. The
  // right call here is to wait for more impressions/clicks, NOT to pause
  // a creative that hasn't had a fair chance yet.
  const dataBottlenecked = isDataBottlenecked(components, trendGated);

  let lead: string;
  if (trendGated && daysActive !== undefined) {
    lead = `Active for ${daysActive} day${daysActive === 1 ? "" : "s"} — too early to assess trend, but ${weakest.weakNarrative}.`;
  } else if (dataBottlenecked) {
    const reason =
      components.C <= components.B
        ? "we don't have enough data yet to be confident in the score"
        : "this creative hasn't accumulated enough volume to call reliable";
    lead = `${reason.charAt(0).toUpperCase() + reason.slice(1)}.`;
  } else if (weakest && components[weakest.key] < 0.5) {
    lead = `${weakest.weakNarrative.charAt(0).toUpperCase() + weakest.weakNarrative.slice(1)}.`;
  } else {
    lead = "All components are within healthy range — no single weakness stands out.";
  }

  let verdict: string;
  if (dataBottlenecked) {
    verdict = "Hold and let it gather more data before deciding.";
  } else if (health >= 70) {
    verdict = "Safe to scale.";
  } else if (health >= 45) {
    verdict = "Monitor closely.";
  } else {
    verdict = "Consider pausing or refreshing this creative.";
  }

  return `${lead} ${verdict}`;
}

/** Low Confidence (or low Reliability) is the binding constraint when:
 *  - C or B is below 0.4, AND
 *  - Strength, Trend (if not gated), Cohort rank, and Efficiency are all
 *    at or above the median (≥ 0.5). I.e. the creative would look fine if
 *    we only had more data on it.
 */
function isDataBottlenecked(
  components: NarrativeInput["components"],
  trendGated: boolean,
): boolean {
  const cLow = components.C < 0.4;
  const bLow = components.B < 0.4;
  if (!cLow && !bLow) return false;
  const performanceFloor =
    components.S >= 0.5 &&
    components.R >= 0.5 &&
    components.E >= 0.5 &&
    (trendGated || components.T >= 0.5);
  return performanceFloor;
}

function tone(value: number): "good" | "warn" | "bad" {
  if (value >= 0.7) return "good";
  if (value >= 0.4) return "warn";
  return "bad";
}

function fmt(n: number | undefined | null, digits = 4): string {
  if (n === undefined || n === null || !Number.isFinite(n)) return "–";
  if (Math.abs(n) >= 1000) return n.toLocaleString("en-US", { maximumFractionDigits: 0 });
  return n.toLocaleString("en-US", { maximumFractionDigits: digits });
}

function fmtCount(n: number | undefined | null): string {
  if (n === undefined || n === null || !Number.isFinite(n)) return "–";
  return Math.round(n).toLocaleString("en-US");
}

export function HealthBreakdownPanel({
  breakdown,
  daysActive,
  alwaysOpen = false,
  rowData,
}: {
  breakdown?: HealthBreakdown | null;
  daysActive?: number;
  alwaysOpen?: boolean;
  rowData?: RowData;
}) {
  // expandedKey is null when no component-row is expanded; otherwise the component key.
  const [expandedKey, setExpandedKey] = useState<ComponentDef["key"] | null>(null);
  // Customer-summary by default — full breakdown table starts collapsed
  // even on the always-open detail page. Marketers don't want bars + weights
  // in their face on first glance.
  const [showFull, setShowFull] = useState(false);

  if (!breakdown?.components) return null;

  const c = breakdown.components as Record<string, number>;
  const components = {
    S: c.S ?? 0,
    C: c.C ?? 0,
    T: c.T ?? 0,
    R: c.R ?? 0,
    E: c.E ?? 0,
    B: c.B ?? 0,
  };
  const trendGated =
    daysActive !== undefined && daysActive < TREND_GATE_DAYS;
  const weights = (breakdown.weights ?? {}) as Record<string, number>;
  const contributions = (breakdown.contributions ?? {}) as Record<string, number>;
  const raw = ((breakdown as unknown as { raw?: RawPayload }).raw ?? {}) as RawPayload;
  const cohort = (breakdown.cohort ?? {}) as CohortMeta;
  const objectiveMode = (breakdown.objective_mode || "ctr") as ObjectiveMode;
  const kpiGoal = breakdown.kpi_goal ?? objectiveMode.toUpperCase();

  const narrative = generateNarrative({
    health: breakdown.health ?? 0,
    components,
    daysActive,
    trendGated,
  });

  const cohortKeys = cohort?.keys
    ? Object.values(cohort.keys)
        .filter((v) => v !== null && v !== undefined && v !== "")
        .map(String)
        .join(" · ")
    : null;

  const verdictTone =
    (breakdown.health ?? 0) >= 70 ? "good"
    : (breakdown.health ?? 0) >= 45 ? "warn"
    : "bad";
  const bandLabel = (breakdown.status_band ?? "").charAt(0).toUpperCase() +
    (breakdown.status_band ?? "").slice(1);

  return (
    <section className={`health-panel${alwaysOpen ? " always-open" : ""}`}>
      <header className="health-panel-head">
        <div className="col gap-1" style={{ minWidth: 0 }}>
          <h3 className="t-section" style={{ margin: 0 }}>Health</h3>
          <span className="t-micro muted">
            {kpiGoal} goal · {bandLabel || "–"}
          </span>
        </div>
        <div className="col gap-1" style={{ alignItems: "flex-end" }}>
          <strong className={`health-panel-score tone-${verdictTone}`}>
            {Number.isFinite(breakdown.health ?? NaN) ? breakdown.health : "–"}
          </strong>
        </div>
      </header>

      <p className="health-panel-narrative">{narrative}</p>

      <button
        type="button"
        className="health-panel-toggle"
        onClick={() => setShowFull((v) => !v)}
        aria-expanded={showFull}
      >
        {showFull ? "Hide full breakdown" : "See full breakdown"}
        <span className="health-panel-toggle-icon">▾</span>
      </button>

      {showFull ? (
        <>
          <div className="health-panel-rows">
            {COMPONENTS.map((cdef) => {
          const value = components[cdef.key];
          const dimmed = trendGated && cdef.key === "T";
          const weight = weights[cdef.weightKey] ?? 0;
          const contribution = contributions[cdef.key] ?? 0;
          const expanded = expandedKey === cdef.key;
          return (
            <div
              key={cdef.key}
              className={`health-panel-row${expanded ? " expanded" : ""}`}
            >
              <button
                type="button"
                className="health-panel-row-summary"
                onClick={() => setExpandedKey((k) => (k === cdef.key ? null : cdef.key))}
                aria-expanded={expanded}
              >
                <div className="col gap-1" style={{ minWidth: 0 }}>
                  <span className="health-panel-row-label">
                    <span
                      className={`health-panel-tone-dot tone-${tone(value)}${dimmed ? " dim" : ""}`}
                      aria-hidden
                    />
                    <span className="health-panel-row-name">{cdef.label}</span>
                    <span className="t-micro muted">· {cdef.description}</span>
                  </span>
                </div>

                <div className="col gap-1">
                  <div className="score-bar" aria-label={`${cdef.label} ${formatPct(value, 0)}`}>
                    <div
                      style={{
                        width: `${Math.max(3, value * 100)}%`,
                        background:
                          tone(value) === "good"
                            ? "var(--status-top)"
                            : tone(value) === "warn"
                              ? "var(--status-fatigued)"
                              : "var(--status-cut)",
                      }}
                    />
                  </div>
                  <span className="t-micro muted">
                    Weight {formatPct(weight, 0)} · contributes {contribution.toFixed(2)} pts to health
                  </span>
                </div>

                <div className="health-panel-row-score">
                  {dimmed ? "—" : Math.round(value * 100)}
                </div>

                <span className="health-panel-row-chevron" aria-hidden>
                  ▾
                </span>
              </button>

              {expanded ? (
                <div className="health-panel-row-detail">
                  <ComponentMath
                    component={cdef}
                    components={components}
                    value={value}
                    weight={weight}
                    contribution={contribution}
                    raw={raw}
                    cohort={cohort}
                    objectiveMode={objectiveMode}
                    rowData={rowData}
                    daysActive={daysActive}
                    dimmed={dimmed}
                  />
                </div>
              ) : null}
            </div>
          );
        })}
      </div>

          <footer className="health-panel-foot">
            <div className="health-panel-meta">
              <span className="t-micro muted">
                Cohort:{" "}
                <strong>
                  {cohort?.level ?? "fallback"}
                  {cohort?.size ? ` · n=${cohort.size}` : ""}
                </strong>
                {cohortKeys ? ` · ${cohortKeys}` : ""}
              </span>
              <span className="t-micro muted">
                Final: 100 ×
                (w₁·S + w₂·C + w₃·T + w₄·R + w₅·E + w₆·B)
                =&nbsp;<strong>{breakdown.health ?? "–"}</strong>
              </span>
            </div>
          </footer>
        </>
      ) : null}
    </section>
  );
}

/* ------------------------------------------------------------------
   Per-component math panels. Each one walks through the exact formula
   used in backend/app/datastore.py::_compute_health_scores, with this
   creative's numbers plugged in. Every value here comes from the
   `breakdown` payload — none of it is invented.
   ------------------------------------------------------------------ */

function ComponentMath({
  component,
  components,
  value,
  weight,
  contribution,
  raw,
  cohort,
  objectiveMode,
  rowData,
  daysActive,
  dimmed,
}: {
  component: ComponentDef;
  components: { S: number; C: number; T: number; R: number; E: number; B: number };
  value: number;
  weight: number;
  contribution: number;
  raw: RawPayload;
  cohort: CohortMeta;
  objectiveMode: ObjectiveMode;
  rowData?: RowData;
  daysActive?: number;
  dimmed: boolean;
}) {
  switch (component.key) {
    case "S":
      return (
        <StrengthMath
          objectiveMode={objectiveMode}
          posterior={raw.selected_objective_value}
          rowData={rowData}
          value={value}
          weight={weight}
          contribution={contribution}
        />
      );
    case "C":
      return (
        <ConfidenceMath
          objectiveMode={objectiveMode}
          width={raw.credible_interval_width}
          posterior={raw.selected_objective_value}
          sample={raw.effective_sample_size}
          value={value}
          weight={weight}
          contribution={contribution}
        />
      );
    case "T":
      return (
        <TrendMath
          objectiveMode={objectiveMode}
          value={value}
          weight={weight}
          contribution={contribution}
          daysActive={daysActive}
          gated={dimmed}
        />
      );
    case "R":
      return (
        <CohortMath
          cohort={cohort}
          objectiveMode={objectiveMode}
          value={value}
          weight={weight}
          contribution={contribution}
        />
      );
    case "E":
      return (
        <EfficiencyMath
          objectiveMode={objectiveMode}
          efficiency={raw.efficiency_value}
          value={value}
          weight={weight}
          contribution={contribution}
        />
      );
    case "B":
      return (
        <ReliabilityMath
          objectiveMode={objectiveMode}
          sample={raw.effective_sample_size}
          value={value}
          weight={weight}
          contribution={contribution}
        />
      );
  }
}

function MathBlock({ children }: { children: React.ReactNode }) {
  return <div className="health-math-block">{children}</div>;
}

function MathRow({ label, value }: { label: React.ReactNode; value: React.ReactNode }) {
  return (
    <div className="health-math-row">
      <span className="health-math-label">{label}</span>
      <span className="health-math-value">{value}</span>
    </div>
  );
}

function StrengthMath({
  objectiveMode,
  posterior,
  rowData,
  value,
  weight,
  contribution,
}: {
  objectiveMode: ObjectiveMode;
  posterior?: number;
  rowData?: RowData;
  value: number;
  weight: number;
  contribution: number;
}) {
  const num = MODE_NUM[objectiveMode];
  const den = MODE_DEN[objectiveMode];
  return (
    <>
      <p className="health-math-text">
        <strong>What it measures:</strong> the posterior performance on this creative's
        KPI goal ({MODE_KPI[objectiveMode]}), smoothed against the (vertical, format)
        cohort baseline so a 50-impression creative can't out-rank a 5M-impression one.
      </p>

      <p className="health-math-text"><strong>Step 1 — Empirical Bayes smoothing.</strong></p>
      <MathBlock>
        <code>
          {`KPI_post = (${num} + cohort_prior × n)
           / (${den} + n)`}
        </code>
        <p className="t-micro muted" style={{ margin: "6px 0 0" }}>
          where <code>cohort_prior</code> = the cohort's pooled <code>{num}/{den}</code>{" "}
          and <code>n</code> = a sample-size prior calibrated from the portfolio median{" "}
          (<code>n</code> ∈ [1k, 10k] for CTR, [50, 500] for CVR, [100, 1k] for ROAS/CPA).
        </p>
      </MathBlock>

      <p className="health-math-text"><strong>Step 2 — Robust normalization to [0, 1].</strong></p>
      <MathBlock>
        <code>S = clip((KPI_post − p₅) / (p₉₅ − p₅), 0, 1)</code>
        <p className="t-micro muted" style={{ margin: "6px 0 0" }}>
          where <code>p₅</code>, <code>p₉₅</code> are the 5th and 95th percentiles of
          <code> KPI_post</code> across all creatives running the same KPI goal.
          Trimming at the 5/95 percentiles makes the score insensitive to outliers.
        </p>
      </MathBlock>

      <p className="health-math-text"><strong>This creative</strong></p>
      <MathBlock>
        <MathRow label={`KPI goal`} value={objectiveMode.toUpperCase()} />
        <MathRow
          label={`Raw ${num}`}
          value={
            objectiveMode === "ctr" ? fmtCount(rowData?.total_clicks)
            : objectiveMode === "cvr" ? fmtCount(rowData?.total_conversions)
            : objectiveMode === "roas" ? `$${fmt(rowData?.total_revenue_usd, 2)}`
            : fmtCount(rowData?.total_conversions)
          }
        />
        <MathRow
          label={`Raw ${den}`}
          value={
            objectiveMode === "ctr" ? fmtCount(rowData?.total_impressions)
            : objectiveMode === "cvr" ? fmtCount(rowData?.total_clicks)
            : `$${fmt(rowData?.total_spend_usd, 2)}`
          }
        />
        <MathRow label={<><code>KPI_post</code> (smoothed)</>} value={fmt(posterior, 6)} />
        <MathRow label={<>Normalised → <code>S</code></>} value={value.toFixed(3)} />
      </MathBlock>

      <ContributionRow value={value} weight={weight} contribution={contribution} symbol="S" />
    </>
  );
}

function ConfidenceMath({
  objectiveMode,
  width,
  posterior,
  sample,
  value,
  weight,
  contribution,
}: {
  objectiveMode: ObjectiveMode;
  width?: number;
  posterior?: number;
  sample?: number;
  value: number;
  weight: number;
  contribution: number;
}) {
  const isProportion = objectiveMode === "ctr" || objectiveMode === "cvr";
  return (
    <>
      <p className="health-math-text">
        <strong>What it measures:</strong> how narrow the 95% credible interval around
        the posterior KPI is. A creative with the same point estimate but more data
        gets a higher confidence score because its interval is tighter.
      </p>

      <p className="health-math-text"><strong>Step 1 — 95% interval width.</strong></p>
      <MathBlock>
        <code>
          {isProportion
            ? `width = 3.92 × √(p × (1 − p) / (n + n_prior + 1))`
            : `width = 1 / √(spend + n_prior + 1)`}
        </code>
        <p className="t-micro muted" style={{ margin: "6px 0 0" }}>
          {isProportion
            ? <>For CTR/CVR we use a Wilson-style normal approximation on the smoothed
                rate <code>p = KPI_post</code> with effective sample <code>n + n_prior</code>.</>
            : <>For ROAS/CPA we use spend as the precision proxy — more spend = tighter interval.</>
          }
          {" "}3.92 = 2 × 1.96 (the two-tailed z for 95%).
        </p>
      </MathBlock>

      <p className="health-math-text"><strong>Step 2 — Invert and normalize.</strong></p>
      <MathBlock>
        <code>C = clip(1 − width / p₉₅(width), 0, 1)</code>
        <p className="t-micro muted" style={{ margin: "6px 0 0" }}>
          Narrower interval → higher <code>C</code>. Divisor is the 95th percentile width
          across the same-objective cohort, so confidence is a relative ranking.
        </p>
      </MathBlock>

      <p className="health-math-text"><strong>This creative</strong></p>
      <MathBlock>
        <MathRow label={<>Posterior <code>p</code> = KPI_post</>} value={fmt(posterior, 6)} />
        <MathRow
          label={`Effective sample (${MODE_SAMPLE_FIELD[objectiveMode]})`}
          value={fmtCount(sample)}
        />
        <MathRow label="Interval width" value={fmt(width, 6)} />
        <MathRow label={<>Inverted &amp; normalised → <code>C</code></>} value={value.toFixed(3)} />
      </MathBlock>

      <ContributionRow value={value} weight={weight} contribution={contribution} symbol="C" />
    </>
  );
}

function TrendMath({
  objectiveMode,
  value,
  weight,
  contribution,
  daysActive,
  gated,
}: {
  objectiveMode: ObjectiveMode;
  value: number;
  weight: number;
  contribution: number;
  daysActive?: number;
  gated: boolean;
}) {
  return (
    <>
      <p className="health-math-text">
        <strong>What it measures:</strong> whether daily {MODE_KPI[objectiveMode]} is
        improving or fading over the recent window. Implemented as a two-window
        comparison rather than a slope, so noisy single-day spikes don't dominate.
      </p>

      <p className="health-math-text"><strong>Step 1 — Split the last 14 days.</strong></p>
      <MathBlock>
        <code>tail = points[-14:]
midpoint = ⌊len(tail) / 2⌋
prior   = tail[:midpoint]
recent  = tail[midpoint:]</code>
        <p className="t-micro muted" style={{ margin: "6px 0 0" }}>
          Each half is then aggregated to a single KPI value (sum-of-numerators /
          sum-of-denominators, not a mean of daily ratios — that prevents low-volume
          days from skewing the average).
        </p>
      </MathBlock>

      <p className="health-math-text"><strong>Step 2 — Signed change &amp; clip.</strong></p>
      <MathBlock>
        <code>{`Δ = (recent − prior) / |prior|
T = clip(0.5 + 0.5 × Δ, 0, 1)`}</code>
        <p className="t-micro muted" style={{ margin: "6px 0 0" }}>
          So <code>Δ = 0</code> (flat) → <code>T = 0.5</code>; <code>Δ = +1</code>{" "}
          (doubled) → <code>T = 1.0</code>; <code>Δ ≤ −1</code> (halved or worse) →{" "}
          <code>T = 0.0</code>. Gated to <code>T = 0</code> entirely when{" "}
          <code>days_active &lt; 7</code> or fewer than 2 daily points exist.
        </p>
      </MathBlock>

      <p className="health-math-text"><strong>This creative</strong></p>
      <MathBlock>
        <MathRow label="Days active" value={fmtCount(daysActive)} />
        <MathRow
          label="Gating"
          value={gated ? "gated (too few days)" : `passes (${daysActive} ≥ 7)`}
        />
        <MathRow label={<><code>T</code></>} value={gated ? "0.000 (gated)" : value.toFixed(3)} />
      </MathBlock>

      <ContributionRow value={value} weight={weight} contribution={contribution} symbol="T" />
    </>
  );
}

function CohortMath({
  cohort,
  objectiveMode,
  value,
  weight,
  contribution,
}: {
  cohort: CohortMeta;
  objectiveMode: ObjectiveMode;
  value: number;
  weight: number;
  contribution: number;
}) {
  const cohortKeys = cohort?.keys
    ? Object.entries(cohort.keys)
        .filter(([, v]) => v !== null && v !== undefined && v !== "")
        .map(([k, v]) => `${k}=${String(v)}`)
        .join(", ")
    : null;
  return (
    <>
      <p className="health-math-text">
        <strong>What it measures:</strong> where this creative ranks against peers in
        the same (vertical × format × country × OS) segment, on its KPI metric. Falls
        back to the broader (vertical × format) cohort if the segment is sparse.
      </p>

      <p className="health-math-text"><strong>Formula.</strong></p>
      <MathBlock>
        <code>R = pct_rank(KPI_value, peers_in_cohort) ∈ [0, 1]</code>
        <p className="t-micro muted" style={{ margin: "6px 0 0" }}>
          Pandas <code>rank(pct=True)</code>: <code>R = 0.5</code> means median peer,{" "}
          <code>R = 1.0</code> means top of the cohort.
        </p>
      </MathBlock>

      <p className="health-math-text"><strong>This creative</strong></p>
      <MathBlock>
        <MathRow
          label="Cohort level"
          value={cohort?.level ?? "fallback"}
        />
        <MathRow label="Cohort size" value={fmtCount(cohort?.size)} />
        <MathRow label="Cohort keys" value={cohortKeys ?? "–"} />
        <MathRow label="Ranking metric" value={MODE_KPI[objectiveMode]} />
        <MathRow label={<><code>R</code></>} value={value.toFixed(3)} />
      </MathBlock>

      <ContributionRow value={value} weight={weight} contribution={contribution} symbol="R" />
    </>
  );
}

function EfficiencyMath({
  objectiveMode,
  efficiency,
  value,
  weight,
  contribution,
}: {
  objectiveMode: ObjectiveMode;
  efficiency?: number;
  value: number;
  weight: number;
  contribution: number;
}) {
  return (
    <>
      <p className="health-math-text">
        <strong>What it measures:</strong> business efficiency — return per dollar
        spent. Tracked even when the KPI goal isn't ROAS/CPA, because a creative with
        great CTR but no return-on-spend is still a problem.
      </p>

      <p className="health-math-text"><strong>Definition.</strong></p>
      <MathBlock>
        <code>{`efficiency_value = ROAS_post           if mode ∈ {ctr, cvr, roas}
                 = (1 / CPA_post) = conv / spend  if mode = cpa`}</code>
        <p className="t-micro muted" style={{ margin: "6px 0 0" }}>
          ROAS_post / CPA_post are the empirical-Bayes-smoothed posteriors from
          step S above (same prior, same n).
        </p>
      </MathBlock>

      <p className="health-math-text"><strong>Normalization.</strong></p>
      <MathBlock>
        <code>E = clip((efficiency_value − p₅) / (p₉₅ − p₅), 0, 1)</code>
      </MathBlock>

      <p className="health-math-text"><strong>This creative</strong></p>
      <MathBlock>
        <MathRow label="KPI mode" value={objectiveMode.toUpperCase()} />
        <MathRow label="efficiency_value" value={fmt(efficiency, 6)} />
        <MathRow label={<><code>E</code></>} value={value.toFixed(3)} />
      </MathBlock>

      <ContributionRow value={value} weight={weight} contribution={contribution} symbol="E" />
    </>
  );
}

function ReliabilityMath({
  objectiveMode,
  sample,
  value,
  weight,
  contribution,
}: {
  objectiveMode: ObjectiveMode;
  sample?: number;
  value: number;
  weight: number;
  contribution: number;
}) {
  return (
    <>
      <p className="health-math-text">
        <strong>What it measures:</strong> a small bonus for creatives with enough
        data to be statistically meaningful. Uses a logarithmic scale so the bonus
        diminishes as samples grow — going from 1k → 10k matters more than 100k → 1M.
      </p>

      <p className="health-math-text"><strong>Formula.</strong></p>
      <MathBlock>
        <code>{`B = log(1 + n) / log(1 + p₉₅(n))`}</code>
        <p className="t-micro muted" style={{ margin: "6px 0 0" }}>
          where <code>n</code> = the effective sample for this objective:{" "}
          impressions for CTR, clicks for CVR, spend for ROAS, conversions for CPA.{" "}
          The denominator is the 95th-percentile sample across the same-objective
          cohort, so <code>B</code> sits in [0, 1].
        </p>
      </MathBlock>

      <p className="health-math-text"><strong>This creative</strong></p>
      <MathBlock>
        <MathRow
          label={`Effective sample (${MODE_SAMPLE_FIELD[objectiveMode]})`}
          value={fmtCount(sample)}
        />
        <MathRow label={<><code>B</code></>} value={value.toFixed(3)} />
      </MathBlock>

      <ContributionRow value={value} weight={weight} contribution={contribution} symbol="B" />
    </>
  );
}

function ContributionRow({
  value,
  weight,
  contribution,
  symbol,
}: {
  value: number;
  weight: number;
  contribution: number;
  symbol: string;
}) {
  return (
    <div className="health-math-contribution">
      <code>
        contribution = 100 × weight × {symbol} = 100 × {formatPct(weight, 0)} × {value.toFixed(3)} = {contribution.toFixed(2)} pts
      </code>
    </div>
  );
}
