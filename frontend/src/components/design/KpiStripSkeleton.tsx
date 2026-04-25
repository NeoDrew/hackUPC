/** Mirrors the live <section className="kpi-strip"> shape so a swap mid-
 * navigation is a no-op visually. */
export function KpiStripSkeleton() {
  const labels = ["ROAS", "Spend", "CTR", "CVR", "Need attention"];
  return (
    <section className="kpi-strip" aria-busy>
      {labels.map((label, i) => (
        <div
          key={label}
          className={`kpi-tile${i === labels.length - 1 ? " urgent" : ""}`}
        >
          <span className="kpi-label">{label}</span>
          <span className="kpi-value">
            <span className="skeleton" style={{ height: 30, width: 78, display: "inline-block" }} />
          </span>
          <span className="kpi-delta" style={{ visibility: "hidden" }}>–</span>
        </div>
      ))}
    </section>
  );
}
