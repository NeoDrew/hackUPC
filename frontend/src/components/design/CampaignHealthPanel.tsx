import type { CampaignMetrics } from "@/lib/api";

function tone(score: number): string {
  if (score >= 70) return "good";
  if (score >= 40) return "watch";
  return "bad";
}

function pct(n: number): string {
  return `${(n * 100).toFixed(0)}%`;
}

function num(n: number, dp = 2): string {
  return n.toFixed(dp);
}

/**
 * Campaign composite health — transparent rollup of:
 *   30% (1 - %fatigued) · 25% mean drop_ratio · 20% (1 - ctr_cv/1.5) · 25% cohort_rank
 * Weights are heuristic, not learned — surfaced in the footnote so a judge
 * can defend the score with real arithmetic.
 */
export function CampaignHealthPanel({
  metrics,
}: {
  metrics: CampaignMetrics;
}) {
  const c = metrics.health_components;
  const t = tone(metrics.health);
  const rows: { key: string; label: string; raw: string; goodness: number }[] = [
    {
      key: "fatigued",
      label: "Creatives fatigued",
      raw: `${c.fatigued_count} / ${c.creative_count} (${pct(c.pct_fatigued)})`,
      goodness: 1 - c.pct_fatigued,
    },
    {
      key: "drop",
      label: "Mean CTR retention (last/first)",
      raw: num(c.mean_drop_ratio),
      goodness: Math.max(0, Math.min(1, c.mean_drop_ratio)),
    },
    {
      key: "cv",
      label: "Daily CTR coefficient of variation",
      raw: num(c.agg_ctr_cv),
      goodness: 1 - Math.max(0, Math.min(1, c.agg_ctr_cv / 1.5)),
    },
    {
      key: "cohort",
      label: "Cohort rank (vertical · objective)",
      raw: pct(c.cohort_rank_pct),
      goodness: c.cohort_rank_pct,
    },
  ];

  return (
    <section className="campaign-health-panel" aria-label="Campaign composite health">
      <header className="campaign-health-head">
        <div className="campaign-health-score-block">
          <span className={`campaign-health-score tone-${t}`}>{metrics.health}</span>
          <span className="campaign-health-score-out">/ 100</span>
        </div>
        <div className="campaign-health-explainer">
          <h3 className="t-section">Campaign health composite</h3>
          <p className="t-body muted">
            Rolled up from per-creative fatigue verdicts, retention, daily-CTR
            stability, and cohort rank. Weights are heuristic (30/25/20/25) —
            shown so the score is defensible, not an opaque ML output.
          </p>
        </div>
      </header>
      <ul className="campaign-health-rows">
        {rows.map((r) => (
          <li key={r.key} className="campaign-health-row">
            <span className="campaign-health-row-label">{r.label}</span>
            <span className="campaign-health-row-raw">{r.raw}</span>
            <span className="campaign-health-row-bar" aria-hidden>
              <span
                className="campaign-health-row-fill"
                style={{ width: `${Math.round(r.goodness * 100)}%` }}
              />
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
