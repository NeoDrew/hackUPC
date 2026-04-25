"use client";

import { useTransition } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

import { setActiveWeek } from "@/lib/periodScopeActions";

/**
 * Cumulative week stepper. Selecting "Week N" exposes data from week 1
 * through end of week N to every read site (KPIs, bands, queue, cards),
 * so the demo can replay how the cockpit's recommendations would have
 * looked at any point in the campaign.
 *
 * "All time" clears the cookie and shows the full dataset.
 */
export function PeriodPicker({
  totalWeeks,
  activeWeek,
}: {
  totalWeeks: number;
  activeWeek: number | null;
}) {
  const [isPending, startTransition] = useTransition();
  const week = activeWeek ?? totalWeeks; // when "all time", display as last week
  const isAllTime = activeWeek == null || activeWeek >= totalWeeks;

  function setWeek(n: number | null) {
    if (isPending) return;
    const fd = new FormData();
    if (n != null) fd.set("week", String(n));
    startTransition(() => {
      setActiveWeek(fd);
    });
  }

  function step(delta: number) {
    const next = week + delta;
    if (next < 1) return;
    if (next >= totalWeeks) {
      setWeek(null);
      return;
    }
    setWeek(next);
  }

  return (
    <div className={`week-stepper${isPending ? " pending" : ""}`}>
      <button
        type="button"
        className="week-step-btn"
        aria-label="Previous week"
        disabled={week <= 1 || isPending}
        onClick={() => step(-1)}
      >
        <ChevronLeft size={14} strokeWidth={2} aria-hidden />
      </button>
      <div className="week-stepper-text">
        <span className="week-stepper-label">Period</span>
        <span className="week-stepper-value">
          {isAllTime ? "All time" : `Week ${week} of ${totalWeeks}`}
        </span>
      </div>
      <button
        type="button"
        className="week-step-btn"
        aria-label="Next week"
        disabled={isAllTime || isPending}
        onClick={() => step(+1)}
      >
        <ChevronRight size={14} strokeWidth={2} aria-hidden />
      </button>
      {!isAllTime ? (
        <button
          type="button"
          className="week-stepper-reset"
          onClick={() => setWeek(null)}
          disabled={isPending}
          aria-label="Show all time"
        >
          All time
        </button>
      ) : null}
    </div>
  );
}
