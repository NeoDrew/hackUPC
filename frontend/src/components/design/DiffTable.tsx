import type { TwinDiff } from "@/lib/api";

const DIRECTION_CLASS: Record<string, string> = {
  pos: "chip-pos",
  neg: "chip-neg",
  neu: "chip-neu",
};

const DIRECTION_SYMBOL: Record<string, string> = {
  pos: "↑",
  neg: "↓",
  neu: "→",
};

const IMPACT_BARS: Record<string, { className: string; bars: number }> = {
  high: { className: "high", bars: 3 },
  medium: { className: "medium", bars: 3 },
  low: { className: "low", bars: 3 },
};

export function DiffTable({ diffs }: { diffs: TwinDiff[] }) {
  if (diffs.length === 0) {
    return <p className="t-body muted">No attribute diffs between these creatives.</p>;
  }
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr 1fr 70px 80px",
        rowGap: 6,
        columnGap: 12,
        fontSize: 13,
        alignItems: "center",
      }}
    >
      <span className="t-th">Field</span>
      <span className="t-th">Yours</span>
      <span className="t-th">Twin</span>
      <span className="t-th">Direction</span>
      <span className="t-th">Impact</span>

      {diffs.map((d) => (
        <DiffRow key={d.field} diff={d} />
      ))}
    </div>
  );
}

function DiffRow({ diff }: { diff: TwinDiff }) {
  const dirClass = DIRECTION_CLASS[diff.direction] ?? "chip-neu";
  const symbol = DIRECTION_SYMBOL[diff.direction] ?? "→";
  const impact = IMPACT_BARS[diff.impact] ?? IMPACT_BARS.low;
  return (
    <>
      <span style={{ fontWeight: 500 }}>{prettyField(diff.field)}</span>
      <span className="mono">{formatValue(diff.source_value)}</span>
      <span className="mono">{formatValue(diff.twin_value)}</span>
      <span className={dirClass} style={{ justifySelf: "start" }}>
        {symbol}
      </span>
      <span className={`impact-bars ${impact.className}`}>
        {Array.from({ length: impact.bars }).map((_, i) => (
          <i key={i} />
        ))}
      </span>
    </>
  );
}

function prettyField(field: string): string {
  return field.replace(/_/g, " ");
}

function formatValue(v: unknown): string {
  if (v === null || v === undefined) return "–";
  if (typeof v === "number") return Number.isInteger(v) ? String(v) : v.toFixed(2);
  if (typeof v === "boolean") return v ? "yes" : "no";
  if (typeof v === "string") return v;
  return JSON.stringify(v);
}
