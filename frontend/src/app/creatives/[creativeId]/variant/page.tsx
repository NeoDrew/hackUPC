import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft } from "lucide-react";

import { api } from "@/lib/api";
import { BriefPanel, type BriefField } from "@/components/design/BriefPanel";
import { Lineage } from "@/components/design/Lineage";
import { PredictedLift, type LiftRow } from "@/components/design/PredictedLift";
import { PreviewChip } from "@/components/design/PreviewChip";
import { PushToTestButton } from "@/components/design/Toast";
import {
  RenderedVariantSvg,
  type VariantBrief,
} from "@/components/design/RenderedVariantSvg";

export default async function VariantPage(
  props: PageProps<"/creatives/[creativeId]/variant">,
) {
  const { creativeId } = await props.params;
  const id = Number(creativeId);
  if (!Number.isFinite(id)) notFound();

  let twin;
  try {
    twin = await api.getTwin(id);
  } catch {
    notFound();
  }
  const [source, winner] = await Promise.all([
    api.getCreative(twin.fatigued_id),
    api.getCreative(twin.winner_id),
  ]);
  const sourceData = source as unknown as Record<string, number | string | null | undefined>;
  const winnerData = winner as unknown as Record<string, number | string | null | undefined>;

  const brief: VariantBrief = {
    headline: String(winnerData.headline ?? sourceData.headline ?? "New variant"),
    subhead: String(winnerData.subhead ?? sourceData.subhead ?? ""),
    cta: String(winnerData.cta_text ?? sourceData.cta_text ?? "Try now"),
    dominantColor: String(winnerData.dominant_color ?? sourceData.dominant_color ?? "purple"),
    discountBadge: Boolean(winnerData.has_discount_badge),
  };

  const fields: BriefField[] = [
    { label: "Headline", value: brief.headline },
    { label: "Subhead", value: brief.subhead },
    { label: "CTA", value: brief.cta },
    { label: "Dominant color", value: brief.dominantColor },
    { label: "Emotional tone", value: String(winnerData.emotional_tone ?? "urgent") },
    { label: "Duration (s)", value: String(winnerData.duration_sec ?? 15) },
    { label: "Text density", value: String(winnerData.text_density ?? 0.2) },
    { label: "Clutter target", value: "keep low" },
    {
      label: "Discount badge",
      value: brief.discountBadge ? "yes" : "no",
    },
    {
      label: "UGC style",
      value: winnerData.has_ugc_style ? "yes" : "no",
    },
  ];

  const rationale = [
    `Mirror the winner's hook type "${winnerData.hook_type ?? ""}". Adjacent combos in the cohort average 2× CVR.`,
    `Keep clutter score low (${winnerData.clutter_score ?? "<0.3"}). Fatigued creatives in this cohort trend above 0.5.`,
    `Run at ${winnerData.duration_sec ?? 15}s, the winning duration ceiling in ${twin.segment.format}.`,
    `Restate the discount proof; it's the single largest driver of CVR in this vertical.`,
  ];

  const lift: LiftRow[] = [
    {
      label: "CTR",
      base: (sourceData.last_7d_ctr as number) ?? (sourceData.overall_ctr as number) ?? 0,
      projected: (winnerData.overall_ctr as number) ?? 0,
      format: "pct",
    },
    {
      label: "CVR",
      base: (sourceData.last_7d_cvr as number) ?? (sourceData.overall_cvr as number) ?? 0,
      projected: (winnerData.overall_cvr as number) ?? 0,
      format: "pct",
    },
    {
      label: "ROAS",
      base: (sourceData.overall_roas as number) ?? 0,
      projected: (winnerData.overall_roas as number) ?? 0,
      format: "roas",
    },
  ];

  return (
    <section
      className="col gap-5"
      style={{ paddingTop: 16, maxWidth: 1100, margin: "0 auto" }}
    >
      <header className="row between center" style={{ flexWrap: "wrap", gap: 12 }}>
        <div className="col gap-1">
          <div className="row center gap-3">
            <Link href={`/creatives/${id}/twin`} className="btn dense">
              <ArrowLeft size={14} strokeWidth={1.75} aria-hidden /> Back to twin
            </Link>
            <span className="filter-chip mono">V-{id.toString().padStart(6, "0")}-001</span>
            <PreviewChip />
          </div>
          <h1 className="t-page" style={{ margin: 0 }}>
            AI-generated variant · {twin.segment.vertical} / {twin.segment.format}
          </h1>
          <p className="t-body muted">
            Brief derived from the twin winner. Swap in Gemma + Q3 bandit output once wired.
          </p>
        </div>
        <div className="row center gap-2">
          <button type="button" className="btn dense">Save</button>
          <button type="button" className="btn dense">Send to designer</button>
          <PushToTestButton />
        </div>
      </header>

      <Lineage fatiguedId={twin.fatigued_id} winnerId={twin.winner_id} />

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "380px 1fr",
          gap: 20,
          alignItems: "start",
        }}
      >
        <div
          className="col gap-2"
          style={{
            background: "var(--bg-1)",
            border: "1px solid var(--line)",
            borderRadius: 12,
            padding: 14,
            boxShadow: "var(--shadow-1)",
          }}
        >
          <RenderedVariantSvg brief={brief} />
          <span className="t-micro muted" style={{ textAlign: "center" }}>
            Rendered SVG mock · replaced by Gemma + image model when available
          </span>
        </div>
        <BriefPanel fields={fields} rationale={rationale} />
      </div>

      <PredictedLift rows={lift} />
    </section>
  );
}
