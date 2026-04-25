export interface BriefField {
  label: string;
  value: string;
}

export function BriefPanel({
  fields,
  rationale,
}: {
  fields: BriefField[];
  rationale: string[];
}) {
  return (
    <div
      className="col gap-4"
      style={{
        background: "var(--bg-1)",
        border: "1px solid var(--line)",
        borderRadius: 12,
        padding: 18,
        boxShadow: "var(--shadow-1)",
      }}
    >
      <header className="col gap-1">
        <h3 className="t-section">Creative brief</h3>
        <p className="t-body muted">
          Attributes templated from the twin winner. Swap in Gemma output once the LLM is wired.
        </p>
      </header>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
          gap: 8,
        }}
      >
        {fields.map((f) => (
          <div key={f.label} className="meta-pill">
            <span className="k">{f.label}</span>
            <span className="v">{f.value}</span>
          </div>
        ))}
      </div>

      <div className="col gap-2">
        <span className="t-overline">Why these choices</span>
        <ul className="col gap-1" style={{ listStyle: "none", padding: 0, margin: 0 }}>
          {rationale.map((r, i) => (
            <li key={i} className="row gap-2" style={{ alignItems: "flex-start" }}>
              <span style={{ color: "var(--status-top)", marginTop: 2 }}>✓</span>
              <span className="t-body">{r}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
