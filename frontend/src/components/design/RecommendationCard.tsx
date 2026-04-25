"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ArrowRight, Check, Clock, X } from "lucide-react";

import {
  applyRecommendation,
  dismissRecommendation,
  snoozeRecommendation,
  type SliceRecommendation,
} from "@/lib/api";
import { creativeImageUrl } from "@/lib/assetUrl";
import {
  actionTypeLabel,
  severityLabel,
  severityToTone,
} from "@/lib/status";

/**
 * Industry-canonical recommendation card. Anatomy mirrors AppLovin MAX /
 * Liftoff Vector / Moloco Cloud DSP cards (data_findings.md):
 *
 *   1. Entity label   — creative_id · country · os
 *   2. Signal headline — leads with the delta ("CTR -42% (7d)")
 *   3. Imperative CTA — one of the canonical six verbs
 *   4. Projected impact — always prefixed with "est." so we never overclaim
 *   5. Apply / Snooze / Dismiss
 *
 * The headline + rationale are computed deterministically by
 * recommendation_copy.py and (best-effort) polished by Gemma. The card
 * never re-derives copy on the client.
 */
export function RecommendationCard({
  rec,
  showImpactBar = false,
  totalDailyImpactUsd,
}: {
  rec: SliceRecommendation;
  showImpactBar?: boolean;
  totalDailyImpactUsd?: number;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState<"apply" | "snooze" | "dismiss" | null>(null);
  const [snoozeOpen, setSnoozeOpen] = useState(false);

  const tone = severityToTone(rec.severity);
  const label = severityLabel(rec.severity);
  const verb = actionTypeLabel(rec.action_type);
  const slice =
    rec.os && rec.os !== "*"
      ? `${rec.country} · ${rec.os}`
      : rec.country;

  // Drill destination — slice context preserved for the detail page so it
  // can filter performance to the recommended slice.
  const detailHref = (() => {
    const params = new URLSearchParams({ from: "advisor" });
    if (rec.country) params.set("country", rec.country);
    if (rec.os && rec.os !== "*") params.set("os", rec.os);
    return `/creatives/${rec.creative_id}?${params.toString()}`;
  })();

  // Bar width — share of the total at-stake $/day. Visual proxy for "how
  // much of today's portfolio impact lives in this single card".
  const impactShare =
    showImpactBar && totalDailyImpactUsd && totalDailyImpactUsd > 0
      ? Math.min(1, rec.est_daily_impact_usd / totalDailyImpactUsd)
      : 0;

  const onApply = async () => {
    if (busy) return;
    setBusy("apply");
    try {
      await applyRecommendation(rec.recommendation_id);
      router.refresh();
    } finally {
      setBusy(null);
    }
  };

  const onSnooze = async (hours: number) => {
    if (busy) return;
    setBusy("snooze");
    setSnoozeOpen(false);
    try {
      const until = new Date(
        Date.now() + hours * 60 * 60 * 1000,
      ).toISOString();
      await snoozeRecommendation(rec.recommendation_id, until);
      router.refresh();
    } finally {
      setBusy(null);
    }
  };

  const onDismiss = async () => {
    if (busy) return;
    setBusy("dismiss");
    try {
      await dismissRecommendation(rec.recommendation_id);
      router.refresh();
    } finally {
      setBusy(null);
    }
  };

  const showThumb = rec.creative_id > 0;
  const impactText = formatImpact(rec.est_daily_impact_usd);

  return (
    <li
      className={`rec-card rec-card-${tone}`}
      data-busy={busy ? "1" : undefined}
    >
      {showThumb ? (
        <Link href={detailHref} prefetch={false} className="rec-card-thumb">
          <img
            src={creativeImageUrl(rec.creative_id)}
            alt=""
            loading="lazy"
          />
        </Link>
      ) : null}

      <div className="rec-card-body">
        <div className="rec-card-meta">
          <span className={`rec-card-pill tone-${tone}`}>
            <span className="rec-card-dot" aria-hidden />
            {label}
          </span>
          <span className="rec-card-verb">{verb}</span>
          <span className="rec-card-slice">{slice}</span>
          <span className="rec-card-cid">#{rec.creative_id}</span>
          {rec.is_polished ? (
            <span className="rec-card-polished" title="Marketer-voice copy">
              ✦
            </span>
          ) : null}
        </div>

        <Link href={detailHref} prefetch={false} className="rec-card-headline">
          {rec.headline}
        </Link>
        <p className="rec-card-rationale">{rec.rationale}</p>

        <div className="rec-card-impact">
          <span className="rec-card-impact-num">est. {impactText}/day</span>
          {showImpactBar ? (
            <span
              className="rec-card-impact-bar"
              style={{ width: `${(impactShare * 100).toFixed(1)}%` }}
              aria-hidden
            />
          ) : null}
        </div>
      </div>

      <div className="rec-card-actions">
        <button
          type="button"
          className="rec-card-cta primary"
          onClick={onApply}
          disabled={busy !== null}
        >
          {busy === "apply" ? (
            "…"
          ) : (
            <>
              <Check size={14} strokeWidth={2} aria-hidden />
              Apply
            </>
          )}
        </button>
        <div className="rec-card-snooze">
          <button
            type="button"
            className="rec-card-secondary"
            onClick={() => setSnoozeOpen((v) => !v)}
            disabled={busy !== null}
          >
            <Clock size={14} strokeWidth={1.75} aria-hidden />
            Snooze
          </button>
          {snoozeOpen ? (
            <div className="rec-card-snooze-menu" role="menu">
              <button onClick={() => onSnooze(24)}>24h</button>
              <button onClick={() => onSnooze(24 * 7)}>7 days</button>
              <button onClick={() => onSnooze(24 * 30)}>30 days</button>
            </div>
          ) : null}
        </div>
        <button
          type="button"
          className="rec-card-dismiss"
          onClick={onDismiss}
          disabled={busy !== null}
          title="Dismiss"
        >
          <X size={14} strokeWidth={1.75} aria-hidden />
        </button>
        <Link
          href={detailHref}
          prefetch={false}
          className="rec-card-drill"
          title="Open creative"
        >
          <ArrowRight size={14} strokeWidth={1.75} aria-hidden />
        </Link>
      </div>
    </li>
  );
}

function formatImpact(usd: number): string {
  if (usd >= 1000) return `$${(usd / 1000).toFixed(1)}k`;
  return `$${Math.round(usd).toLocaleString()}`;
}
