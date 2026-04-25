import type { Quadrant } from "@/lib/api";

const LABELS: Record<string, { title: string; tone: string }> = {
  "top-performer": { title: "Top performer", tone: "good" },
  "clickbait-risk": { title: "Clickbait risk", tone: "warn" },
  "niche-converter": { title: "Niche converter", tone: "neutral" },
  "below-peers": { title: "Below peers", tone: "bad" },
  unknown: { title: "Unknown", tone: "muted" },
};

export function QuadrantBadge({ quadrant }: { quadrant: Quadrant }) {
  const meta = LABELS[quadrant.quadrant_label] ?? LABELS.unknown;
  return (
    <aside data-card="quadrant" data-tone={meta.tone}>
      <header>
        <span data-pill>{meta.title}</span>
        <small>
          vs cohort {quadrant.cohort_keys.vertical} ·{" "}
          {quadrant.cohort_keys.format} (n={quadrant.cohort_size})
        </small>
      </header>
      <dl>
        <div>
          <dt>CTR percentile</dt>
          <dd>{formatPercentile(quadrant.ctr_percentile)}</dd>
        </div>
        <div>
          <dt>CVR percentile</dt>
          <dd>{formatPercentile(quadrant.cvr_percentile)}</dd>
        </div>
      </dl>
      <footer>
        Diagnostic only. Raw cohort percentile, to be Bayesian-shrunk once
        ranking ships.
      </footer>
    </aside>
  );
}

function formatPercentile(p: number | null | undefined): string {
  if (p == null) return "–";
  return `${Math.round(p * 100)}${ordinalSuffix(Math.round(p * 100))}`;
}

function ordinalSuffix(n: number): string {
  const r = n % 100;
  if (r >= 11 && r <= 13) return "th";
  const last = n % 10;
  if (last === 1) return "st";
  if (last === 2) return "nd";
  if (last === 3) return "rd";
  return "th";
}
