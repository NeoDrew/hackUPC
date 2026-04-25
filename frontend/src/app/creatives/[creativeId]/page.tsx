import Link from "next/link";
import { notFound } from "next/navigation";

import { api } from "@/lib/api";
import { creativeImageUrl } from "@/lib/assetUrl";
import { HealthRing } from "@/components/design/HealthRing";
import { StatusPill } from "@/components/design/StatusPill";
import { BandPill } from "@/components/design/BandPill";
import { MetadataPills } from "@/components/design/MetadataPills";
import { PerformanceGrid } from "@/components/design/PerformanceGrid";
import { FatigueChart } from "@/components/design/FatigueChart";
import { SaturationCard } from "@/components/design/SaturationCard";
import { HealthBreakdownCard } from "@/components/design/HealthBreakdownCard";

const VALID_FROM = new Set(["scale", "watch", "rescue", "cut", "explore"]);

export default async function CreativeDetailPage(
  props: PageProps<"/creatives/[creativeId]">,
) {
  const { creativeId } = await props.params;
  const id = Number(creativeId);
  if (!Number.isFinite(id)) notFound();

  const sp = await props.searchParams;
  const rawFrom = typeof sp?.from === "string" ? sp.from : undefined;
  const from = rawFrom && VALID_FROM.has(rawFrom) ? rawFrom : undefined;
  const backHref =
    from === "explore" ? "/explore" : from ? `/?tab=${from}` : "/";

  let creative;
  try {
    creative = await api.getCreative(id);
  } catch {
    notFound();
  }
  const data = creative as unknown as Record<string, unknown>;
  const health = (creative.health as number | null) ?? 0;
  const status = (data.creative_status as string | null) ?? null;
  const band = (creative.status_band as string | null) ?? null;
  const fatigueDay = (data.fatigue_day as number | null) ?? null;

  return (
    <section
      className="col gap-5"
      style={{ paddingTop: 16, maxWidth: 1040, margin: "0 auto" }}
    >
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
        <Link href={backHref} className="btn dense">
          ← Back
        </Link>
        {status === "fatigued" && (
          <Link href={`/creatives/${id}/twin`} className="btn dense primary">
            Why is this losing?
          </Link>
        )}
      </div>

      <header className="col gap-2">
        <span className="t-overline">Creative #{creative.creative_id}</span>
        <h1 className="t-page" style={{ margin: 0 }}>
          {(data.headline as string) || `Creative ${creative.creative_id}`}
        </h1>
        <div className="row center gap-2" style={{ flexWrap: "wrap" }}>
          <BandPill band={band} health={health} />
          <StatusPill status={status} dense />
          <span className="t-micro muted">{bandVsLabel(band, status)}</span>
        </div>
        <div className="t-body muted">
          {String(data.advertiser_name ?? "")} · {String(data.vertical ?? "")} ·{" "}
          {String(data.format ?? "")} · {String(data.language ?? "")}
        </div>
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
        <img
          src={creativeImageUrl(creative.creative_id)}
          alt={`creative ${creative.creative_id}`}
          style={{
            width: 220,
            height: 220,
            objectFit: "cover",
            borderRadius: 10,
            background: "var(--bg-2)",
            border: "1px solid var(--line)",
          }}
        />
        <div className="col gap-4">
          <div className="row center gap-4">
            <HealthRing value={health} size={120} />
            <div className="col gap-2" style={{ flex: 1 }}>
              <div className="col gap-1">
                <span className="t-micro">CTR vs cohort</span>
                <div className="score-bar">
                  <div
                    style={{
                      width: `${cohortBarWidth((creative.quadrant?.ctr_percentile ?? 0) * 100)}%`,
                      background: "var(--accent)",
                    }}
                  />
                </div>
              </div>
              <div className="col gap-1">
                <span className="t-micro">CVR vs cohort</span>
                <div className="score-bar">
                  <div
                    style={{
                      width: `${cohortBarWidth((creative.quadrant?.cvr_percentile ?? 0) * 100)}%`,
                      background: "var(--status-top)",
                    }}
                  />
                </div>
              </div>
              <div className="col gap-1">
                <span className="t-micro">Health band</span>
                <div className="score-bar">
                  <div
                    style={{
                      width: `${Math.max(5, health)}%`,
                      background: "var(--health-mid-a)",
                    }}
                  />
                </div>
              </div>
            </div>
          </div>
          <PerformanceGrid creative={creative} />
        </div>
      </div>

      <HealthBreakdownCard
        breakdown={
          data.health_breakdown as
            | {
                health?: number;
                status_band?: string;
                objective_mode?: string;
                kpi_goal?: string | null;
                components?: {
                  S?: number;
                  C?: number;
                  T?: number;
                  R?: number;
                  E?: number;
                  B?: number;
                } | null;
                weights?: Record<string, number>;
                contributions?: Record<string, number>;
                cohort?: {
                  level?: string;
                  size?: number;
                  keys?: Record<string, unknown>;
                };
                raw?: Record<string, unknown>;
              }
            | null
            | undefined
        }
      />

      {status === "fatigued" && (
        <section
          className="col gap-2"
          style={{
            background: "var(--bg-1)",
            border: "1px solid var(--line)",
            borderRadius: 12,
            padding: 16,
          }}
        >
          <header className="row center between">
            <h3 className="t-section">Daily CTR · fatigue signature</h3>
            <span className="t-micro">
              Launched day 0 · fatigue flagged day {fatigueDay ?? "–"}
            </span>
          </header>
          <FatigueChart creativeId={id} fatigueDay={fatigueDay} />
        </section>
      )}

      <section className="col gap-2">
        <h3 className="t-section">Creative attributes</h3>
        <MetadataPills creative={creative} />
      </section>

      {creative.saturation ? (
        <SaturationCard saturation={creative.saturation} />
      ) : null}
    </section>
  );
}

function cohortBarWidth(pct: number): number {
  return Math.max(5, Math.min(100, pct));
}

function bandVsLabel(band: string | null, status: string | null): string {
  if (!band || !status) return "";
  const expected: Record<string, string> = {
    top_performer: "scale",
    stable: "watch",
    fatigued: "rescue",
    underperformer: "cut",
  };
  const expectedBand = expected[status];
  if (!expectedBand) return "";
  return band === expectedBand
    ? "✓ our trajectory band agrees with Smadex's label"
    : "✗ diverges from Smadex's label · talking point";
}
