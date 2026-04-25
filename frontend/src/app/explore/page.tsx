import { Suspense } from "react";

import { api } from "@/lib/api";
import { AggregatesStrip } from "@/components/design/AggregatesStrip";
import { CreativeTable } from "@/components/design/CreativeTable";
import { CreativeTableSkeleton } from "@/components/design/CreativeTableSkeleton";
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

  const buildHref = (paramKey: string, value: string | undefined) => {
    const next: Record<string, string | undefined> = { ...params };
    if (value === undefined) delete next[paramKey];
    else next[paramKey] = value;
    delete next.limit;
    const qp = new URLSearchParams();
    for (const [k, v] of Object.entries(next)) {
      if (v !== undefined && v !== "") qp.set(k, v);
    }
    const s = qp.toString();
    return `/explore${s ? `?${s}` : ""}`;
  };

  const suspenseKey = `${params.vertical ?? ""}|${params.format ?? ""}|${params.status ?? ""}|${sort ?? ""}|${desc ? "d" : "a"}|${limit}`;

  return (
    <section className="col gap-4" style={{ paddingTop: 16 }}>
      <header className="col gap-1">
        <h1 className="t-page">Explore</h1>
        <p className="t-body muted">
          Cross-slice creatives by vertical, format, and status.
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

      <Suspense
        key={suspenseKey}
        fallback={
          <>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(7, minmax(0, 1fr))",
                gap: 10,
                padding: 12,
                background: "var(--bg-1)",
                border: "1px solid var(--line)",
                borderRadius: 10,
              }}
            >
              {Array.from({ length: 7 }).map((_, i) => (
                <div className="col gap-1" key={i}>
                  <div className="skeleton" style={{ height: 11, width: 60 }} />
                  <div className="skeleton" style={{ height: 18, width: 70 }} />
                </div>
              ))}
            </div>
            <CreativeTableSkeleton rows={10} />
          </>
        }
      >
        <ExploreTable params={params} sort={sort} desc={desc} limit={limit} />
      </Suspense>
    </section>
  );
}

async function ExploreTable({
  params,
  sort,
  desc,
  limit,
}: {
  params: ExploreSearchParams;
  sort?: string;
  desc: boolean;
  limit: number;
}) {
  const listing = await api.listCreatives({
    vertical: params.vertical,
    format: params.format,
    status: params.status,
    sort,
    desc,
    limit,
  });
  const total = listing.total;
  const shown = listing.rows.length;

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
    <>
      <AggregatesStrip rows={listing.rows} />
      <CreativeTable
        rows={listing.rows}
        from="explore"
        sortState={{
          sort,
          desc,
          buildHref: (key: string) => {
            const next: Record<string, string | undefined> = { ...params };
            delete next.limit;
            if (sort !== key) {
              next.sort = key;
              next.desc = "false";
            } else if (!desc) {
              next.sort = key;
              next.desc = "true";
            } else {
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
    </>
  );
}

function clampLimit(raw: string | undefined): number {
  const n = raw ? Number(raw) : PAGE_SIZE;
  if (!Number.isFinite(n) || n < 1) return PAGE_SIZE;
  return Math.min(2000, Math.max(PAGE_SIZE, n));
}
