import { api } from "@/lib/api";
import { AggregatesStrip } from "@/components/design/AggregatesStrip";
import { CreativeTable } from "@/components/design/CreativeTable";
import { FilterChipGroup } from "@/components/design/FilterChipGroup";

const VERTICALS = [
  "ecommerce",
  "entertainment",
  "fintech",
  "food_delivery",
  "gaming",
  "travel",
];
const FORMATS = ["banner", "interstitial", "native", "playable", "rewarded_video"];
const STATUSES: Array<{ value: string; label: string }> = [
  { value: "top_performer", label: "Scale" },
  { value: "stable", label: "Watch" },
  { value: "fatigued", label: "Rescue" },
  { value: "underperformer", label: "Cut" },
];

const PAGE_SIZE = 100;

const SORTABLE = new Set(["ctr", "cvr", "roas", "spend_usd", "days_active", "health"]);

interface ExploreSearchParams {
  vertical?: string;
  format?: string;
  status?: string;
  sort?: string;
  desc?: string;
  limit?: string;
}

export default async function ExplorePage(props: {
  searchParams: Promise<ExploreSearchParams>;
}) {
  const params = await props.searchParams;
  const limit = clampLimit(params.limit);
  const sort = params.sort && SORTABLE.has(params.sort) ? params.sort : undefined;
  const desc = params.desc !== "false";

  const listArgs = {
    vertical: params.vertical,
    format: params.format,
    status: params.status,
    sort,
    desc,
    limit,
  };
  const listing = await api.listCreatives(listArgs);
  const total = listing.total;
  const shown = listing.rows.length;

  const buildHref = (paramKey: string, value: string | undefined) => {
    const next: Record<string, string | undefined> = { ...params };
    if (value === undefined) delete next[paramKey];
    else next[paramKey] = value;
    // Reset pagination when filters change.
    delete next.limit;
    const qp = new URLSearchParams();
    for (const [k, v] of Object.entries(next)) {
      if (v !== undefined && v !== "") qp.set(k, v);
    }
    const s = qp.toString();
    return `/explore${s ? `?${s}` : ""}`;
  };

  const showMoreHref = (() => {
    const next: Record<string, string | undefined> = { ...params };
    next.limit = String(Math.min(limit + PAGE_SIZE, total));
    const qp = new URLSearchParams();
    for (const [k, v] of Object.entries(next)) {
      if (v !== undefined && v !== "") qp.set(k, v);
    }
    return `/explore?${qp.toString()}`;
  })();

  return (
    <section className="col gap-4" style={{ paddingTop: 16 }}>
      <header className="col gap-1">
        <h1 className="t-page">Explore</h1>
        <p className="t-body muted">
          Cross-slice {shown} of {total} active creatives by vertical, format, and status.
        </p>
      </header>

      <div className="col gap-4">
        <FilterChipGroup
          label="Vertical"
          paramKey="vertical"
          options={VERTICALS.map((v) => ({ value: v, label: v }))}
          currentValue={params.vertical}
          buildHref={buildHref}
        />
        <FilterChipGroup
          label="Format"
          paramKey="format"
          options={FORMATS.map((v) => ({ value: v, label: v.replace("_", " ") }))}
          currentValue={params.format}
          buildHref={buildHref}
        />
        <FilterChipGroup
          label="Status"
          paramKey="status"
          options={STATUSES}
          currentValue={params.status}
          buildHref={buildHref}
        />
      </div>

      <AggregatesStrip rows={listing.rows} />

      <CreativeTable
        rows={listing.rows}
        from="explore"
        sortState={{
          sort,
          desc,
          buildHref: (key: string) => {
            // 3-click cycle: off → asc → desc → off
            const next: Record<string, string | undefined> = { ...params };
            delete next.limit; // restart pagination on re-sort
            if (sort !== key) {
              next.sort = key;
              next.desc = "false";
            } else if (!desc) {
              next.sort = key;
              next.desc = "true";
            } else {
              // Currently descending → fall off back to default.
              delete next.sort;
              delete next.desc;
            }
            const qp = new URLSearchParams();
            for (const [k, v] of Object.entries(next)) {
              if (v !== undefined && v !== "") qp.set(k, v);
            }
            return `/explore${qp.toString() ? `?${qp.toString()}` : ""}`;
          },
        }}
        footer={
          shown < total ? (
            <div
              className="row between center"
              style={{ padding: "10px 16px", borderTop: "1px solid var(--line-soft)" }}
            >
              <span className="t-micro muted">
                Showing {shown} of {total}
              </span>
              <a className="btn dense" href={showMoreHref}>
                Show {Math.min(PAGE_SIZE, total - shown)} more
              </a>
            </div>
          ) : (
            <p className="t-micro muted" style={{ padding: "10px 16px" }}>
              Showing all {total} matching creatives.
            </p>
          )
        }
      />
    </section>
  );
}

function clampLimit(raw: string | undefined): number {
  const n = raw ? Number(raw) : PAGE_SIZE;
  if (!Number.isFinite(n) || n < 1) return PAGE_SIZE;
  return Math.min(2000, Math.max(PAGE_SIZE, n));
}
