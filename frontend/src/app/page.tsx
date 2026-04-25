import { api } from "@/lib/api";
import { KpiTile } from "@/components/design/KpiTile";
import { CreativeTable } from "@/components/design/CreativeTable";
import { formatCount, formatCurrency, formatPct, formatRoas } from "@/lib/format";
import { TAB_TO_STATUS, type TabKey } from "@/lib/status";

const TAB_HEADINGS: Record<TabKey, { heading: string; subcopy: string }> = {
  scale: {
    heading: "Creatives recommended to scale",
    subcopy: "Top performers. Increase spend or replicate the winning attributes.",
  },
  watch: {
    heading: "Stable creatives to watch",
    subcopy: "Maintain current spend; monitor for fatigue or sudden drops.",
  },
  rescue: {
    heading: "Losing performance: rescue or replace",
    subcopy: "These creatives have declining CTR/CVR. Drill in to find the twin and generate a variant.",
  },
  cut: {
    heading: "Underperformers: cut or rework",
    subcopy: "Below cohort baseline since launch. Pause or fundamentally redesign.",
  },
  explore: {
    heading: "Explore",
    subcopy: "All creatives.",
  },
};

interface CockpitSearchParams {
  tab?: string;
  limit?: string;
}

const PAGE_SIZE = 100;

export default async function Cockpit(props: {
  searchParams: Promise<CockpitSearchParams>;
}) {
  const { tab: rawTab, limit: rawLimit } = await props.searchParams;
  const tab = normalizeTab(rawTab);
  const limit = clampLimit(rawLimit);
  const [kpis, listing] = await Promise.all([
    api.portfolioKpis(),
    api.listCreatives({ tab, limit }),
  ]);
  const headings = TAB_HEADINGS[tab];
  const total = listing.total;
  const shown = listing.rows.length;
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
      <CreativeTable
        rows={listing.rows}
        heading={headings.heading}
        subcopy={headings.subcopy}
        from={tab}
        footer={
          shown < total ? (
            <ShowMoreFooter
              tab={tab}
              shown={shown}
              total={total}
              currentLimit={limit}
            />
          ) : (
            <p className="t-micro muted" style={{ padding: "10px 16px" }}>
              Showing all {total} creatives in this view.
            </p>
          )
        }
      />
    </>
  );
}

function ShowMoreFooter({
  tab,
  shown,
  total,
  currentLimit,
}: {
  tab: TabKey;
  shown: number;
  total: number;
  currentLimit: number;
}) {
  const next = Math.min(currentLimit + PAGE_SIZE, total);
  const href = `/?tab=${tab}&limit=${next}`;
  return (
    <div
      className="row between center"
      style={{ padding: "10px 16px", borderTop: "1px solid var(--line-soft)" }}
    >
      <span className="t-micro muted">
        Showing {shown} of {total}
      </span>
      <a className="btn dense" href={href}>
        Show {Math.min(PAGE_SIZE, total - shown)} more
      </a>
    </div>
  );
}

function clampLimit(raw: string | undefined): number {
  const n = raw ? Number(raw) : PAGE_SIZE;
  if (!Number.isFinite(n) || n < 1) return PAGE_SIZE;
  return Math.min(2000, Math.max(PAGE_SIZE, n));
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
