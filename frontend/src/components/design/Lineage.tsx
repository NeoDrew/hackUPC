import { creativeImageUrl } from "@/lib/assetUrl";

export function Lineage({
  fatiguedId,
  winnerId,
  variantLabel = "Generated variant",
}: {
  fatiguedId: number;
  winnerId: number;
  variantLabel?: string;
}) {
  const cell = (
    src: string | null,
    caption: string,
    sub: string,
    accent?: boolean,
  ) => (
    <div className="col gap-2 center">
      {src ? (
        <img
          src={src}
          alt=""
          style={{
            width: 120,
            height: 120,
            borderRadius: 10,
            objectFit: "cover",
            background: "var(--bg-2)",
            border: accent ? "2px solid var(--accent)" : "1px solid var(--line)",
            boxShadow: "var(--shadow-1)",
          }}
        />
      ) : (
        <div
          style={{
            width: 120,
            height: 120,
            borderRadius: 10,
            background: "var(--accent-soft)",
            border: "2px solid var(--accent)",
            display: "grid",
            placeItems: "center",
            color: "var(--accent)",
            fontWeight: 600,
          }}
        >
          SVG mock
        </div>
      )}
      <span className="t-card">{caption}</span>
      <span className="t-micro muted">{sub}</span>
    </div>
  );

  const arrow = (label: string) => (
    <div className="col center gap-1" style={{ color: "var(--t-3)" }}>
      <span style={{ fontSize: 24 }}>→</span>
      <span className="t-micro">{label}</span>
    </div>
  );

  return (
    <div className="row center gap-4" style={{ justifyContent: "center" }}>
      {cell(creativeImageUrl(fatiguedId), "Fatigued", `#${fatiguedId}`)}
      {arrow("twin found")}
      {cell(creativeImageUrl(winnerId), "Winner twin", `#${winnerId}`)}
      {arrow("variant generated")}
      {cell(null, variantLabel, "AI-templated", true)}
    </div>
  );
}
