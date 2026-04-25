import type { CreativeRow } from "@/lib/api";
import { formatCount, formatCurrency, formatPct, formatRoas } from "@/lib/format";

export function AggregatesStrip({ rows }: { rows: CreativeRow[] }) {
  if (rows.length === 0) {
    return <div className="t-body muted">No creatives in the current filter.</div>;
  }

  const impressions = rows.reduce((a, r) => a + (r.impressions || 0), 0);
  const clicks = rows.reduce((a, r) => a + (r.clicks || 0), 0);
  const conversions = rows.reduce((a, r) => a + (r.conversions || 0), 0);
  const spend = rows.reduce((a, r) => a + (r.spend_usd || 0), 0);
  const revenue = rows.reduce((a, r) => a + (r.revenue_usd || 0), 0);
  const ctr = impressions ? clicks / impressions : 0;
  const cvr = clicks ? conversions / clicks : 0;
  const roas = spend ? revenue / spend : 0;
  const avgHealth = rows.reduce((a, r) => a + (r.health || 0), 0) / rows.length;

  const cells: Array<{ label: string; value: string }> = [
    { label: "Creatives", value: formatCount(rows.length) },
    { label: "Avg health", value: Math.round(avgHealth).toString() },
    { label: "Impressions", value: formatCount(impressions, { compact: true }) },
    { label: "CTR", value: formatPct(ctr) },
    { label: "CVR", value: formatPct(cvr, 1) },
    { label: "Spend", value: formatCurrency(spend, { compact: true }) },
    { label: "ROAS", value: formatRoas(roas) },
  ];

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: `repeat(${cells.length}, minmax(0, 1fr))`,
        gap: 10,
        padding: 12,
        background: "var(--bg-1)",
        border: "1px solid var(--line)",
        borderRadius: 10,
      }}
    >
      {cells.map((c) => (
        <div key={c.label} className="col gap-1">
          <span className="t-overline">{c.label}</span>
          <span className="num" style={{ fontSize: 18, fontWeight: 600 }}>
            {c.value}
          </span>
        </div>
      ))}
    </div>
  );
}
