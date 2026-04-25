import Link from "next/link";
import { Suspense } from "react";

import { AdvisorQueue } from "@/components/design/AdvisorQueue";
import { getActiveAdvertiser } from "@/lib/advertiserScope";
import type {
  SliceActionType,
  SliceSeverity,
} from "@/lib/api";

interface ActionsSearchParams {
  severity?: string;
  action_type?: string;
}

const SEVERITIES: { key: SliceSeverity | "all"; label: string }[] = [
  { key: "all", label: "All" },
  { key: "critical", label: "Critical" },
  { key: "warning", label: "Warning" },
  { key: "opportunity", label: "Opportunity" },
];

const ACTION_TYPES: { key: SliceActionType | "all"; label: string }[] = [
  { key: "all", label: "All actions" },
  { key: "pause", label: "Pause" },
  { key: "rotate", label: "Rotate" },
  { key: "scale", label: "Scale" },
  { key: "shift", label: "Shift" },
  { key: "refresh", label: "Refresh" },
  { key: "archive", label: "Archive" },
];

export default async function ActionsPage(props: {
  searchParams: Promise<ActionsSearchParams>;
}) {
  const params = await props.searchParams;
  const severity =
    params.severity && params.severity !== "all"
      ? (params.severity as SliceSeverity)
      : undefined;
  const actionType =
    params.action_type && params.action_type !== "all"
      ? (params.action_type as SliceActionType)
      : undefined;

  const active = await getActiveAdvertiser();
  const advertiserId = active?.advertiser_id;

  // URL helpers — flip a single filter, leave the rest.
  const buildHref = (key: keyof ActionsSearchParams, val: string) => {
    const next = new URLSearchParams();
    if (params.severity) next.set("severity", params.severity);
    if (params.action_type) next.set("action_type", params.action_type);
    if (val === "all") next.delete(key);
    else next.set(key, val);
    const qs = next.toString();
    return qs ? `/actions?${qs}` : "/actions";
  };

  const currentSeverity = params.severity || "all";
  const currentActionType = params.action_type || "all";

  return (
    <div className="actions-page">
      <header className="actions-page-head">
        <h1 className="t-section">Advisor</h1>
        <p className="t-body muted">
          Per-(creative · country · OS) recommendations, ranked by est.
          daily impact. Apply one-click, snooze for later, or dismiss.
        </p>
      </header>

      <nav className="actions-page-filters" aria-label="Severity">
        {SEVERITIES.map((s) => (
          <Link
            key={s.key}
            href={buildHref("severity", s.key)}
            prefetch={false}
            className="actions-page-filter"
            aria-current={currentSeverity === s.key ? "page" : undefined}
          >
            {s.label}
          </Link>
        ))}
      </nav>

      <nav className="actions-page-filters" aria-label="Action type">
        {ACTION_TYPES.map((a) => (
          <Link
            key={a.key}
            href={buildHref("action_type", a.key)}
            prefetch={false}
            className="actions-page-filter"
            aria-current={currentActionType === a.key ? "page" : undefined}
          >
            {a.label}
          </Link>
        ))}
      </nav>

      <Suspense
        key={`queue|${advertiserId ?? "all"}|${severity ?? "all"}|${actionType ?? "all"}`}
        fallback={null}
      >
        <AdvisorQueue
          advertiserId={advertiserId}
          severity={severity}
          actionType={actionType}
        />
      </Suspense>
    </div>
  );
}
