import Link from "next/link";

import type { CreativeRow as CreativeRowT } from "@/lib/api";
import { CreativeRow } from "./CreativeRow";

export interface SortState {
  sort?: string;
  desc?: boolean;
  buildHref: (sort: string) => string;
}

const SORTABLE = [
  { key: "ctr", label: "CTR" },
  { key: "cvr", label: "CVR" },
  { key: "roas", label: "ROAS" },
  { key: "spend_usd", label: "Spend" },
  { key: "days_active", label: "Days" },
  { key: "health", label: "Health" },
] as const;

const SORT_LABEL_TO_KEY: Record<string, string> = Object.fromEntries(
  SORTABLE.map((s) => [s.label, s.key]),
);

export function CreativeTable({
  rows,
  heading,
  subcopy,
  from,
  footer,
  sortState,
}: {
  rows: CreativeRowT[];
  heading?: string;
  subcopy?: string;
  from?: string;
  footer?: React.ReactNode;
  sortState?: SortState;
}) {
  return (
    <section className="col gap-3">
      {heading ? (
        <header className="section-head">
          <div className="col gap-1">
            <h2 className="t-page">{heading}</h2>
            {subcopy ? <p className="t-body muted">{subcopy}</p> : null}
          </div>
        </header>
      ) : null}
      <div className="creative-table">
        <div className="creative-thead">
          <span></span>
          <span>Creative</span>
          <SortableHeader label="CTR" sortState={sortState} />
          <SortableHeader label="CVR" sortState={sortState} />
          <SortableHeader label="ROAS" sortState={sortState} />
          <SortableHeader label="Spend" sortState={sortState} />
          <SortableHeader label="Days" sortState={sortState} />
          <span className="num-cell">7d trend</span>
          <SortableHeader label="Health" sortState={sortState} />
        </div>
        {rows.length === 0 ? (
          <div style={{ padding: 32, textAlign: "center" }} className="t-body muted">
            No creatives in this view.
          </div>
        ) : (
          rows.map((row) => <CreativeRow key={row.creative_id} row={row} from={from} />)
        )}
      </div>
      {footer}
    </section>
  );
}

function SortableHeader({
  label,
  sortState,
}: {
  label: string;
  sortState?: SortState;
}) {
  const key = SORT_LABEL_TO_KEY[label];
  if (!sortState || !key) {
    return <span className="num-cell">{label}</span>;
  }
  const active = sortState.sort === key;
  const arrow = active ? (sortState.desc ? "▼" : "▲") : "";
  return (
    <Link
      href={sortState.buildHref(key)}
      className={`num-cell sortable-th${active ? " active" : ""}`}
      prefetch={false}
    >
      {label}
      {arrow ? <span className="sort-arrow">{arrow}</span> : null}
    </Link>
  );
}
