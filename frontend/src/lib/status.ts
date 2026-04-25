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
  if (!status) return "–";
  if (status in STATUS_TO_VERB) return STATUS_TO_VERB[status as CreativeStatus];
  return status;
}

export function statusToTone(status: string | null | undefined): string {
  if (!status) return "stable";
  if (status in STATUS_TONE) return STATUS_TONE[status as CreativeStatus];
  return "stable";
}

// Health band → verb mapping (mirrors STATUS_TO_VERB, keyed by band).
export const BAND_TO_VERB: Record<string, string> = {
  scale: "Scale",
  watch: "Watch",
  rescue: "Rescue",
  cut: "Cut",
};

export const BAND_TO_TONE: Record<string, string> = {
  scale: "top",
  watch: "stable",
  rescue: "fatigued",
  cut: "cut",
};

export function bandToVerb(band: string | null | undefined): string {
  if (!band) return "–";
  return BAND_TO_VERB[band] ?? band;
}

export function bandToTone(band: string | null | undefined): string {
  if (!band) return "stable";
  return BAND_TO_TONE[band] ?? "stable";
}

// Slice-advisor severity → existing tone tokens.
// critical (red) reuses the cut tone; warning (amber) reuses fatigued;
// opportunity (green) reuses top — keeps the visual language consistent
// with the rest of the cockpit (cf. globals.css colour tokens).
export function severityToTone(
  severity: string | null | undefined,
): "cut" | "fatigued" | "top" | "stable" {
  if (!severity) return "stable";
  if (severity === "critical") return "cut";
  if (severity === "warning") return "fatigued";
  if (severity === "opportunity") return "top";
  return "stable";
}

export function severityLabel(
  severity: string | null | undefined,
): string {
  if (!severity) return "—";
  if (severity === "critical") return "Critical";
  if (severity === "warning") return "Warning";
  if (severity === "opportunity") return "Opportunity";
  return severity;
}

export function actionTypeLabel(actionType: string | null | undefined): string {
  if (!actionType) return "Review";
  // Capitalised industry-canonical verbs.
  const m: Record<string, string> = {
    pause: "Pause",
    rotate: "Rotate",
    scale: "Scale",
    shift: "Shift",
    refresh: "Refresh",
    archive: "Archive",
  };
  return m[actionType] ?? actionType;
}

export function agreeWithLabel(band: string | null | undefined, status: string | null | undefined): boolean | null {
  if (!band || !status) return null;
  const expected: Record<string, string> = {
    top_performer: "scale",
    stable: "watch",
    fatigued: "rescue",
    underperformer: "cut",
  };
  const want = expected[status];
  if (!want) return null;
  return band === want;
}
