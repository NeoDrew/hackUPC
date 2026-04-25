export interface WinningPattern {
  trait: string;
  what: string;
  /** % uplift in attribute prevalence among top performers vs the rest of
   * the cohort. Computed deterministically over the cohort attribute table
   * — no LLM. */
  lift_pct: number;
  /** % of top performers that share this trait. */
  prevalence_pct: number;
  winner_count: number;
}

export function WinningPatternsCard({
  patterns,
}: {
  patterns: WinningPattern[];
}) {
  if (patterns.length === 0) {
    return (
      <p className="t-body muted">
        Cohort sample is too small to detect winning attribute patterns.
      </p>
    );
  }
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: `repeat(${Math.min(3, patterns.length)}, minmax(0, 1fr))`,
        gap: 12,
      }}
    >
      {patterns.map((p, i) => (
        <div key={i} className="pattern-card">
          <div className="row between center">
            <span className="lift">{formatLift(p.lift_pct)}</span>
            <span className="prevalence">
              in {Math.round(p.prevalence_pct)}% of winners
            </span>
          </div>
          <span className="trait">{p.trait}</span>
          <span className="what">{p.what}</span>
        </div>
      ))}
    </div>
  );
}

function formatLift(pct: number): string {
  if (!Number.isFinite(pct)) return "—";
  const sign = pct >= 0 ? "+" : "";
  return `${sign}${Math.round(pct)}%`;
}
