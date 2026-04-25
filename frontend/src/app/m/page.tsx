import { api, type ListCreativesArgs } from "@/lib/api";
import { PhoneFeed } from "@/components/design/PhoneFeed";

interface PhoneSearchParams {
  tab?: string;
  limit?: string;
}

const VALID_TABS = new Set(["scale", "watch", "rescue", "cut"]);
const PAGE_SIZE = 60;

export default async function PhoneFeedPage(props: {
  searchParams: Promise<PhoneSearchParams>;
}) {
  const { tab: rawTab, limit: rawLimit } = await props.searchParams;
  const tab = rawTab && VALID_TABS.has(rawTab) ? rawTab : "all";
  const limit = clampLimit(rawLimit);
  const args: ListCreativesArgs = { limit };
  if (tab !== "all") args.tab = tab;
  const listing = await api.listCreatives(args);
  return (
    <PhoneFeed rows={listing.rows} activeTab={tab} total={listing.total} />
  );
}

function clampLimit(raw: string | undefined): number {
  const n = raw ? Number(raw) : PAGE_SIZE;
  if (!Number.isFinite(n) || n < 1) return PAGE_SIZE;
  return Math.min(200, Math.max(10, n));
}
