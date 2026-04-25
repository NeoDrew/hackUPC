import { Suspense } from "react";

import { AutoScaleBanner } from "@/components/design/AutoScaleBanner";
import { CampaignGrid } from "@/components/design/CampaignGrid";
import { CockpitHero } from "@/components/design/CockpitHero";
import { KpiStrip } from "@/components/design/KpiStrip";
import { KpiStripSkeleton } from "@/components/design/KpiStripSkeleton";
import { getActiveAdvertiser } from "@/lib/advertiserScope";
import { getActiveWindow } from "@/lib/periodScope";

interface AdvertiserOverviewSearchParams {
  start?: string;
  end?: string;
}

export default async function AdvertiserOverview(props: {
  searchParams: Promise<AdvertiserOverviewSearchParams>;
}) {
  const params = await props.searchParams;
  // Cookie-driven week wins over URL params; URL is a power-user override.
  const cookieWindow = await getActiveWindow();
  const start = params.start ?? cookieWindow?.start;
  const end = params.end ?? cookieWindow?.end;
  const rangeKey = `${start ?? ""}|${end ?? ""}`;

  const active = await getActiveAdvertiser();
  const advertiserId = active?.advertiser_id;
  const advertiserName = active?.advertiser_name ?? null;
  const scopeKey = advertiserId ?? "all";

  return (
    <>
      <Suspense key={`hero|${rangeKey}|${scopeKey}`} fallback={null}>
        <CockpitHero
          advertiserId={advertiserId}
          advertiserName={advertiserName}
          start={start}
          end={end}
        />
      </Suspense>
      <Suspense key={`kpis|${rangeKey}|${scopeKey}`} fallback={<KpiStripSkeleton />}>
        <KpiStrip start={start} end={end} advertiserId={advertiserId} />
      </Suspense>
      <Suspense key={`autoscale|${rangeKey}|${scopeKey}`} fallback={null}>
        <AutoScaleBanner advertiserId={advertiserId} start={start} end={end} />
      </Suspense>
      {advertiserId ? (
        <Suspense key={`grid|${scopeKey}|${rangeKey}`} fallback={null}>
          <CampaignGrid advertiserId={advertiserId} start={start} end={end} />
        </Suspense>
      ) : null}
    </>
  );
}
