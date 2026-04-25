import type { CreativeDetail } from "@/lib/api";
import { formatCount, formatCurrency, formatRoas } from "@/lib/format";

export function PerformanceGrid({ creative }: { creative: CreativeDetail }) {
  const data = creative as unknown as Record<string, number | undefined>;
  const cells: Array<{ label: string; value: string }> = [
    { label: "ROAS", value: formatRoas(data.overall_roas ?? 0) },
    { label: "Spend", value: formatCurrency(data.total_spend_usd ?? 0, { compact: true }) },
    { label: "Revenue", value: formatCurrency(data.total_revenue_usd ?? 0, { compact: true }) },
    { label: "Impressions", value: formatCount(data.total_impressions ?? 0, { compact: true }) },
    { label: "Clicks", value: formatCount(data.total_clicks ?? 0, { compact: true }) },
    { label: "Conversions", value: formatCount(data.total_conversions ?? 0, { compact: true }) },
  ];
  return (
    <div className="perf-grid">
      {cells.map((c) => (
        <div key={c.label} className="cell">
          <span className="label">{c.label}</span>
          <span className="value">{c.value}</span>
        </div>
      ))}
    </div>
  );
}
