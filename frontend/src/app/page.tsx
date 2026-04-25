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
  sort?: string;
  desc?: string;
}

const PAGE_SIZE = 100;
const SORTABLE = new Set(["ctr", "cvr", "roas", "spend_usd", "days_active", "health"]);

export default async function Cockpit(props: {
  searchParams: Promise<CockpitSearchParams>;
}) {
  const params = await props.searchParams;
  const tab = normalizeTab(params.tab);
  const limit = clampLimit(params.limit);
  const sort = params.sort && SORTABLE.has(params.sort) ? params.sort : undefined;
  const desc = params.desc !== "false";
  const [kpis, listing] = await Promise.all([
    api.portfolioKpis(),
    api.listCreatives({ tab, limit, sort, desc }),
  ]);
  const headings = TAB_HEADINGS[tab];
  const total = listing.total;
  const shown = listing.rows.length;
  const buildSortHref = (key: string) => {
    const next: Record<string, string> = { tab };
    if (limit !== PAGE_SIZE) next.limit = String(limit);
    next.sort = key;
    if (sort === key) {
      // Toggle direction if clicking the active column.
      next.desc = desc ? "false" : "true";
    } else {
      next.desc = "true";
    }
    const qp = new URLSearchParams(next).toString();
    return `/?${qp}`;
  };
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
        sortState={{ sort, desc, buildHref: buildSortHref }}
        footer={
          shown < total ? (
            <ShowMoreFooter
              tab={tab}
              shown={shown}
              total={total}
              currentLimit={limit}
              sort={sort}
              desc={desc}
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
  sort,
  desc,
}: {
  tab: TabKey;
  shown: number;
  total: number;
  currentLimit: number;
  sort?: string;
  desc: boolean;
}) {
  const next = Math.min(currentLimit + PAGE_SIZE, total);
  const params: Record<string, string> = { tab, limit: String(next) };
  if (sort) {
    params.sort = sort;
    params.desc = desc ? "true" : "false";
  }
  const href = `/?${new URLSearchParams(params).toString()}`;
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
