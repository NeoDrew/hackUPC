/** Route-level loading state for the creative detail page. Next.js
 * renders this automatically while the server component on the same
 * segment fetches — covers the cold-start window when Render is sleepy
 * or the user just changed the date range. Mirrors the live layout
 * (sticky back bar, header, hero card, sections) so the swap doesn't
 * jolt the eye. */
export default function CreativeDetailLoading() {
  return (
    <section className="col gap-5" style={{ paddingTop: 16, maxWidth: 1040, margin: "0 auto" }}>
      <div
        className="row center between"
        style={{
          position: "sticky",
          top: 0,
          zIndex: 5,
          background: "var(--bg-0)",
          padding: "8px 0",
        }}
      >
        <div className="skeleton" style={{ width: 90, height: 30, borderRadius: 8 }} />
      </div>

      <header className="col gap-2">
        <div className="skeleton" style={{ height: 12, width: 120 }} />
        <div className="skeleton" style={{ height: 28, width: 360 }} />
        <div className="skeleton" style={{ height: 14, width: 280 }} />
      </header>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "220px 1fr",
          gap: 24,
          alignItems: "start",
          background: "var(--bg-1)",
          border: "1px solid var(--line)",
          borderRadius: 14,
          padding: 20,
          boxShadow: "var(--shadow-1)",
        }}
      >
        <div className="skeleton" style={{ width: 220, height: 220, borderRadius: 10 }} />
        <div className="col gap-4">
          <div className="row center gap-4">
            <div
              className="skeleton"
              style={{ width: 120, height: 120, borderRadius: 999 }}
            />
            <div className="col gap-2" style={{ flex: 1 }}>
              {[0, 1, 2].map((i) => (
                <div key={i} className="col gap-1">
                  <div className="skeleton" style={{ height: 11, width: 110 }} />
                  <div className="skeleton" style={{ height: 8, width: "60%", borderRadius: 4 }} />
                </div>
              ))}
            </div>
          </div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(3, 1fr)",
              gap: 12,
            }}
          >
            {[0, 1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="col gap-1">
                <div className="skeleton" style={{ height: 11, width: 60 }} />
                <div className="skeleton" style={{ height: 18, width: 80 }} />
              </div>
            ))}
          </div>
        </div>
      </div>

      <section className="col gap-2">
        <div className="skeleton" style={{ height: 18, width: 180 }} />
        <div className="row gap-2" style={{ flexWrap: "wrap" }}>
          {[80, 110, 70, 95, 130, 90].map((w, i) => (
            <div
              key={i}
              className="skeleton"
              style={{ height: 24, width: w, borderRadius: 999 }}
            />
          ))}
        </div>
      </section>
    </section>
  );
}
