import { formatPct, formatRoas } from "@/lib/format";

export interface LiftRow {
  label: string;
  base: number;
  projected: number;
  format: "pct" | "roas";
}

export function PredictedLift({ rows }: { rows: LiftRow[] }) {
  return (
    <div
      className="col gap-3"
      style={{
        background: "rgba(23, 124, 99, 0.06)",
        border: "1px solid rgba(23, 124, 99, 0.35)",
        borderLeft: "3px solid var(--status-top)",
        borderRadius: 10,
        padding: 16,
      }}
    >
      <header className="row between center">
        <h3 className="t-section" style={{ color: "var(--status-top)" }}>
          Predicted lift
        </h3>
        <span className="t-micro muted">Templated projection — not yet model-backed</span>
      </header>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
          gap: 12,
        }}
      >
        {rows.map((r) => {
          const display = (v: number) => (r.format === "pct" ? formatPct(v) : formatRoas(v));
          const pct = r.base > 0 ? ((r.projected - r.base) / r.base) * 100 : 0;
          return (
            <div key={r.label} className="col gap-1" style={{ background: "var(--bg-1)", padding: 12, borderRadius: 8, border: "1px solid var(--line)" }}>
              <span className="t-overline">{r.label}</span>
              <div className="row gap-2 center">
                <span className="mono muted" style={{ fontSize: 13 }}>
                  {display(r.base)}
                </span>
                <span className="muted">→</span>
                <span className="mono" style={{ fontSize: 18, fontWeight: 600, color: "var(--status-top)" }}>
                  {display(r.projected)}
                </span>
              </div>
              <span className="chip-pos" style={{ width: "max-content" }}>
                {pct >= 0 ? "+" : ""}
                {pct.toFixed(0)}%
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
