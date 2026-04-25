import { api } from "@/lib/api";
import type { Campaign } from "@/lib/api";

export async function CockpitHero({
  advertiserId,
  advertiserName,
  campaign,
  start,
  end,
}: {
  advertiserId?: number;
  advertiserName?: string | null;
  campaign?: Campaign | null;
  start?: string;
  end?: string;
}) {
  const counts = await api.tabCounts({
    ...(campaign
      ? { campaign_id: campaign.campaign_id }
      : advertiserId
        ? { advertiser_id: advertiserId }
        : {}),
    start,
    end,
  });
  const refreshedMinutes = 2;
  return (
    <section className="cockpit-hero">
      <div className="col gap-1">
        <h1 className="cockpit-hero-title">
          {campaign ? (
            <>
              {advertiserName ? (
                <span className="cockpit-hero-crumb">{advertiserName} / </span>
              ) : null}
              <span className="cockpit-hero-advertiser">{campaign.app_name}</span>
              <span className="cockpit-hero-sub-theme"> · {campaign.primary_theme}</span>
            </>
          ) : (
            <>
              Hi Maya, here&apos;s your portfolio
              {advertiserName ? (
                <>
                  {" "}at{" "}
                  <span className="cockpit-hero-advertiser">
                    {advertiserName}
                  </span>
                </>
              ) : null}
            </>
          )}
        </h1>
        <p className="cockpit-hero-sub">
          <strong>{counts.scale}</strong> to scale ·{" "}
          <strong>{counts.rescue}</strong> to rescue ·{" "}
          <strong>{counts.cut}</strong> to cut · last refresh{" "}
          {refreshedMinutes} min ago
        </p>
      </div>
    </section>
  );
}
