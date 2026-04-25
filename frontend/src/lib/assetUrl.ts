const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8001";

export function creativeImageUrl(creativeId: number): string {
  return `${BASE}/assets/creative_${creativeId}.png`;
}
