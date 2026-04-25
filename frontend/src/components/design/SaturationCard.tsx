import type { Saturation } from "@/lib/api";
import { formatPct } from "@/lib/format";

export function SaturationCard({ saturation }: { saturation: Saturation }) {
  const cohort = saturation.cohort_advertiser_size;
  if (cohort < 5) return null;

  const tone =
    cohort >= 8 ? "warn" : cohort >= 5 ? "neutral" : "muted";
  const tripleParts = [
    saturation.triple.theme,
    saturation.triple.hook_type,
    saturation.used_triple ? saturation.triple.dominant_color : null,
  ].filter(Boolean);
  const ctrDelta =
    saturation.this_ctr - saturation.cohort_avg_ctr;
  const cvrDelta =
    saturation.this_cvr - saturation.cohort_avg_cvr;
  const recommend = saturation.recommend_consolidate_to;

  return (
    <aside data-card="saturation" data-tone={tone}>
      <header>
        <span data-pill>Portfolio saturation</span>
        <small>
          {cohort} creatives in this advertiser share{" "}
          <strong>{tripleParts.join(" · ")}</strong>
          {saturation.used_triple ? "" : " (color too sparse, falling back to theme × hook)"}
          {" · "}
          {saturation.cohort_global_size} cross-portfolio
        </small>
      </header>
      <dl>
        <div>
          <dt>Cohort avg CTR</dt>
          <dd>{formatPct(saturation.cohort_avg_ctr)}</dd>
        </div>
        <div>
          <dt>Yours</dt>
          <dd>
            {formatPct(saturation.this_ctr)}{" "}
            <span className={ctrDelta >= 0 ? "chip-pos" : "chip-neg"} style={{ marginLeft: 6 }}>
              {ctrDelta >= 0 ? "+" : ""}
              {formatPct(ctrDelta)}
            </span>
          </dd>
        </div>
        <div>
          <dt>Cohort avg CVR</dt>
          <dd>{formatPct(saturation.cohort_avg_cvr)}</dd>
        </div>
        <div>
          <dt>Yours</dt>
          <dd>
            {formatPct(saturation.this_cvr)}{" "}
            <span className={cvrDelta >= 0 ? "chip-pos" : "chip-neg"} style={{ marginLeft: 6 }}>
              {cvrDelta >= 0 ? "+" : ""}
              {formatPct(cvrDelta)}
            </span>
          </dd>
        </div>
      </dl>
      {recommend !== null ? (
        <footer>
          <strong>Recommend:</strong> consolidate to {recommend} creative{recommend === 1 ? "" : "s"}.
          Near-duplicates risk audience saturation; the cohort already averages{" "}
          {formatPct(saturation.cohort_avg_ctr)} CTR with diminishing returns at scale.
        </footer>
      ) : null}
    </aside>
  );
}
