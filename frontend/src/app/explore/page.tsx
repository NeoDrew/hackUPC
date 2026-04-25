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

interface ExploreSearchParams {
  vertical?: string;
  format?: string;
  status?: string;
  sort?: string;
  desc?: string;
}

export default async function ExplorePage(props: {
  searchParams: Promise<ExploreSearchParams>;
}) {
  const params = await props.searchParams;

  const listArgs = {
    vertical: params.vertical,
    format: params.format,
    status: params.status,
    sort: params.sort,
    desc: params.desc !== "false",
  };
  const rows = await api.listCreatives(listArgs);

  const buildHref = (paramKey: string, value: string | undefined) => {
    const next: Record<string, string | undefined> = { ...params };
    if (value === undefined) delete next[paramKey];
    else next[paramKey] = value;
    const qp = new URLSearchParams();
    for (const [k, v] of Object.entries(next)) {
      if (v !== undefined && v !== "") qp.set(k, v);
    }
    const s = qp.toString();
    return `/explore${s ? `?${s}` : ""}`;
  };

  return (
    <section className="col gap-4" style={{ paddingTop: 16 }}>
      <header className="col gap-1">
        <h1 className="t-page">Explore</h1>
        <p className="t-body muted">
          Cross-slice all {rows.length} active creatives by vertical, format, and status.
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

      <AggregatesStrip rows={rows} />

      <CreativeTable rows={rows} />
    </section>
  );
}
