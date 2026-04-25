import { api } from "@/lib/api";
import { KpiTile } from "@/components/design/KpiTile";
import { CreativeTable } from "@/components/design/CreativeTable";
import { formatCount, formatCurrency, formatPct, formatRoas } from "@/lib/format";
import { TAB_TO_STATUS, type TabKey } from "@/lib/status";

const TAB_HEADINGS: Record<TabKey, { heading: string; subcopy: string }> = {
  scale: {
    heading: "Creatives recommended to scale",
    subcopy: "Top performers — increase spend or replicate the winning attributes.",
  },
  watch: {
    heading: "Stable creatives to watch",
    subcopy: "Maintain current spend; monitor for fatigue or sudden drops.",
  },
  rescue: {
    heading: "Creatives losing performance — rescue or replace",
    subcopy: "These creatives have declining CTR/CVR. Drill in to find the twin and generate a variant.",
  },
  cut: {
    heading: "Underperformers — cut or rework",
    subcopy: "Below cohort baseline since launch. Pause or fundamentally redesign.",
  },
  explore: {
    heading: "Explore",
    subcopy: "All creatives.",
  },
};

interface CockpitSearchParams {
  tab?: string;
}

export default async function Cockpit(props: {
  searchParams: Promise<CockpitSearchParams>;
}) {
  const { tab: rawTab } = await props.searchParams;
  const tab = normalizeTab(rawTab);
  const [kpis, rows] = await Promise.all([
    api.portfolioKpis(),
    api.listCreatives({ tab }),
  ]);
  const headings = TAB_HEADINGS[tab];
  return (
    <>
      <section className="kpi-strip">
        <KpiTile label="ROAS" value={formatRoas(kpis.roas)} />
        <KpiTile label="Spend" value={formatCurrency(kpis.total_spend_usd, { compact: true })} />
        <KpiTile label="CTR" value={formatPct(kpis.ctr, 2)} />
        <KpiTile label="CVR" value={formatPct(kpis.cvr, 1)} />
        <KpiTile
          label="Need attention"
          value={formatCount(kpis.attention_count)}
          urgent
        />
      </section>
      <CreativeTable rows={rows} heading={headings.heading} subcopy={headings.subcopy} />
    </>
  );
}

function normalizeTab(value: string | undefined): TabKey {
  if (value && (value === "scale" || value === "watch" || value === "rescue" || value === "cut")) {
    return value;
  }
  if (value === "explore") return "explore";
  return "scale";
}

// Make TAB_TO_STATUS importable for trees that might want it.
export { TAB_TO_STATUS };
