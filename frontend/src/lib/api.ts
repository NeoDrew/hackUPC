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
export type CampaignMetrics = components["schemas"]["CampaignMetrics"];
export type CampaignHealthComponents = components["schemas"]["CampaignHealthComponents"];
export type CreativeListItem = components["schemas"]["CreativeListItem"];
export type CreativeDetail = components["schemas"]["CreativeDetail"];
export type Quadrant = components["schemas"]["Quadrant"];
export type Saturation = components["schemas"]["Saturation"];
export type CreativeListResponse =
  components["schemas"]["CreativeListResponse"];
export type SearchHit = components["schemas"]["SearchHit"];
export type SearchResponse = components["schemas"]["SearchResponse"];
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
export type VariantBriefResponse = components["schemas"]["VariantBriefResponse"];
export type WinningPattern = components["schemas"]["WinningPattern"];
export type WinningPatternsResponse = components["schemas"]["WinningPatternsResponse"];

type AdvertisersResponse =
  paths["/api/advertisers"]["get"]["responses"]["200"]["content"]["application/json"];
type CampaignsResponse =
  paths["/api/advertisers/{advertiser_id}/campaigns"]["get"]["responses"]["200"]["content"]["application/json"];
type CampaignCreativesResponse =
  paths["/api/campaigns/{campaign_id}/creatives"]["get"]["responses"]["200"]["content"]["application/json"];

export interface ListCreativesArgs {
  tab?: string;
  status?: string;
  band?: string;
  vertical?: string;
  format?: string;
  theme?: string;
  hook_type?: string;
  country?: string;
  os?: string;
  sort?: string;
  desc?: boolean;
  limit?: number;
  start?: string;
  end?: string;
  advertiser_id?: number;
  campaign_id?: number;
}

export interface ScopedRange extends DateRange {
  advertiser_id?: number;
  campaign_id?: number;
}

export interface CampaignsListOpts extends DateRange {
  with_metrics?: boolean;
}

export interface DateRange {
  start?: string;
  end?: string;
}

function buildQuery(
  params: Record<string, string | number | boolean | undefined> | object,
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
  listCampaigns: (advertiserId: number, opts: CampaignsListOpts = {}) =>
    fetchJSON<CampaignsResponse>(
      `/api/advertisers/${advertiserId}/campaigns${buildQuery(opts)}`,
    ),
  getCampaign: (id: number) => fetchJSON<Campaign>(`/api/campaigns/${id}`),
  listCreativesForCampaign: (campaignId: number) =>
    fetchJSON<CampaignCreativesResponse>(
      `/api/campaigns/${campaignId}/creatives`,
    ),

  // Cockpit / portfolio.
  portfolioKpis: (scope: ScopedRange = {}) =>
    fetchJSON<PortfolioKPIs>(`/api/portfolio/kpis${buildQuery(scope)}`),
  tabCounts: (scope: ScopedRange = {}) =>
    fetchJSON<TabCounts>(`/api/portfolio/tab-counts${buildQuery(scope)}`),
  listCreatives: (args: ListCreativesArgs = {}) =>
    fetchJSON<CreativeListResponse>(
      `/api/creatives${buildQuery(args as Record<string, string | number | boolean | undefined>)}`,
    ),

  // Drawer / detail.
  getCreative: (id: number, range: DateRange = {}) =>
    fetchJSON<CreativeDetail>(`/api/creatives/${id}${buildQuery(range)}`),
  getCreativeTimeseries: (id: number) =>
    fetchJSON<CreativeTimeseries>(`/api/creatives/${id}/timeseries`),

  // Twin.
  getTwin: (id: number, range: DateRange = {}) =>
    fetchJSON<TwinSummary>(`/api/creatives/${id}/twin${buildQuery(range)}`),

  // Variant brief (Gemma-generated; falls back to template server-side).
  getVariantBrief: (id: number) =>
    fetchJSON<VariantBriefResponse>(`/api/creatives/${id}/variant-brief`),

  // Cohort attribute prevalence — deterministic count, no LLM.
  getWinningPatterns: (id: number) =>
    fetchJSON<WinningPatternsResponse>(`/api/creatives/${id}/winning-patterns`),

  // Search.
  search: (q: string, limit = 8) =>
    fetchJSON<SearchResponse>(
      `/api/search?q=${encodeURIComponent(q)}&limit=${limit}`,
    ),

  // Variant queue (mock — process-lifetime in-memory).
  applyVariant: async (creativeId: number, rationale?: string) => {
    const res = await fetch(`${BASE}/api/creatives/${creativeId}/apply-variant`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ rationale: rationale ?? null }),
    });
    if (!res.ok) throw new Error(`POST apply-variant ${creativeId} → ${res.status}`);
    return (await res.json()) as {
      creative_id: number;
      queued: boolean;
      entry: AppliedVariant | null;
    };
  },
  undoVariant: async (creativeId: number) => {
    const res = await fetch(`${BASE}/api/creatives/${creativeId}/apply-variant`, {
      method: "DELETE",
    });
    if (!res.ok) throw new Error(`DELETE apply-variant ${creativeId} → ${res.status}`);
    return (await res.json()) as {
      creative_id: number;
      queued: boolean;
      entry: AppliedVariant | null;
    };
  },
  listAppliedVariants: () =>
    fetchJSON<AppliedVariant[]>("/api/applied-variants"),
};

export interface AppliedVariant {
  creative_id: number;
  rationale?: string | null;
  queued_at: string;
  eta_hours: number;
}

// ── Slice advisor ──────────────────────────────────────────────────
//
// Hand-written types — the openapi-typescript regen happens via a CI
// step we may not run before the demo, so these mirror the backend
// SliceRecommendation pydantic model directly. Update both together.

export type SliceActionType =
  | "pause"
  | "rotate"
  | "scale"
  | "shift"
  | "refresh"
  | "archive";

export type SliceSeverity = "critical" | "warning" | "opportunity";

export interface SliceRecommendation {
  recommendation_id: string;
  creative_id: number;
  country: string;
  os: string; // "Android" | "iOS" | "*"
  advertiser_id: number;
  campaign_id: number;
  action_type: SliceActionType;
  severity: SliceSeverity;
  headline: string;
  rationale: string;
  est_daily_impact_usd: number;
  trigger_magnitude: Record<string, number>;
  is_polished: boolean;
  applied_at?: string | null;
  snoozed_until?: string | null;
  dismissed_at?: string | null;
  // Extras for some action types — Pydantic extra="allow" passes these through.
  cluster_name?: string;
  decaying_countries_csv?: string;
  sibling_creative_id?: number;
  receiver_creative_id?: number;
  receiver_country?: string;
  receiver_os?: string;
  shift_usd?: number;
  peer_format?: string;
  my_format?: string;
}

export interface RecommendationsList {
  recommendations: SliceRecommendation[];
  total_daily_impact_usd: number;
  counts_by_severity: Record<string, number>;
  counts_by_action_type: Record<string, number>;
}

export interface RecommendationsScope {
  advertiser_id?: number;
  campaign_id?: number;
  severity?: SliceSeverity;
  action_type?: SliceActionType;
  include_inactive?: boolean;
}

type RecommendationActionResponse = {
  recommendation_id: string;
  applied: boolean;
  entry: SliceRecommendation | null;
};

export const listRecommendations = (scope: RecommendationsScope = {}) =>
  fetchJSON<RecommendationsList>(
    `/api/recommendations${buildQuery(scope)}`,
  );

export const applyRecommendation = async (
  recommendationId: string,
): Promise<RecommendationActionResponse> => {
  const res = await fetch(
    `${BASE}/api/recommendations/${recommendationId}/apply`,
    { method: "POST" },
  );
  if (!res.ok)
    throw new Error(`POST apply ${recommendationId} → ${res.status}`);
  return (await res.json()) as RecommendationActionResponse;
};

export const snoozeRecommendation = async (
  recommendationId: string,
  until: string,
): Promise<RecommendationActionResponse> => {
  const res = await fetch(
    `${BASE}/api/recommendations/${recommendationId}/snooze`,
    {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ until }),
    },
  );
  if (!res.ok)
    throw new Error(`POST snooze ${recommendationId} → ${res.status}`);
  return (await res.json()) as RecommendationActionResponse;
};

export const dismissRecommendation = async (
  recommendationId: string,
): Promise<RecommendationActionResponse> => {
  const res = await fetch(
    `${BASE}/api/recommendations/${recommendationId}/dismiss`,
    { method: "POST" },
  );
  if (!res.ok)
    throw new Error(`POST dismiss ${recommendationId} → ${res.status}`);
  return (await res.json()) as RecommendationActionResponse;
};
