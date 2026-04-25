import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { listRecommendations, type RecommendationsScope } from "@/lib/api";

/**
 * Top-of-cockpit advisor summary. One row, slots under <KpiStrip /> on
 * the landing page. Tells the marketer at a glance how much is on the
 * table and links to the full /actions queue.
 *
 * Server component — fetches the ranked list, surfaces the headline
 * counts, never blocks render on Gemma polish (the deterministic
 * rationale is always present).
 */
export async function AdvisorBanner({
  advertiserId,
  campaignId,
}: {
  advertiserId?: number;
  campaignId?: number;
}) {
  const scope: RecommendationsScope = {};
  if (advertiserId) scope.advertiser_id = advertiserId;
  if (campaignId) scope.campaign_id = campaignId;

  const data = await listRecommendations(scope).catch(() => null);

  if (!data || data.recommendations.length === 0) {
    return null;
  }

  const total = data.recommendations.length;
  const c = data.counts_by_severity.critical ?? 0;
  const w = data.counts_by_severity.warning ?? 0;
  const o = data.counts_by_severity.opportunity ?? 0;
  const impactStr = formatImpact(data.total_daily_impact_usd);

  // Top three by est_daily_impact_usd — show as a single-line preview.
  const top3 = data.recommendations.slice(0, 3);

  return (
    <section className="advisor-banner" aria-label="Advisor summary">
      <div className="advisor-banner-headline">
        <span className="advisor-banner-icon" aria-hidden>
          ⚠
        </span>
        <strong className="advisor-banner-strong">
          {total} action{total === 1 ? "" : "s"} ready
        </strong>
        <span className="advisor-banner-meta">
          · est. ${impactStr}/day at stake
        </span>
      </div>
      <div className="advisor-banner-pips">
        {c > 0 ? (
          <span className="advisor-pip advisor-pip-critical">
            <span className="advisor-pip-dot" aria-hidden />
            {c} critical
          </span>
        ) : null}
        {w > 0 ? (
          <span className="advisor-pip advisor-pip-warning">
            <span className="advisor-pip-dot" aria-hidden />
            {w} warning
          </span>
        ) : null}
        {o > 0 ? (
          <span className="advisor-pip advisor-pip-opportunity">
            <span className="advisor-pip-dot" aria-hidden />
            {o} opportunity
          </span>
        ) : null}
      </div>
      <div className="advisor-banner-preview" aria-hidden>
        {top3.map((rec) => (
          <span key={rec.recommendation_id} className="advisor-banner-preview-item">
            {rec.headline}
          </span>
        ))}
      </div>
      <Link
        href="/actions"
        prefetch={false}
        className="advisor-banner-cta primary"
      >
        Open advisor
        <ArrowRight size={14} strokeWidth={1.75} aria-hidden />
      </Link>
    </section>
  );
}

function formatImpact(usd: number): string {
  if (usd >= 1000) return `${(usd / 1000).toFixed(1)}k`;
  return Math.round(usd).toLocaleString();
}
