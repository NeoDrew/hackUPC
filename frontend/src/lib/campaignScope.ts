import { api, type Campaign } from "@/lib/api";

const _campaignsByAdvertiser: Map<number, Campaign[]> = new Map();
// Cache windowed metrics by (advertiserId, start, end). Lifetime sits at "all|all".
const _campaignsWithMetricsCache: Map<string, Campaign[]> = new Map();

function metricsKey(
  advertiserId: number,
  start?: string,
  end?: string,
): string {
  return `${advertiserId}|${start ?? "all"}|${end ?? "all"}`;
}

export async function listCampaignsForAdvertiser(
  advertiserId: number,
): Promise<Campaign[]> {
  const cached = _campaignsByAdvertiser.get(advertiserId);
  if (cached) return cached;
  const list = await api
    .listCampaigns(advertiserId)
    .catch(() => [] as Campaign[]);
  const sorted = [...list].sort((a, b) =>
    a.app_name.localeCompare(b.app_name),
  );
  _campaignsByAdvertiser.set(advertiserId, sorted);
  return sorted;
}

export async function listCampaignsWithMetrics(
  advertiserId: number,
  opts: { start?: string; end?: string } = {},
): Promise<Campaign[]> {
  const key = metricsKey(advertiserId, opts.start, opts.end);
  const cached = _campaignsWithMetricsCache.get(key);
  if (cached) return cached;
  const list = await api
    .listCampaigns(advertiserId, {
      with_metrics: true,
      start: opts.start,
      end: opts.end,
    })
    .catch(() => [] as Campaign[]);
  const sorted = [...list].sort((a, b) =>
    (b.metrics?.health ?? 0) - (a.metrics?.health ?? 0),
  );
  _campaignsWithMetricsCache.set(key, sorted);
  return sorted;
}

export async function getCampaignForAdvertiser(
  advertiserId: number | null,
  campaignId: number | null,
): Promise<Campaign | null> {
  if (advertiserId == null || campaignId == null) return null;
  const list = await listCampaignsForAdvertiser(advertiserId);
  return list.find((c) => c.campaign_id === campaignId) ?? null;
}
