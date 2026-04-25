import { cookies } from "next/headers";

import { api, type Advertiser } from "@/lib/api";

export const ADVERTISER_COOKIE = "smadex_advertiser_id";

let _advertisersCache: Advertiser[] | null = null;

async function loadAdvertisers(): Promise<Advertiser[]> {
  if (_advertisersCache !== null) return _advertisersCache;
  const list = await api.listAdvertisers().catch(() => [] as Advertiser[]);
  const sorted = [...list].sort((a, b) =>
    a.advertiser_name.localeCompare(b.advertiser_name),
  );
  _advertisersCache = sorted;
  return sorted;
}

export async function listAdvertisersForPicker(): Promise<Advertiser[]> {
  return loadAdvertisers();
}

export async function getActiveAdvertiserId(): Promise<number | null> {
  const store = await cookies();
  const raw = store.get(ADVERTISER_COOKIE)?.value;
  if (raw) {
    const n = Number.parseInt(raw, 10);
    if (Number.isFinite(n) && n > 0) return n;
  }
  // Auto-pick the first advertiser by name when the cookie is missing.
  // Keeps the demo fast — no onboarding gate, picker still lets the
  // user swap profiles immediately.
  const list = await loadAdvertisers();
  return list[0]?.advertiser_id ?? null;
}

export async function getActiveAdvertiser(): Promise<Advertiser | null> {
  const id = await getActiveAdvertiserId();
  if (id == null) return null;
  const list = await loadAdvertisers();
  return list.find((a) => a.advertiser_id === id) ?? null;
}

