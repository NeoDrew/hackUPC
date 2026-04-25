"""Mutable state for slice recommendations — applied / snoozed / dismissed.

Lives behind a thin interface so an Atlas-backed implementation can swap in
by replacing this file. Process-lifetime in v1; per ``data_findings.md`` the
applied-actions log will eventually persist to MongoDB Atlas (one document
per applied recommendation, advertiser-keyed) for the MLH prize hook and
the demo's "you applied 8 of 12 recommendations this week" claim.

The recommendations themselves are computed at startup and held on the
Datastore; this cache only carries the user-touched state by
``recommendation_id``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

log = logging.getLogger(__name__)


@dataclass
class RecommendationState:
    applied_at: str | None = None
    snoozed_until: str | None = None
    dismissed_at: str | None = None


@dataclass
class RecommendationCache:
    """In-memory store for recommendation state. Public API matches what
    an Atlas implementation would expose so the swap is one file."""

    _state: dict[str, RecommendationState] = field(default_factory=dict)

    def get_state(self, recommendation_id: str) -> RecommendationState:
        return self._state.get(recommendation_id) or RecommendationState()

    def is_active(
        self, recommendation_id: str, now_iso: str | None = None
    ) -> bool:
        """A recommendation is active (should appear in the queue) if it
        has not been applied or dismissed, and is not currently snoozed.
        Applied / dismissed are terminal — the user has handled the
        recommendation, no need to re-surface it. Snooze is temporary."""
        s = self._state.get(recommendation_id)
        if s is None:
            return True
        if s.dismissed_at is not None:
            return False
        if s.applied_at is not None:
            return False
        if s.snoozed_until is not None:
            now = now_iso or _utc_now_iso()
            if now < s.snoozed_until:
                return False
        return True

    def mark_applied(self, recommendation_id: str) -> RecommendationState:
        s = self._state.setdefault(recommendation_id, RecommendationState())
        s.applied_at = _utc_now_iso()
        return s

    def mark_snoozed(
        self, recommendation_id: str, until_iso: str
    ) -> RecommendationState:
        s = self._state.setdefault(recommendation_id, RecommendationState())
        s.snoozed_until = until_iso
        return s

    def mark_dismissed(self, recommendation_id: str) -> RecommendationState:
        s = self._state.setdefault(recommendation_id, RecommendationState())
        s.dismissed_at = _utc_now_iso()
        return s

    def reset(self, recommendation_id: str) -> None:
        self._state.pop(recommendation_id, None)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
