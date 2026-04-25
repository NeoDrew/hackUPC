import type { CreativeDetail } from "@/lib/api";
import { creativeImageUrl } from "@/lib/assetUrl";
import { formatPct, formatRoas } from "@/lib/format";
import { HealthRing } from "./HealthRing";
import { StatusPill } from "./StatusPill";

export function TwinPanel({
  creative,
  role,
}: {
  creative: CreativeDetail;
  role: "yours" | "twin";
}) {
  const data = creative as unknown as Record<string, number | string | null | undefined>;
  // Read the fatigue-adjusted health the backend already computed; do NOT
  // recompute from perf_score (that's the lifetime score and would show a
  // fatigued creative as 84 instead of its trajectory-aware ~25).
  const health = (creative.health as number | null) ?? 0;
  const status = (data.creative_status as string | null) ?? null;
  return (
    <div
      className="col gap-3"
      style={{
        background: "var(--bg-1)",
        border: `1px solid ${role === "twin" ? "var(--status-top)" : "var(--line)"}`,
        borderRadius: 12,
        padding: 16,
        boxShadow: "var(--shadow-1)",
      }}
    >
      <div className="row between center">
        <span className="t-overline">{role === "yours" ? "Your fatigued creative" : "Twin winner"}</span>
        <StatusPill status={status} dense />
      </div>
      <div className="row gap-4 center">
        <img
          src={creativeImageUrl(creative.creative_id)}
          alt=""
          style={{
            width: 120,
            height: 120,
            objectFit: "cover",
            borderRadius: 8,
            border: "1px solid var(--line)",
            background: "var(--bg-2)",
          }}
        />
        <HealthRing value={health} size={72} />
      </div>
      <div className="col gap-1">
        <strong className="t-card">{(data.headline as string) || `Creative ${creative.creative_id}`}</strong>
        <span className="t-micro">
          #{creative.creative_id} · {String(data.theme ?? "")} · {String(data.hook_type ?? "")}
        </span>
      </div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: 6,
          marginTop: 4,
        }}
      >
        <Stat label="ROAS" value={formatRoas((data.overall_roas as number) ?? 0)} />
        <Stat label="CTR" value={formatPct((data.overall_ctr as number) ?? 0)} />
        <Stat label="CVR" value={formatPct((data.overall_cvr as number) ?? 0, 1)} />
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="col gap-1">
      <span className="t-overline">{label}</span>
      <span className="num" style={{ fontSize: 16, fontWeight: 600 }}>
        {value}
      </span>
    </div>
  );
}
