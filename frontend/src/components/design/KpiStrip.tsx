import { api } from "@/lib/api";
import { KpiTile } from "@/components/design/KpiTile";
import { formatCount, formatCurrency, formatPct, formatRoas } from "@/lib/format";

export async function KpiStrip({
  start,
  end,
  advertiserId,
  campaignId,
}: {
  start?: string;
  end?: string;
  advertiserId?: number;
  campaignId?: number;
}) {
  const kpis = await api.portfolioKpis({
    start,
    end,
    advertiser_id: advertiserId,
    campaign_id: campaignId,
  });
  return (
    <section className="kpi-strip">
      <KpiTile label="ROAS" value={formatRoas(kpis.roas)} series={kpis.roas_series} />
      <KpiTile
        label="Spend"
        value={formatCurrency(kpis.total_spend_usd, { compact: true })}
        series={kpis.spend_series}
      />
      <KpiTile label="CTR" value={formatPct(kpis.ctr, 2)} series={kpis.ctr_series} />
      <KpiTile label="CVR" value={formatPct(kpis.cvr, 1)} series={kpis.cvr_series} />
      <KpiTile
        label="Need attention"
        value={formatCount(kpis.attention_count)}
        urgent
      />
    </section>
  );
}
