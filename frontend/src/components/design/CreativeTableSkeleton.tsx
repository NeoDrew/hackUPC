/** Mirrors the live CreativeTable shape so a swap mid-navigation is
 * a no-op visually. Renders the same grid columns, with shimmer blocks
 * sized roughly like the real cells. */
export function CreativeTableSkeleton({
  rows = 8,
  heading,
  subcopy,
}: {
  rows?: number;
  heading?: string;
  subcopy?: string;
}) {
  return (
    <section className="col gap-3" aria-busy>
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
        {Array.from({ length: rows }).map((_, i) => (
          <SkeletonRow key={i} />
        ))}
      </div>
    </section>
  );
}

function SkeletonRow() {
  return (
    <div className="creative-row creative-row-skeleton">
      <div className="thumb">
        <div className="skeleton skeleton-thumb" />
      </div>
      <div className="col gap-2" style={{ paddingRight: 32 }}>
        <div className="skeleton" style={{ height: 14, width: "70%" }} />
        <div className="skeleton" style={{ height: 10, width: "55%" }} />
      </div>
      <SkeletonNum />
      <SkeletonNum />
      <SkeletonNum />
      <SkeletonNum />
      <SkeletonNum width={36} />
      <div style={{ display: "flex", justifyContent: "flex-end" }}>
        <div className="skeleton" style={{ height: 22, width: 88 }} />
      </div>
      <div style={{ display: "flex", justifyContent: "flex-end" }}>
        <div className="skeleton" style={{ height: 20, width: 20, borderRadius: 999 }} />
      </div>
    </div>
  );
}

function SkeletonNum({ width = 50 }: { width?: number }) {
  return (
    <div className="num-cell" style={{ display: "flex", justifyContent: "flex-end" }}>
      <div className="skeleton" style={{ height: 12, width }} />
    </div>
  );
}
