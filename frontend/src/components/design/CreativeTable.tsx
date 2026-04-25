import type { CreativeRow as CreativeRowT } from "@/lib/api";
import { CreativeRow } from "./CreativeRow";

export function CreativeTable({
  rows,
  heading,
  subcopy,
}: {
  rows: CreativeRowT[];
  heading?: string;
  subcopy?: string;
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
          <span className="num-cell">CTR</span>
          <span className="num-cell">CVR</span>
          <span className="num-cell">ROAS</span>
          <span className="num-cell">Spend</span>
          <span className="num-cell">Days</span>
          <span className="num-cell">7d trend</span>
          <span className="num-cell">Health</span>
        </div>
        {rows.length === 0 ? (
          <div style={{ padding: 32, textAlign: "center" }} className="t-body muted">
            No creatives in this view.
          </div>
        ) : (
          rows.map((row) => <CreativeRow key={row.creative_id} row={row} />)
        )}
      </div>
    </section>
  );
}
