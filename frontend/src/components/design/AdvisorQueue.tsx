import {
  listRecommendations,
  type RecommendationsScope,
  type SliceRecommendation,
} from "@/lib/api";
import { RecommendationCard } from "./RecommendationCard";

/**
 * Full-width slice-advisor queue. Server component — fetches the ranked
 * list once and hands each row to <RecommendationCard /> (client component
 * for the interactive Apply / Snooze / Dismiss buttons).
 *
 * Intentionally simple: no infinite scroll, no virtualisation. The
 * backend caps at 50 per advertiser and the demo never scrolls past the
 * first dozen.
 */
export async function AdvisorQueue({
  advertiserId,
  campaignId,
  severity,
  actionType,
}: {
  advertiserId?: number;
  campaignId?: number;
  severity?: SliceRecommendation["severity"];
  actionType?: SliceRecommendation["action_type"];
}) {
  const scope: RecommendationsScope = {};
  if (advertiserId) scope.advertiser_id = advertiserId;
  if (campaignId) scope.campaign_id = campaignId;
  if (severity) scope.severity = severity;
  if (actionType) scope.action_type = actionType;

  const data = await listRecommendations(scope).catch(() => null);

  if (!data || data.recommendations.length === 0) {
    return (
      <section className="advisor-queue empty">
        <p className="t-body muted">
          Advisor has nothing to surface right now — your portfolio looks
          clean.
        </p>
      </section>
    );
  }

  return (
    <section
      className="advisor-queue"
      aria-label="Slice-level advisor recommendations"
    >
      <header className="advisor-queue-head">
        <h2 className="t-section">
          {data.recommendations.length}{" "}
          {data.recommendations.length === 1 ? "action" : "actions"} ready
        </h2>
        <p className="t-body muted">
          est. ${formatTotal(data.total_daily_impact_usd)}/day at stake.{" "}
          {summariseSeverity(data.counts_by_severity)}
        </p>
      </header>
      <ol className="advisor-queue-list">
        {data.recommendations.map((rec) => (
          <RecommendationCard
            key={rec.recommendation_id}
            rec={rec}
            showImpactBar
            totalDailyImpactUsd={data.total_daily_impact_usd}
          />
        ))}
      </ol>
    </section>
  );
}

function formatTotal(usd: number): string {
  if (usd >= 1000) return `${(usd / 1000).toFixed(1)}k`;
  return Math.round(usd).toLocaleString();
}

function summariseSeverity(counts: Record<string, number>): string {
  const c = counts.critical ?? 0;
  const w = counts.warning ?? 0;
  const o = counts.opportunity ?? 0;
  return `${c} critical · ${w} warning · ${o} opportunity`;
}
