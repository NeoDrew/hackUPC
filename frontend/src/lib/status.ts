export type CreativeStatus =
  | "top_performer"
  | "stable"
  | "fatigued"
  | "underperformer";

export type TabKey = "scale" | "watch" | "rescue" | "cut" | "explore";

export const TAB_TO_STATUS: Record<TabKey, CreativeStatus | null> = {
  scale: "top_performer",
  watch: "stable",
  rescue: "fatigued",
  cut: "underperformer",
  explore: null,
};

export const STATUS_TO_TAB: Record<CreativeStatus, TabKey> = {
  top_performer: "scale",
  stable: "watch",
  fatigued: "rescue",
  underperformer: "cut",
};

export const STATUS_TO_VERB: Record<CreativeStatus, string> = {
  top_performer: "Scale",
  stable: "Watch",
  fatigued: "Rescue",
  underperformer: "Cut",
};

export const STATUS_TONE: Record<CreativeStatus, "top" | "stable" | "fatigued" | "cut"> = {
  top_performer: "top",
  stable: "stable",
  fatigued: "fatigued",
  underperformer: "cut",
};

export const TABS: { key: TabKey; label: string; urgent: boolean; utility?: boolean }[] = [
  { key: "scale", label: "Scale", urgent: false },
  { key: "watch", label: "Watch", urgent: false },
  { key: "rescue", label: "Rescue", urgent: true },
  { key: "cut", label: "Cut", urgent: true },
  { key: "explore", label: "Explore", urgent: false, utility: true },
];

export function statusToVerb(status: string | null | undefined): string {
  if (!status) return "—";
  if (status in STATUS_TO_VERB) return STATUS_TO_VERB[status as CreativeStatus];
  return status;
}

export function statusToTone(status: string | null | undefined): string {
  if (!status) return "stable";
  if (status in STATUS_TONE) return STATUS_TONE[status as CreativeStatus];
  return "stable";
}
