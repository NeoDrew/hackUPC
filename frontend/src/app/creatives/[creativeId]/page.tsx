import Link from "next/link";
import { notFound } from "next/navigation";

import { api, type HealthBreakdown } from "@/lib/api";
import { creativeImageUrl } from "@/lib/assetUrl";
import { HealthRing } from "@/components/design/HealthRing";
import { MetadataPills } from "@/components/design/MetadataPills";
import { PerformanceGrid } from "@/components/design/PerformanceGrid";
import { FatigueChart } from "@/components/design/FatigueChart";
import { SaturationCard } from "@/components/design/SaturationCard";
import { HealthBreakdownPanel } from "@/components/design/HealthBreakdownPanel";

const VALID_FROM = new Set([
  "scale",
  "watch",
  "rescue",
  "cut",
  "explore",
  "advisor",
]);

export default async function CreativeDetailPage(
  props: PageProps<"/creatives/[creativeId]">,
) {
  const { creativeId } = await props.params;
  const id = Number(creativeId);
  if (!Number.isFinite(id)) notFound();

  const sp = await props.searchParams;
  const rawFrom = typeof sp?.from === "string" ? sp.from : undefined;
  const from = rawFrom && VALID_FROM.has(rawFrom) ? rawFrom : undefined;
  const start = typeof sp?.start === "string" ? sp.start : undefined;
  const end = typeof sp?.end === "string" ? sp.end : undefined;
  // Slice context — when the user drilled in from an advisor card.
  const sliceCountry = typeof sp?.country === "string" ? sp.country : undefined;
  const sliceOs = typeof sp?.os === "string" ? sp.os : undefined;
  const rangeQs = new URLSearchParams();
  if (start) rangeQs.set("start", start);
  if (end) rangeQs.set("end", end);
  const rangeSuffix = rangeQs.toString();
  const backBase =
    from === "advisor"
      ? "/actions"
      : from === "explore"
      ? "/explore"
      : from
      ? `/?tab=${from}`
      : "/";
  const backHref = rangeSuffix
    ? `${backBase}${backBase.includes("?") ? "&" : "?"}${rangeSuffix}`
    : backBase;
  const twinSuffix = rangeSuffix ? `?${rangeSuffix}` : "";

  let creative;
  try {
    creative = await api.getCreative(id, { start, end });
  } catch {
    notFound();
  }
  const data = creative as unknown as Record<string, unknown>;
  const health = (creative.health as number | null) ?? 0;
  const status = (data.creative_status as string | null) ?? null;
  const band = (creative.status_band as string | null) ?? null;
  const needsRescue = band === "rescue" || band === "cut";
  // Our predicted fatigue verdict (changepoint + trained classifier).
  // The dataset's `fatigue_day` is the supervised training label and is
  // never read here — predictions only.
  const predictedFatigue = (creative.predicted_fatigue ?? null) as {
    is_fatigued: boolean;
    predicted_fatigue_day: number | null;
    predicted_fatigue_date: string | null;
    fatigue_ctr_drop: number | null;
    pre_ctr: number | null;
    post_ctr: number | null;
    model_score: number | null;
  } | null;
  const fatigueDay = predictedFatigue?.predicted_fatigue_day ?? null;
  const fatiguePredicted = predictedFatigue?.is_fatigued ?? false;

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
        {needsRescue ? (
          <div className="row center gap-2">
            <Link
              href={`/creatives/${id}/twin${twinSuffix}`}
              className="btn dense"
            >
              Why is this losing?
            </Link>
            <Link
              href={`/creatives/${id}/variant${twinSuffix}`}
              className="btn primary"
              style={{
                padding: "12px 22px",
                fontSize: 15,
                fontWeight: 700,
                letterSpacing: "-0.01em",
                background: "var(--accent)",
                borderColor: "var(--accent)",
                color: "#fff",
                boxShadow: "var(--shadow-1)",
              }}
            >
              Improve →
            </Link>
          </div>
        ) : (
          <Link
            href={`/creatives/${id}/variant${twinSuffix}`}
            className="t-micro"
            style={{ color: "var(--accent)" }}
          >
            Improve →
          </Link>
        )}
      </div>

      <header className="col gap-2">
        <span className="t-overline">
          Creative #{creative.creative_id}
          {sliceCountry || sliceOs ? (
            <span className="slice-context-chip">
              Filtered to {sliceCountry ?? ""}
              {sliceOs && sliceOs !== "*"
                ? ` · ${sliceOs}`
                : ""}
            </span>
          ) : null}
        </span>
        <h1 className="t-page" style={{ margin: 0 }}>
          {(data.headline as string) || `Creative ${creative.creative_id}`}
        </h1>
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

      <HealthBreakdownPanel
        breakdown={data.health_breakdown as HealthBreakdown | null}
        daysActive={(data.total_days_active as number | null) ?? undefined}
        alwaysOpen
        rowData={{
          total_impressions: data.total_impressions as number | undefined,
          total_clicks: data.total_clicks as number | undefined,
          total_conversions: data.total_conversions as number | undefined,
          total_spend_usd: data.total_spend_usd as number | undefined,
          total_revenue_usd: data.total_revenue_usd as number | undefined,
          total_days_active: data.total_days_active as number | undefined,
        }}
      />

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
          <h3 className="t-section">Daily CTR · 75-day trend</h3>
          <span className="t-micro muted">
            {fatiguePredicted && fatigueDay !== null
              ? `Our model flags fatigue from day ${fatigueDay}${
                  predictedFatigue?.model_score !== null &&
                  predictedFatigue?.model_score !== undefined
                    ? ` (confidence ${Math.round(predictedFatigue.model_score * 100)}%)`
                    : ""
                }`
              : "Our model: no fatigue detected"}
          </span>
        </header>
        <FatigueChart creativeId={id} fatigueDay={fatigueDay} />
      </section>

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
