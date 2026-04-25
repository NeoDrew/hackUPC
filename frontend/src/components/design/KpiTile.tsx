import { Sparkline } from "./Sparkline";

export function KpiTile({
  label,
  value,
  delta,
  series,
  urgent = false,
}: {
  label: string;
  value: string;
  delta?: { text: string; direction: "pos" | "neg" };
  series?: number[];
  urgent?: boolean;
}) {
  return (
    <div className={`kpi-tile${urgent ? " urgent" : ""}`}>
      <span className="kpi-label">{label}</span>
      <span className="kpi-value">{value}</span>
      {delta ? (
        <span className={`kpi-delta ${delta.direction}`}>{delta.text}</span>
      ) : (
        <span className="kpi-delta" style={{ visibility: "hidden" }}>
          –
        </span>
      )}
      {series && series.length > 1 ? (
        <div className="kpi-spark">
          <Sparkline series={series} width={220} height={28} />
        </div>
      ) : null}
    </div>
  );
}
