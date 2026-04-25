import { cookies } from "next/headers";

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8001";

export const WEEK_COOKIE = "smadex_week";

export interface DatasetBounds {
  start: string;
  end: string;
  total_days: number;
  total_weeks: number;
}

let _boundsCache: DatasetBounds | null = null;

export async function getDatasetBounds(): Promise<DatasetBounds> {
  if (_boundsCache) return _boundsCache;
  try {
    const res = await fetch(`${BASE}/api/portfolio/dataset-bounds`, {
      cache: "no-store",
    });
    if (!res.ok) throw new Error(`bounds ${res.status}`);
    const data = (await res.json()) as DatasetBounds;
    _boundsCache = data;
    return data;
  } catch {
    // Hardcoded fallback matches the dataset shape the team is shipping with.
    return {
      start: "2026-01-01",
      end: "2026-03-16",
      total_days: 75,
      total_weeks: 11,
    };
  }
}

export async function getActiveWeek(): Promise<number | null> {
  const store = await cookies();
  const raw = store.get(WEEK_COOKIE)?.value;
  if (!raw) return null;
  const n = Number.parseInt(raw, 10);
  if (!Number.isFinite(n) || n <= 0) return null;
  return n;
}

function addDays(iso: string, days: number): string {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

/**
 * Cumulative window for week N: from dataset start through end of week N.
 * Returns ``undefined`` when no week is set (lifetime). Caps at dataset end
 * so picking week 11 (or beyond) is equivalent to "all time".
 */
export async function getActiveWindow(): Promise<
  { start: string; end: string } | undefined
> {
  const week = await getActiveWeek();
  if (week == null) return undefined;
  const bounds = await getDatasetBounds();
  if (week >= bounds.total_weeks) {
    // Same as lifetime — let backend short-circuit via is_full_range.
    return undefined;
  }
  const endIdx = Math.min(week * 7 - 1, bounds.total_days - 1);
  return { start: bounds.start, end: addDays(bounds.start, endIdx) };
}
