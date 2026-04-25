import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { api, type CreativeRow } from "@/lib/api";
import { creativeImageUrl } from "@/lib/assetUrl";
import { formatCurrency, formatPct, formatRoas } from "@/lib/format";

/**
 * Smart "today's inbox" landing strip — three highest-leverage decisions
 * a marketer should make right now: one creative to refresh (rescue band,
 * highest spend at risk), one to replace (cut band, most $ wasted), one
 * to scale (scale band, top performer). Each card is a one-line decision
 * with a primary action button — first thing on the cockpit, before any
 * KPI tile or table. The cockpit answers "what should I do?" before it
 * shows any data.
 */
export async function CockpitInbox() {
  // Fetch the three highest-leverage rows in parallel.
  const [rescueRes, cutRes, scaleRes] = await Promise.all([
    api
      .listCreatives({ tab: "rescue", sort: "spend_usd", desc: true, limit: 1 })
      .catch(() => null),
    api
      .listCreatives({ tab: "cut", sort: "spend_usd", desc: true, limit: 1 })
      .catch(() => null),
    api
      .listCreatives({ tab: "scale", sort: "roas", desc: true, limit: 1 })
      .catch(() => null),
  ]);

  const rescue = rescueRes?.rows?.[0];
  const cut = cutRes?.rows?.[0];
  const scale = scaleRes?.rows?.[0];

  // If we somehow got nothing back, render nothing (don't ship a broken
  // empty strip into the demo).
  if (!rescue && !cut && !scale) return null;

  return (
    <section className="cockpit-inbox" aria-label="Today's actions">
      {rescue ? <InboxCard kind="rescue" row={rescue} /> : null}
      {cut ? <InboxCard kind="cut" row={cut} /> : null}
      {scale ? <InboxCard kind="scale" row={scale} /> : null}
    </section>
  );
}

type Kind = "rescue" | "cut" | "scale";

const COPY: Record<
  Kind,
  {
    tag: string;
    statClass: string;
    button: string;
    primary: boolean;
    destination: "variant" | "detail";
    line: (r: CreativeRow) => string;
  }
> = {
  rescue: {
    tag: "Refresh",
    statClass: "rescue",
    button: "Improve",
    primary: true,
    destination: "variant",
    line: (r) =>
      `Audience is tired — CTR has fallen to ${formatPct(r.ctr)} after ${r.days_active} days.`,
  },
  cut: {
    tag: "Replace",
    statClass: "cut",
    button: "Replace",
    primary: true,
    destination: "variant",
    line: (r) =>
      `Losing money — only ${formatRoas(r.roas)} ROAS on ${formatCurrency(r.spend_usd, { compact: true })} of spend.`,
  },
  scale: {
    tag: "Scale up",
    statClass: "scale",
    button: "Scale up",
    primary: false,
    destination: "detail",
    line: (r) =>
      `Top performer — ${formatRoas(r.roas)} ROAS, ${formatPct(r.ctr)} CTR. Push more budget behind it.`,
  },
};

function InboxCard({ kind, row }: { kind: Kind; row: CreativeRow }) {
  const copy = COPY[kind];
  const href =
    copy.destination === "variant"
      ? `/creatives/${row.creative_id}/variant?from=${kind}`
      : `/creatives/${row.creative_id}?from=${kind}`;
  const headline = row.headline || `Creative ${row.creative_id}`;
  return (
    <article className={`inbox-card inbox-${kind}`}>
      <div className="inbox-thumb">
        <img src={creativeImageUrl(row.creative_id)} alt="" loading="lazy" />
      </div>
      <div className="inbox-body">
        <span className={`inbox-tag inbox-tag-${kind}`}>
          <span className="inbox-dot" aria-hidden />
          {copy.tag}
        </span>
        <strong className="inbox-headline">{headline}</strong>
        <p className="inbox-line">{copy.line(row)}</p>
      </div>
      <Link
        href={href}
        className={`inbox-cta${copy.primary ? " primary" : ""}`}
        prefetch={false}
      >
        {copy.button}
        <ArrowRight size={14} strokeWidth={1.75} aria-hidden />
      </Link>
    </article>
  );
}
