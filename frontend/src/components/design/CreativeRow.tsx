"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import type { CreativeRow as CreativeRowT, HealthBreakdown } from "@/lib/api";
import { creativeImageUrl } from "@/lib/assetUrl";
import {
  formatCurrency,
  formatDays,
  formatPct,
  formatRoas,
} from "@/lib/format";
import { HealthBreakdownPanel } from "./HealthBreakdownPanel";
import { HealthRing } from "./HealthRing";
import { Sparkline } from "./Sparkline";

// Per-band action verb + destination. The cockpit table now answers "what
// should I do with this creative" inline — a marketer doesn't need to drill
// in to figure out the next step.
function actionForBand(band: string | null | undefined): {
  label: string;
  destination: "variant" | "detail";
  primary: boolean;
} {
  switch (band) {
    case "rescue":
      return { label: "Improve", destination: "variant", primary: true };
    case "cut":
      return { label: "Replace", destination: "variant", primary: true };
    case "scale":
      return { label: "Scale up", destination: "detail", primary: false };
    case "watch":
    default:
      return { label: "Open", destination: "detail", primary: false };
  }
}

export function CreativeRow({
  row,
  from,
  range,
}: {
  row: CreativeRowT;
  from?: string;
  range?: { start?: string; end?: string };
}) {
  const [expanded, setExpanded] = useState(false);
  const router = useRouter();

  const qp = new URLSearchParams();
  if (from) qp.set("from", from);
  if (range?.start) qp.set("start", range.start);
  if (range?.end) qp.set("end", range.end);
  const qs = qp.toString();
  const detailHref = qs
    ? `/creatives/${row.creative_id}?${qs}`
    : `/creatives/${row.creative_id}`;
  const variantHref = qs
    ? `/creatives/${row.creative_id}/variant?${qs}`
    : `/creatives/${row.creative_id}/variant`;
  const action = actionForBand(row.status_band);
  const actionHref = action.destination === "variant" ? variantHref : detailHref;
  const href = detailHref;

  // The Link still wraps the row so middle-click and Cmd-click open in
  // a new tab. The chevron stops propagation + prevents the default
  // navigation so clicking it just toggles the dropdown.
  return (
    <div className="creative-row-wrap">
      <Link href={href} className="creative-row" prefetch={false}>
        <div className="thumb">
          <img
            src={creativeImageUrl(row.creative_id)}
            alt=""
            loading="lazy"
          />
        </div>
        <div className="col">
          <div className="headline">
            {row.headline || `Creative ${row.creative_id}`}
          </div>
          <div className="meta">
            {row.advertiser_name} · {row.vertical} · {row.format} · #
            {row.creative_id}
          </div>
        </div>
        <div className="num-cell">{formatPct(row.ctr)}</div>
        <div className="num-cell">{formatPct(row.cvr)}</div>
        <div className="num-cell">{formatRoas(row.roas)}</div>
        <div className="num-cell">
          {formatCurrency(row.spend_usd, { compact: true })}
        </div>
        <div className="num-cell">{formatDays(row.days_active)}</div>
        <div
          className="num-cell"
          style={{
            display: "flex",
            justifyContent: "flex-end",
            alignItems: "center",
          }}
        >
          <Sparkline
            series={row.sparkline}
            fatigueDay={row.fatigue_day}
            width={88}
            height={22}
          />
        </div>
        <div
          className="health-cell"
          style={{
            display: "flex",
            justifyContent: "flex-end",
            alignItems: "center",
            gap: 6,
          }}
        >
          <HealthRing value={row.health} size={20} showLabel={false} />
          <button
            type="button"
            className="creative-row-expand-btn"
            aria-expanded={expanded}
            aria-label={
              expanded ? "Hide health breakdown" : "Show health breakdown"
            }
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              setExpanded((v) => !v);
            }}
          >
            <span className="creative-row-expand-icon">▾</span>
          </button>
        </div>
        <div className="action-cell">
          <button
            type="button"
            className={`row-action${action.primary ? " primary" : ""}`}
            aria-label={`${action.label} creative ${row.creative_id}`}
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              router.push(actionHref);
            }}
          >
            {action.label}
            <span className="row-action-arrow" aria-hidden>
              →
            </span>
          </button>
        </div>
      </Link>
      <div className={`creative-row-expander${expanded ? " open" : ""}`}>
        <div>
          <div className="creative-row-expander-inner">
            <HealthBreakdownPanel
              breakdown={row.health_breakdown as HealthBreakdown | null}
              daysActive={row.days_active}
              rowData={{
                total_impressions: row.impressions,
                total_clicks: row.clicks,
                total_conversions: row.conversions,
                total_spend_usd: row.spend_usd,
                total_revenue_usd: row.revenue_usd,
                total_days_active: row.days_active,
              }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

