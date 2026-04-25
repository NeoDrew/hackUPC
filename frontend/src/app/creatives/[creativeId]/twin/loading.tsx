/** Route-level loading for the twin comparison. The twin page makes
 * three sequential awaits (twin lookup, source detail, winner detail)
 * plus a Gemma call for vision insight — easily 1-3 s on a warm Render.
 * Cold start adds another ~30 s; this skeleton means the user is never
 * staring at a frozen old page during the navigation, and the explicit
 * "Generating analysis…" banner tells them the latency is the LLM
 * doing work, not the app being broken. */
export default function TwinLoading() {
  return (
    <section
      className="col gap-5"
      style={{ paddingTop: 16, maxWidth: 1100, margin: "0 auto" }}
    >
      <div className="generating-banner" role="status" aria-live="polite">
        <span className="generating-dot" />
        <span>
          <strong>Generating analysis with Gemma 4</strong>
          <span className="generating-sub"> · finding the closest twin and diffing attributes</span>
        </span>
      </div>

      <header className="row between center" style={{ flexWrap: "wrap", gap: 12 }}>
        <div className="col gap-2">
          <div className="row center gap-3">
            <div className="skeleton" style={{ width: 130, height: 30, borderRadius: 8 }} />
            <div className="skeleton" style={{ width: 200, height: 26, borderRadius: 8 }} />
          </div>
          <div className="skeleton" style={{ height: 28, width: 480 }} />
          <div className="skeleton" style={{ height: 14, width: 220 }} />
        </div>
        <div className="row center gap-2">
          <div className="skeleton" style={{ width: 70, height: 32, borderRadius: 8 }} />
          <div className="skeleton" style={{ width: 180, height: 36, borderRadius: 8 }} />
        </div>
      </header>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 48px 1fr",
          gap: 16,
          alignItems: "stretch",
        }}
      >
        <TwinPanelSkeleton />
        <div />
        <TwinPanelSkeleton />
      </div>

      <section
        style={{
          background: "var(--bg-1)",
          border: "1px solid var(--line)",
          borderRadius: 12,
          padding: 16,
        }}
        className="col gap-2"
      >
        <div className="row center between">
          <div className="skeleton" style={{ height: 18, width: 280 }} />
          <span className="t-micro generating-pill">
            <span className="generating-dot" /> generating
          </span>
        </div>
        <div className="skeleton" style={{ height: 12, width: "85%" }} />
        <div className="skeleton" style={{ height: 12, width: "70%" }} />
      </section>

      <section className="col gap-2">
        <div className="skeleton" style={{ height: 18, width: 240 }} />
        <div className="skeleton" style={{ height: 220, width: "100%", borderRadius: 8 }} />
      </section>
    </section>
  );
}

function TwinPanelSkeleton() {
  return (
    <div
      className="col gap-3"
      style={{
        background: "var(--bg-1)",
        border: "1px solid var(--line)",
        borderRadius: 12,
        padding: 16,
        boxShadow: "var(--shadow-1)",
      }}
    >
      <div className="row between center">
        <div className="skeleton" style={{ height: 12, width: 140 }} />
        <div className="skeleton" style={{ height: 18, width: 60, borderRadius: 4 }} />
      </div>
      <div className="row gap-4 center">
        <div className="skeleton" style={{ width: 120, height: 120, borderRadius: 8 }} />
        <div className="skeleton" style={{ width: 72, height: 72, borderRadius: 999 }} />
      </div>
      <div className="col gap-1">
        <div className="skeleton" style={{ height: 14, width: "75%" }} />
        <div className="skeleton" style={{ height: 11, width: "50%" }} />
      </div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: 6,
        }}
      >
        {[0, 1, 2].map((i) => (
          <div key={i} className="col gap-1">
            <div className="skeleton" style={{ height: 11, width: 36 }} />
            <div className="skeleton" style={{ height: 16, width: 64 }} />
          </div>
        ))}
      </div>
    </div>
  );
}
