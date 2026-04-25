import Link from "next/link";
import { notFound } from "next/navigation";

import { api } from "@/lib/api";
import { DiffTable } from "@/components/design/DiffTable";
import { PreviewChip } from "@/components/design/PreviewChip";
import { TwinPanel } from "@/components/design/TwinPanel";
import { VisionInsightCard } from "@/components/design/VisionInsightCard";
import { WinningPatternsCard } from "@/components/design/WinningPatternsCard";

export default async function TwinPage(
  props: PageProps<"/creatives/[creativeId]/twin">,
) {
  const { creativeId } = await props.params;
  const id = Number(creativeId);
  if (!Number.isFinite(id)) notFound();

  const sp = await props.searchParams;
  const start = typeof sp?.start === "string" ? sp.start : undefined;
  const end = typeof sp?.end === "string" ? sp.end : undefined;
  const rangeQs = new URLSearchParams();
  if (start) rangeQs.set("start", start);
  if (end) rangeQs.set("end", end);
  const rangeSuffix = rangeQs.toString() ? `?${rangeQs.toString()}` : "";

  let twin;
  try {
    twin = await api.getTwin(id, { start, end });
  } catch {
    notFound();
  }

  const [source, winner, patterns] = await Promise.all([
    api.getCreative(twin.fatigued_id, { start, end }),
    api.getCreative(twin.winner_id, { start, end }),
    api.getWinningPatterns(twin.fatigued_id).catch(() => null),
  ]);

  return (
    <section
      className="col gap-5"
      style={{ paddingTop: 16, maxWidth: 1100, margin: "0 auto" }}
    >
      <header className="row between center" style={{ flexWrap: "wrap", gap: 12 }}>
        <div className="col gap-1">
          <div className="row center gap-3">
            <Link href={`/creatives/${id}${rangeSuffix}`} className="btn dense">
              ← Back to detail
            </Link>
            <span className="filter-chip">
              {Math.round(twin.similarity * 100)}% similar · {twin.segment.vertical} ×{" "}
              {twin.segment.format}
            </span>
            {twin.is_stub ? <PreviewChip /> : null}
          </div>
          <h1 className="t-page" style={{ margin: 0 }}>
            Why is your fatigued creative losing to its twin?
          </h1>
          <p className="t-body muted">{twin.diffs.length} high-impact attribute differences</p>
        </div>
        <div className="row center gap-2">
          <button className="btn dense" type="button">
            Save
          </button>
          <Link href={`/creatives/${id}/variant${rangeSuffix}`} className="btn primary">
            Generate next variant →
          </Link>
        </div>
      </header>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 48px 1fr",
          gap: 16,
          alignItems: "stretch",
        }}
      >
        <TwinPanel creative={source} role="yours" />
        <div className="col center" style={{ justifyContent: "center" }}>
          <div
            style={{
              width: 40,
              height: 40,
              borderRadius: 999,
              background: "var(--bg-1)",
              border: "1px solid var(--line)",
              display: "grid",
              placeItems: "center",
              boxShadow: "var(--shadow-1)",
              fontSize: 16,
              color: "var(--accent)",
            }}
          >
            ⟷
          </div>
        </div>
        <TwinPanel creative={winner} role="twin" />
      </div>

      <VisionInsightCard insight={twin.vision_insight} />

      <section className="col gap-2">
        <h3 className="t-section">Attribute diffs · where the winner pulls ahead</h3>
        <DiffTable diffs={twin.diffs} />
      </section>

      <section className="col gap-2">
        <div className="row between center">
          <h3 className="t-section">Winning patterns in this cohort</h3>
          {patterns ? (
            <span className="t-micro muted">
              {patterns.winner_count} of {patterns.cohort_size} top performers
              · {patterns.segment.vertical} / {patterns.segment.format}
            </span>
          ) : null}
        </div>
        <WinningPatternsCard patterns={patterns?.patterns ?? []} />
      </section>
    </section>
  );
}
