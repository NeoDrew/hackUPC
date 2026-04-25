import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { api, type CreativeRow } from "@/lib/api";
import { creativeImageUrl } from "@/lib/assetUrl";
import { formatCurrency, formatPct, formatRoas } from "@/lib/format";

const QUEUE_SIZE = 12;

/**
 * The Action page's primary surface — a single ranked queue of creatives
 * that need a human decision (rescue + cut bands only). Top performers
 * are handled passively by AutoScaleBanner above; the queue is reserved
 * for things only the marketer can call.
 *
 * Ranking: top-N rescue + top-N cut by spend descending, merged and
 * re-sorted by spend so the most expensive decisions surface first.
 */
export async function ActionQueue() {
  const half = Math.ceil(QUEUE_SIZE / 2);
  const [rescueRes, cutRes] = await Promise.all([
    api
      .listCreatives({ tab: "rescue", sort: "spend_usd", desc: true, limit: half })
      .catch(() => null),
    api
      .listCreatives({ tab: "cut", sort: "spend_usd", desc: true, limit: half })
      .catch(() => null),
  ]);

  const rescueRows = (rescueRes?.rows ?? []).map((r) => ({
    row: r,
    kind: "rescue" as const,
  }));
  const cutRows = (cutRes?.rows ?? []).map((r) => ({
    row: r,
    kind: "cut" as const,
  }));

  const merged = [...rescueRows, ...cutRows]
    .sort((a, b) => (b.row.spend_usd ?? 0) - (a.row.spend_usd ?? 0))
    .slice(0, QUEUE_SIZE);

  const totalRescue = rescueRes?.total ?? 0;
  const totalCut = cutRes?.total ?? 0;
  const totalRemaining = Math.max(0, totalRescue + totalCut - merged.length);

  if (merged.length === 0) {
    return (
      <section className="action-queue empty">
        <p className="t-body muted">
          Nothing needs your attention right now — your portfolio is healthy.
        </p>
      </section>
    );
  }

  return (
    <section className="action-queue" aria-label="Today's actions">
      <header className="action-queue-head">
        <h2 className="t-section">
          {merged.length} {merged.length === 1 ? "creative needs" : "creatives need"} your attention
        </h2>
        <p className="t-body muted">
          Ranked by spend at risk. Top performers are auto-scaled — see the
          banner above.
        </p>
      </header>
      <ol className="action-queue-list">
        {merged.map(({ row, kind }) => (
          <ActionRow key={row.creative_id} kind={kind} row={row} />
        ))}
      </ol>
      {totalRemaining > 0 ? (
        <footer className="action-queue-foot">
          <Link
            href={`/?tab=${totalRescue >= totalCut ? "rescue" : "cut"}`}
            prefetch={false}
            className="action-queue-more"
          >
            Show all {totalRescue + totalCut} actions →
          </Link>
        </footer>
      ) : null}
    </section>
  );
}

const COPY: Record<
  "rescue" | "cut",
  {
    tag: string;
    button: string;
    line: (r: CreativeRow) => string;
  }
> = {
  rescue: {
    tag: "Refresh",
    button: "Improve",
    line: (r) =>
      `Audience is tired — CTR has fallen to ${formatPct(r.ctr)} after ${r.days_active} days. ${formatCurrency(r.spend_usd, { compact: true })} spent.`,
  },
  cut: {
    tag: "Replace",
    button: "Replace",
    line: (r) =>
      `Losing money — ${formatRoas(r.roas)} ROAS on ${formatCurrency(r.spend_usd, { compact: true })} of spend.`,
  },
};

function ActionRow({
  kind,
  row,
}: {
  kind: "rescue" | "cut";
  row: CreativeRow;
}) {
  const copy = COPY[kind];
  const variantHref = `/creatives/${row.creative_id}/variant?from=${kind}`;
  const detailHref = `/creatives/${row.creative_id}?from=${kind}`;
  const headline = row.headline || `Creative ${row.creative_id}`;
  return (
    <li className={`action-row action-row-${kind}`}>
      <Link href={detailHref} prefetch={false} className="action-row-thumb">
        <img src={creativeImageUrl(row.creative_id)} alt="" loading="lazy" />
      </Link>
      <div className="action-row-body">
        <div className="action-row-meta">
          <span className={`action-row-tag action-row-tag-${kind}`}>
            <span className="action-row-dot" aria-hidden />
            {copy.tag}
          </span>
          <span className="action-row-cohort">
            {row.advertiser_name} · {row.vertical} · {row.format} · #{row.creative_id}
          </span>
        </div>
        <Link href={detailHref} prefetch={false} className="action-row-headline">
          {headline}
        </Link>
        <p className="action-row-line">{copy.line(row)}</p>
      </div>
      <Link
        href={variantHref}
        prefetch={false}
        className="action-row-cta primary"
      >
        {copy.button}
        <ArrowRight size={14} strokeWidth={1.75} aria-hidden />
      </Link>
    </li>
  );
}
