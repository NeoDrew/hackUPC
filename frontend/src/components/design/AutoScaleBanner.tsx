import Link from "next/link";
import { Sparkles } from "lucide-react";

import { api } from "@/lib/api";
import { formatCurrency } from "@/lib/format";

/**
 * Past-tense report of what Smadex auto-scaled this week. Top performers
 * don't need a human in the loop — the system already reallocated budget
 * toward the highest-confidence winners. The banner shows that work was
 * done so the marketer trusts the system without needing to approve
 * every spend change.
 *
 * For the demo, the count is the live Scale-band size and the dollar
 * lift is a deterministic function of total spend (5% reallocation
 * stub). When Andrew wires real auto-scale endpoints, swap this for
 * the live aggregate.
 */
export async function AutoScaleBanner() {
  const counts = await api.tabCounts().catch(() => null);
  const kpis = await api.portfolioKpis().catch(() => null);
  const winnerCount = Math.min(5, counts?.scale ?? 0);
  if (winnerCount === 0) return null;

  // 5% of weekly spend as the auto-scale reallocation stub. Looks
  // plausible for the demo; real allocation will be bandit-driven.
  const weeklySpend = (kpis?.total_spend_usd ?? 0) / 75 * 7;
  const reallocated = weeklySpend * 0.05;

  return (
    <aside className="auto-scale-banner" role="status">
      <span className="auto-scale-icon" aria-hidden>
        <Sparkles size={14} strokeWidth={1.75} />
      </span>
      <div className="auto-scale-body">
        <strong className="auto-scale-title">
          Smadex auto-scaled {winnerCount} winners this week
        </strong>
        <span className="auto-scale-sub">
          +{formatCurrency(reallocated, { compact: true })} reallocated to top performers · no action needed
        </span>
      </div>
      <Link
        href="/?tab=scale"
        prefetch={false}
        className="auto-scale-link"
      >
        See what we did →
      </Link>
    </aside>
  );
}
