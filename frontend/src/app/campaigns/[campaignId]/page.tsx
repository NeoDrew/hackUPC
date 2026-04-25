import { Suspense } from "react";
import Link from "next/link";
import { redirect } from "next/navigation";
import { ArrowLeft } from "lucide-react";

import { ActionQueue } from "@/components/design/ActionQueue";
import { AutoScaleBanner } from "@/components/design/AutoScaleBanner";
import { CampaignHealthPanel } from "@/components/design/CampaignHealthPanel";
import { CockpitHero } from "@/components/design/CockpitHero";
import { CreativeTable } from "@/components/design/CreativeTable";
import { CreativeTableSkeleton } from "@/components/design/CreativeTableSkeleton";
import { KpiStrip } from "@/components/design/KpiStrip";
import { KpiStripSkeleton } from "@/components/design/KpiStripSkeleton";
import { TabBar } from "@/components/design/TabBar";
import { api } from "@/lib/api";
import { getActiveAdvertiser } from "@/lib/advertiserScope";
import { listCampaignsWithMetrics } from "@/lib/campaignScope";
import { getActiveWindow } from "@/lib/periodScope";
import { TAB_TO_STATUS, type TabKey } from "@/lib/status";

const TAB_HEADINGS: Record<TabKey, { heading: string; subcopy: string }> = {
  scale: {
    heading: "Creatives recommended to scale",
    subcopy: "Top performers in this campaign. Increase spend or replicate the winning attributes.",
  },
  watch: {
    heading: "Stable creatives to watch",
    subcopy: "Maintain current spend; monitor for fatigue or sudden drops.",
  },
  rescue: {
    heading: "Losing performance: rescue or replace",
    subcopy: "Declining CTR/CVR. Drill in to find the twin and generate a variant.",
  },
  cut: {
    heading: "Underperformers: cut or rework",
    subcopy: "Below cohort baseline since launch. Pause or fundamentally redesign.",
  },
  explore: {
    heading: "All creatives in this campaign",
    subcopy: "The full set of 6 creatives, regardless of band.",
  },
};

interface CampaignSearchParams {
  tab?: string;
  limit?: string;
  sort?: string;
  desc?: string;
  start?: string;
  end?: string;
  vertical?: string;
  format?: string;
}

const PAGE_SIZE = 100;
const SORTABLE = new Set(["ctr", "cvr", "roas", "spend_usd", "days_active", "health"]);

export default async function CampaignDetail(props: {
  params: Promise<{ campaignId: string }>;
  searchParams: Promise<CampaignSearchParams>;
}) {
  const { campaignId: rawId } = await props.params;
  const params = await props.searchParams;
  const campaignId = Number.parseInt(rawId, 10);

  const active = await getActiveAdvertiser();
  if (!active) redirect("/");

  const cookieWindow = await getActiveWindow();
  const start = params.start ?? cookieWindow?.start;
  const end = params.end ?? cookieWindow?.end;

  // Validate that the campaign belongs to the active advertiser. The
  // metrics on the campaign object come back windowed when a week is
  // active, so the health panel + cards reflect the same period as
  // everything else on the page.
  const campaigns = await listCampaignsWithMetrics(active.advertiser_id, {
    start,
    end,
  });
  const campaign = campaigns.find((c) => c.campaign_id === campaignId);
  if (!campaign) redirect("/");

  const limit = clampLimit(params.limit);
  const sort = params.sort && SORTABLE.has(params.sort) ? params.sort : undefined;
  const desc = params.desc !== "false";
  const vertical = params.vertical;
  const format = params.format;
  const rangeKey = `${start ?? ""}|${end ?? ""}`;
  const scopeKey = `c${campaignId}`;

  const tabParam = params.tab;
  const tab: TabKey | null =
    tabParam && (tabParam === "explore" || ["scale", "watch", "rescue", "cut"].includes(tabParam))
      ? (tabParam as TabKey)
      : null;

  const tabCounts = await api
    .tabCounts({ campaign_id: campaignId, start, end })
    .catch(() => ({ scale: 0, watch: 0, rescue: 0, cut: 0, explore: 0 }));

  return (
    <>
      <Link href="/" prefetch={false} className="back-link">
        <ArrowLeft size={14} strokeWidth={2} aria-hidden />
        All campaigns
      </Link>
      <Suspense key={`hero|${rangeKey}|${scopeKey}`} fallback={null}>
        <CockpitHero
          advertiserId={active.advertiser_id}
          advertiserName={active.advertiser_name}
          campaign={campaign}
          start={start}
          end={end}
        />
      </Suspense>
      <Suspense key={`kpis|${rangeKey}|${scopeKey}`} fallback={<KpiStripSkeleton />}>
        <KpiStrip start={start} end={end} campaignId={campaignId} />
      </Suspense>
      {campaign.metrics ? (
        <CampaignHealthPanel metrics={campaign.metrics} />
      ) : null}
      <Suspense key={`autoscale|${rangeKey}|${scopeKey}`} fallback={null}>
        <AutoScaleBanner campaignId={campaignId} start={start} end={end} />
      </Suspense>
      <TabBar counts={tabCounts} basePath={`/campaigns/${campaignId}`} />
      {tab ? (
        <Suspense
          key={`table|${tab}|${sort ?? ""}|${desc ? "d" : "a"}|${limit}|${rangeKey}|${vertical ?? ""}|${format ?? ""}|${scopeKey}`}
          fallback={
            <CreativeTableSkeleton
              heading={TAB_HEADINGS[tab].heading}
              subcopy={TAB_HEADINGS[tab].subcopy}
            />
          }
        >
          <CockpitTable
            campaignId={campaignId}
            tab={tab}
            limit={limit}
            sort={sort}
            desc={desc}
            start={start}
            end={end}
            vertical={vertical}
            format={format}
          />
        </Suspense>
      ) : (
        <Suspense
          key={`queue|${rangeKey}|${scopeKey}`}
          fallback={null}
        >
          <ActionQueue campaignId={campaignId} start={start} end={end} />
        </Suspense>
      )}
    </>
  );
}

async function CockpitTable({
  campaignId,
  tab,
  limit,
  sort,
  desc,
  start,
  end,
  vertical,
  format,
}: {
  campaignId: number;
  tab: TabKey;
  limit: number;
  sort?: string;
  desc: boolean;
  start?: string;
  end?: string;
  vertical?: string;
  format?: string;
}) {
  const listing = await api.listCreatives({
    tab,
    limit,
    sort,
    desc,
    start,
    end,
    vertical,
    format,
    campaign_id: campaignId,
  });
  const headings = TAB_HEADINGS[tab];
  const total = listing.total;
  const shown = listing.rows.length;
  const buildSortHref = (key: string) => {
    const next: Record<string, string> = { tab };
    if (limit !== PAGE_SIZE) next.limit = String(limit);
    if (sort !== key) {
      next.sort = key;
      next.desc = "false";
    } else if (!desc) {
      next.sort = key;
      next.desc = "true";
    }
    if (start) next.start = start;
    if (end) next.end = end;
    const qp = new URLSearchParams(next).toString();
    return `/campaigns/${campaignId}?${qp}`;
  };
  return (
    <CreativeTable
      rows={listing.rows}
      heading={headings.heading}
      subcopy={headings.subcopy}
      from={tab}
      tab={tab}
      total={total}
      range={{ start, end }}
      sortState={{ sort, desc, buildHref: buildSortHref }}
      footer={
        shown < total ? (
          <ShowMoreFooter
            campaignId={campaignId}
            tab={tab}
            shown={shown}
            total={total}
            currentLimit={limit}
            sort={sort}
            desc={desc}
            start={start}
            end={end}
          />
        ) : (
          <p className="t-micro muted" style={{ padding: "10px 16px" }}>
            Showing all {total} creatives in this view.
          </p>
        )
      }
    />
  );
}

function ShowMoreFooter({
  campaignId,
  tab,
  shown,
  total,
  currentLimit,
  sort,
  desc,
  start,
  end,
}: {
  campaignId: number;
  tab: TabKey;
  shown: number;
  total: number;
  currentLimit: number;
  sort?: string;
  desc: boolean;
  start?: string;
  end?: string;
}) {
  const next = Math.min(currentLimit + PAGE_SIZE, total);
  const params: Record<string, string> = { tab, limit: String(next) };
  if (sort) {
    params.sort = sort;
    params.desc = desc ? "true" : "false";
  }
  if (start) params.start = start;
  if (end) params.end = end;
  const href = `/campaigns/${campaignId}?${new URLSearchParams(params).toString()}`;
  return (
    <div
      className="row between center"
      style={{ padding: "10px 16px", borderTop: "1px solid var(--line-soft)" }}
    >
      <span className="t-micro muted">
        Showing {shown} of {total}
      </span>
      <a className="btn dense" href={href}>
        Show {Math.min(PAGE_SIZE, total - shown)} more
      </a>
    </div>
  );
}

function clampLimit(raw: string | undefined): number {
  const n = raw ? Number(raw) : PAGE_SIZE;
  if (!Number.isFinite(n) || n < 1) return PAGE_SIZE;
  return Math.min(2000, Math.max(PAGE_SIZE, n));
}

export { TAB_TO_STATUS };
