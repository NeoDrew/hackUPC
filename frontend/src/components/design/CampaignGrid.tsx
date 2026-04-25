import { listCampaignsWithMetrics } from "@/lib/campaignScope";
import { CampaignCard } from "./CampaignCard";

export async function CampaignGrid({
  advertiserId,
  start,
  end,
}: {
  advertiserId: number;
  start?: string;
  end?: string;
}) {
  const campaigns = await listCampaignsWithMetrics(advertiserId, { start, end });
  if (campaigns.length === 0) {
    return (
      <section className="campaign-grid empty">
        <p className="t-body muted">No campaigns under this advertiser.</p>
      </section>
    );
  }
  return (
    <section className="campaign-grid" aria-label="Campaigns">
      <header className="campaign-grid-head">
        <h2 className="t-section">Campaigns</h2>
        <p className="t-body muted">
          Ranked by composite health. Click a campaign to drill into its
          creatives.
        </p>
      </header>
      <div className="campaign-grid-list">
        {campaigns.map((c) => (
          <CampaignCard key={c.campaign_id} campaign={c} />
        ))}
      </div>
    </section>
  );
}
