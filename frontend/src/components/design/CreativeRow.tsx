import Link from "next/link";

import type { CreativeRow as CreativeRowT } from "@/lib/api";
import { creativeImageUrl } from "@/lib/assetUrl";
import { formatCount, formatCurrency, formatDays, formatPct, formatRoas } from "@/lib/format";
import { Sparkline } from "./Sparkline";
import { HealthRing } from "./HealthRing";

export function CreativeRow({ row }: { row: CreativeRowT }) {
  return (
    <Link href={`/creatives/${row.creative_id}`} className="creative-row" prefetch={false}>
      <div className="thumb">
        <img src={creativeImageUrl(row.creative_id)} alt="" loading="lazy" />
      </div>
      <div className="col">
        <div className="headline">{row.headline || `Creative ${row.creative_id}`}</div>
        <div className="meta">
          {row.advertiser_name} · {row.vertical} · {row.format} · #{row.creative_id}
        </div>
      </div>
      <div className="num-cell">{formatPct(row.ctr)}</div>
      <div className="num-cell">{formatPct(row.cvr)}</div>
      <div className="num-cell">{formatRoas(row.roas)}</div>
      <div className="num-cell">{formatCurrency(row.spend_usd, { compact: true })}</div>
      <div className="num-cell">{formatDays(row.days_active)}</div>
      <div className="num-cell" style={{ display: "flex", justifyContent: "flex-end", alignItems: "center" }}>
        <Sparkline series={row.sparkline} fatigueDay={row.fatigue_day} width={88} height={22} />
      </div>
      <div className="health-cell">
        <HealthRing value={row.health} size={20} showLabel={false} />
      </div>
    </Link>
  );
}
