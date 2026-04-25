import type { components, paths } from "@/types/api";

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8001";

async function fetchJSON<T>(path: string): Promise<T> {
  const url = `${BASE}${path}`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`GET ${url} → ${res.status}`);
  }
  return (await res.json()) as T;
}

export type Advertiser = components["schemas"]["Advertiser"];
export type Campaign = components["schemas"]["Campaign"];
export type CreativeListItem = components["schemas"]["CreativeListItem"];
export type CreativeDetail = components["schemas"]["CreativeDetail"];
export type Quadrant = components["schemas"]["Quadrant"];
export type Saturation = components["schemas"]["Saturation"];
export type CreativeListResponse =
  components["schemas"]["CreativeListResponse"];
export type CreativeTimeseries = components["schemas"]["CreativeTimeseries"];
export type TimeseriesPoint = components["schemas"]["TimeseriesPoint"];
export type CreativeRow = components["schemas"]["CreativeRow"];
export type PortfolioKPIs = components["schemas"]["PortfolioKPIs"];
export type TabCounts = components["schemas"]["TabCounts"];
export type HealthComponents = components["schemas"]["HealthComponents"];
export type HealthBreakdown = components["schemas"]["HealthBreakdown"];
export type HealthDiagnostics = components["schemas"]["HealthDiagnostics"];
export type TwinSummary = components["schemas"]["TwinSummary"];
export type TwinDiff = components["schemas"]["TwinDiff"];
export type VisionInsight = components["schemas"]["VisionInsight"];

type AdvertisersResponse =
  paths["/api/advertisers"]["get"]["responses"]["200"]["content"]["application/json"];
type CampaignsResponse =
  paths["/api/advertisers/{advertiser_id}/campaigns"]["get"]["responses"]["200"]["content"]["application/json"];
type CampaignCreativesResponse =
  paths["/api/campaigns/{campaign_id}/creatives"]["get"]["responses"]["200"]["content"]["application/json"];

export interface ListCreativesArgs {
  tab?: string;
  status?: string;
  vertical?: string;
  format?: string;
  sort?: string;
  desc?: boolean;
  limit?: number;
}

function buildQuery(
  params: Record<string, string | number | boolean | undefined>,
): string {
  const out = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "") continue;
    out.set(k, String(v));
  }
  const s = out.toString();
  return s ? `?${s}` : "";
}

export const api = {
  // Legacy hierarchical browser (kept for /debug/ routes).
  listAdvertisers: () => fetchJSON<AdvertisersResponse>("/api/advertisers"),
  getAdvertiser: (id: number) =>
    fetchJSON<Advertiser>(`/api/advertisers/${id}`),
  listCampaigns: (advertiserId: number) =>
    fetchJSON<CampaignsResponse>(`/api/advertisers/${advertiserId}/campaigns`),
  getCampaign: (id: number) => fetchJSON<Campaign>(`/api/campaigns/${id}`),
  listCreativesForCampaign: (campaignId: number) =>
    fetchJSON<CampaignCreativesResponse>(
      `/api/campaigns/${campaignId}/creatives`,
    ),

  // Cockpit / portfolio.
  portfolioKpis: () => fetchJSON<PortfolioKPIs>("/api/portfolio/kpis"),
  tabCounts: () => fetchJSON<TabCounts>("/api/portfolio/tab-counts"),
  healthDiagnostics: () =>
    fetchJSON<HealthDiagnostics>("/api/portfolio/health-diagnostics"),
  listCreatives: (args: ListCreativesArgs = {}) =>
    fetchJSON<CreativeListResponse>(
      `/api/creatives${buildQuery(args as Record<string, string | number | boolean | undefined>)}`,
    ),

  // Drawer / detail.
  getCreative: (id: number) =>
    fetchJSON<CreativeDetail>(`/api/creatives/${id}`),
  getCreativeTimeseries: (id: number) =>
    fetchJSON<CreativeTimeseries>(`/api/creatives/${id}/timeseries`),

  // Twin (stub).
  getTwin: (id: number) => fetchJSON<TwinSummary>(`/api/creatives/${id}/twin`),
};
