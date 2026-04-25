"use client";

import { useEffect, useState, useTransition } from "react";

import { api } from "@/lib/api";

/** Apply / undo bar for the variant page.
 *
 * Default state: a primary "Apply this variant →" button.
 * After click: green banner "Queued to replace the live ad in 24h" with an
 * Undo link that DELETEs the queued entry. We re-fetch the queue on mount
 * so a refresh of the variant page restores the banner if it was previously
 * applied. Mock mutation — see backend/app/routes/actions.py.
 */
export function ApplyVariantBar({
  creativeId,
  rationale,
}: {
  creativeId: number;
  rationale?: string;
}) {
  const [queued, setQueued] = useState(false);
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .listAppliedVariants()
      .then((entries) => {
        if (cancelled) return;
        setQueued(entries.some((e) => e.creative_id === creativeId));
      })
      .catch(() => {
        // Network blip — leave queued=false; user can click Apply again.
      });
    return () => {
      cancelled = true;
    };
  }, [creativeId]);

  function apply() {
    setError(null);
    startTransition(async () => {
      try {
        await api.applyVariant(creativeId, rationale);
        setQueued(true);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to queue variant");
      }
    });
  }

  function undo() {
    setError(null);
    startTransition(async () => {
      try {
        await api.undoVariant(creativeId);
        setQueued(false);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to undo");
      }
    });
  }

  if (queued) {
    return (
      <div className="apply-banner success" role="status">
        <span className="apply-banner-icon" aria-hidden>
          ✓
        </span>
        <div className="col gap-1" style={{ flex: 1 }}>
          <strong>Queued to replace the live ad in 24h.</strong>
          <span className="t-micro muted">
            Your team can review the change before it goes live.
          </span>
        </div>
        <button
          type="button"
          className="apply-banner-undo"
          onClick={undo}
          disabled={pending}
        >
          {pending ? "Undoing…" : "Undo"}
        </button>
      </div>
    );
  }

  return (
    <div className="apply-bar">
      <div className="col gap-1" style={{ flex: 1 }}>
        <strong>Ready to push this variant?</strong>
        <span className="t-micro muted">
          Replaces the live ad after a 24h review window — undoable any time.
        </span>
      </div>
      <button
        type="button"
        className="btn primary apply-bar-cta"
        onClick={apply}
        disabled={pending}
      >
        {pending ? "Queueing…" : "Apply this variant →"}
      </button>
      {error ? (
        <span className="apply-bar-error" role="alert">
          {error}
        </span>
      ) : null}
    </div>
  );
}
