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
  const isWinner = role === "twin";
  return (
    <div
      className={`twin-panel${isWinner ? " winner" : ""}`}
      style={{
        background: "var(--bg-1)",
        border: `1px solid ${isWinner ? "var(--status-top)" : "var(--line)"}`,
        borderRadius: 12,
        padding: 18,
        boxShadow: isWinner ? "var(--shadow-2)" : "var(--shadow-1)",
        display: "flex",
        flexDirection: "column",
        gap: 14,
      }}
    >
      <div className="row between center">
        <span
          className="t-overline"
          style={{ color: isWinner ? "var(--status-top)" : "var(--t-3)" }}
        >
          {isWinner ? "Twin winner" : "Your fatigued creative"}
        </span>
        <StatusPill status={status} dense />
      </div>
      <div className="row gap-4 center">
        <img
          src={creativeImageUrl(creative.creative_id)}
          alt=""
          style={{
            width: 180,
            height: 180,
            objectFit: "cover",
            borderRadius: 10,
            border: "1px solid var(--line)",
            background: "var(--bg-2)",
          }}
        />
        <div className="col gap-2" style={{ flex: 1 }}>
          <HealthRing value={health} size={72} />
          <div className="col gap-1">
            <strong className="t-card">
              {(data.headline as string) || `Creative ${creative.creative_id}`}
            </strong>
            <span className="t-micro">
              #{creative.creative_id} · {String(data.theme ?? "")} ·{" "}
              {String(data.hook_type ?? "")}
            </span>
          </div>
        </div>
      </div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: 8,
          paddingTop: 10,
          borderTop: "1px solid var(--line-soft)",
        }}
      >
        <Stat
          label="ROAS"
          value={formatRoas((data.overall_roas as number) ?? 0)}
          highlight={isWinner}
        />
        <Stat
          label="CTR"
          value={formatPct((data.overall_ctr as number) ?? 0)}
          highlight={isWinner}
        />
        <Stat
          label="CVR"
          value={formatPct((data.overall_cvr as number) ?? 0, 1)}
          highlight={isWinner}
        />
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div className="col gap-1">
      <span className="t-overline">{label}</span>
      <span
        className="num"
        style={{
          fontSize: 20,
          fontWeight: 600,
          color: highlight ? "var(--status-top)" : "var(--t-1)",
        }}
      >
        {value}
      </span>
    </div>
  );
}
