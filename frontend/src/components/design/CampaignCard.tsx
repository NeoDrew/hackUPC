import Link from "next/link";

import type { Campaign } from "@/lib/api";
import { formatCurrency } from "@/lib/format";

function healthTone(score: number | null | undefined): string {
  if (score == null) return "neutral";
  if (score >= 70) return "good";
  if (score >= 40) return "watch";
  return "bad";
}

export function CampaignCard({ campaign }: { campaign: Campaign }) {
  const m = campaign.metrics;
  const score = m?.health ?? null;
  const tone = healthTone(score);
  const bands: ("scale" | "watch" | "rescue" | "cut")[] = [
    "scale",
    "watch",
    "rescue",
    "cut",
  ];

  return (
    <Link
      href={`/campaigns/${campaign.campaign_id}`}
      prefetch={false}
      className={`campaign-card tone-${tone}`}
      aria-label={`Open ${campaign.app_name} (${campaign.primary_theme}) campaign`}
    >
      <header className="campaign-card-head">
        <div className="campaign-card-title">
          <span className="campaign-card-app">{campaign.app_name}</span>
          <span className="campaign-card-theme">{campaign.primary_theme}</span>
        </div>
        <span className={`campaign-card-health tone-${tone}`} title="Composite health (0–100)">
          {score ?? "—"}
        </span>
      </header>
      <div className="campaign-card-spend">
        {m ? formatCurrency(m.total_spend_usd, { compact: true }) : "—"}
      </div>
      <div className="campaign-card-bands" aria-label="Band breakdown">
        {bands.map((b) => {
          const n = (m?.[b] as number) ?? 0;
          return (
            <span key={b} className={`campaign-band band-${b}`}>
              <span className="campaign-band-dot" aria-hidden />
              <span className="campaign-band-count">{n}</span>
            </span>
          );
        })}
      </div>
    </Link>
  );
}
