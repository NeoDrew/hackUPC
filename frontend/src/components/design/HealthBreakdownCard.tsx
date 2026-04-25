import type { HealthBreakdown } from "@/lib/api";
import { formatPct } from "@/lib/format";

type HealthComponents = HealthBreakdown["components"];

type HealthBreakdownCardData = Omit<
  HealthBreakdown,
  "cohort" | "components"
> & {
  components?: HealthComponents | null;
  cohort?: {
    level?: string;
    size?: number;
    keys?: Record<string, unknown>;
  };
};

const COMPONENTS: Array<{
  key: keyof HealthComponents;
  weightKey: string;
  label: string;
  description: string;
}> = [
  {
    key: "S",
    weightKey: "w1",
    label: "Strength",
    description: "Posterior objective performance",
  },
  {
    key: "C",
    weightKey: "w2",
    label: "Confidence",
    description: "Narrower credible interval",
  },
  {
    key: "T",
    weightKey: "w3",
    label: "Trend",
    description: "Recent objective slope",
  },
  {
    key: "R",
    weightKey: "w4",
    label: "Cohort rank",
    description: "Fair peer percentile",
  },
  {
    key: "E",
    weightKey: "w5",
    label: "Efficiency",
    description: "ROAS / inverse CPA signal",
  },
  {
    key: "B",
    weightKey: "w6",
    label: "Reliability",
    description: "Effective sample bonus",
  },
];

export function HealthBreakdownCard({
  breakdown,
}: {
  breakdown?: HealthBreakdownCardData | null;
}) {
  if (!breakdown?.components) return null;

  const objective = breakdown.objective_mode?.toUpperCase() ?? "OBJECTIVE";
  const cohort = breakdown.cohort;
  const cohortKeys = cohort?.keys
    ? Object.values(cohort.keys)
        .filter(
          (value) => value !== null && value !== undefined && value !== "",
        )
        .map(String)
        .join(" · ")
    : null;

  return (
    <section
      className="col gap-3"
      style={{
        background: "var(--bg-1)",
        border: "1px solid var(--line)",
        borderRadius: 12,
        padding: 16,
      }}
    >
      <header className="row center between" style={{ gap: 16 }}>
        <div className="col gap-1">
          <h3 className="t-section" style={{ margin: 0 }}>
            Q1 health breakdown
          </h3>
          <p className="t-micro muted" style={{ margin: 0 }}>
            Evidence-based score using posterior strength, confidence, trend,
            cohort rank, efficiency, and reliability.
          </p>
        </div>
        <div className="col gap-1" style={{ alignItems: "flex-end" }}>
          <span className="t-overline">{objective}</span>
          <strong style={{ fontSize: 28, lineHeight: 1 }}>
            {Number.isFinite(breakdown.health ?? NaN) ? breakdown.health : "–"}
          </strong>
        </div>
      </header>

      <div className="col gap-2">
        {COMPONENTS.map((component) => {
          const value = clamp01(breakdown.components?.[component.key] ?? 0);
          const weight = breakdown.weights?.[component.weightKey] ?? 0;
          const contribution = breakdown.contributions?.[component.key] ?? 0;

          return (
            <div
              key={component.key}
              style={{
                display: "grid",
                gridTemplateColumns: "132px 1fr 68px",
                gap: 12,
                alignItems: "center",
              }}
            >
              <div className="col gap-1">
                <span className="t-micro" style={{ color: "var(--fg-0)" }}>
                  {component.key} · {component.label}
                </span>
                <span className="t-micro muted">{component.description}</span>
              </div>

              <div className="col gap-1">
                <div
                  className="score-bar"
                  aria-label={`${component.label} ${formatPct(value, 0)}`}
                >
                  <div
                    style={{
                      width: `${Math.max(3, value * 100)}%`,
                      background: "var(--accent)",
                    }}
                  />
                </div>
                <span className="t-micro muted">
                  Weight {formatPct(weight, 0)} · contributes{" "}
                  {contribution.toFixed(1)} pts
                </span>
              </div>

              <strong style={{ textAlign: "right" }}>
                {formatPct(value, 0)}
              </strong>
            </div>
          );
        })}
      </div>

      <footer
        className="row center between"
        style={{
          borderTop: "1px solid var(--line-soft)",
          paddingTop: 12,
          gap: 16,
          flexWrap: "wrap",
        }}
      >
        <span className="t-micro muted">
          KPI goal: <strong>{breakdown.kpi_goal ?? "–"}</strong>
          {" · "}
          Band: <strong>{breakdown.status_band ?? "–"}</strong>
        </span>
        <span className="t-micro muted">
          Cohort:{" "}
          <strong>
            {cohort?.level ?? "fallback"}
            {cohort?.size ? ` · n=${cohort.size}` : ""}
          </strong>
          {cohortKeys ? ` · ${cohortKeys}` : ""}
        </span>
      </footer>
    </section>
  );
}

function clamp01(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(1, value));
}
