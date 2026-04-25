import type { CreativeRow } from "@/lib/api";
import { creativeImageUrl } from "@/lib/assetUrl";
import { formatCount, formatCurrency, formatPct, formatRoas } from "@/lib/format";
import { statusToTone, statusToVerb } from "@/lib/status";
import { HealthRing } from "./HealthRing";
import { Sparkline } from "./Sparkline";

export function PhoneCard({ row }: { row: CreativeRow }) {
  const tone = statusToTone(row.status);
  const verb = statusToVerb(row.status);
  return (
    <article className="phone-card" data-tone={tone}>
      <div
        className="phone-card-bg"
        style={{ backgroundImage: `url(${creativeImageUrl(row.creative_id)})` }}
        aria-hidden
      />
      <div className="phone-card-scrim" aria-hidden />

      <div className="phone-card-top">
        <span className={`status-pill ${tone} dense`}>
          <span className="seed" />
          {verb}
        </span>
        <HealthRing value={row.health} size={72} />
      </div>

      <div className="phone-card-mid">
        <h2>{row.headline || `Creative ${row.creative_id}`}</h2>
        <p className="phone-meta">
          {row.advertiser_name} · {row.vertical} · {row.format}
        </p>
        <div className="phone-stats">
          <Stat label="CTR" value={formatPct(row.ctr)} />
          <Stat label="CVR" value={formatPct(row.cvr, 1)} />
          <Stat label="ROAS" value={formatRoas(row.roas)} />
        </div>
      </div>

      <div className="phone-card-bottom">
        <div className="phone-trend">
          <Sparkline
            series={row.sparkline}
            fatigueDay={row.fatigue_day}
            width={220}
            height={40}
            stroke="#ffffff"
            fill="rgba(255,255,255,0.18)"
          />
          <span className="phone-trend-label">30-day CTR · spend {formatCurrency(row.spend_usd, { compact: true })} · {formatCount(row.impressions, { compact: true })} impr</span>
        </div>
      </div>
    </article>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="phone-stat">
      <span className="phone-stat-label">{label}</span>
      <span className="phone-stat-value">{value}</span>
    </div>
  );
}
