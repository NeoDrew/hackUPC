export interface WinningPattern {
  lift: string;
  prevalence: string;
  trait: string;
  what: string;
}

export function WinningPatternsCard({ patterns }: { patterns: WinningPattern[] }) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
        gap: 12,
      }}
    >
      {patterns.map((p, i) => (
        <div key={i} className="pattern-card">
          <div className="row between center">
            <span className="lift">{p.lift}</span>
            <span className="prevalence">{p.prevalence}</span>
          </div>
          <span className="trait">{p.trait}</span>
          <span className="what">{p.what}</span>
        </div>
      ))}
    </div>
  );
}
