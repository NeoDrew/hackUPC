import Link from "next/link";

import { api } from "@/lib/api";
import { CreativeList } from "./CreativeList";

export async function CampaignList({
  advertiserId,
}: {
  advertiserId: number;
}) {
  const campaigns = await api.listCampaigns(advertiserId);
  if (campaigns.length === 0) return <p>No campaigns.</p>;
  return (
    <ul>
      {campaigns.map((c) => (
        <li key={c.campaign_id}>
          <strong>
            <Link href={`/campaigns/${c.campaign_id}`}>{c.app_name}</Link>
          </strong>{" "}
          <small>
            ({c.objective} · {c.primary_theme} · {c.target_os} ·{" "}
            {c.country_list.join(", ")} · ${c.daily_budget_usd}/day)
          </small>
          <CreativeList campaignId={c.campaign_id} />
        </li>
      ))}
    </ul>
  );
}
