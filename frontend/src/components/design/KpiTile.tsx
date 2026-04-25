export function KpiTile({
  label,
  value,
  delta,
  urgent = false,
}: {
  label: string;
  value: string;
  delta?: { text: string; direction: "pos" | "neg" };
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
    </div>
  );
}
