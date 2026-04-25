import Link from "next/link";

import { api } from "@/lib/api";
import { creativeImageUrl } from "@/lib/assetUrl";

export async function CreativeList({ campaignId }: { campaignId: number }) {
  const creatives = await api.listCreativesForCampaign(campaignId);
  if (creatives.length === 0) return <p>No creatives.</p>;
  return (
    <ul data-list="creatives">
      {creatives.map((c) => (
        <li key={c.creative_id}>
          <Link href={`/creatives/${c.creative_id}`}>
            <img
              src={creativeImageUrl(c.creative_id)}
              alt={`creative ${c.creative_id}`}
              width={64}
              height={64}
            />
            <span>
              {c.creative_id} · {c.format} · {c.theme}
              {c.creative_status ? ` · ${c.creative_status}` : null}
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}
