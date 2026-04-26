"""Rotating Google AI Studio API key pool.

The free-tier limits on Gemini / Gemma are per-key (e.g. Gemini 2.5 Flash:
10 RPM, 250 RPD). With one key the chat orchestrator throttles within a
handful of turns. With N keys we round-robin and treat 429s on a single
key as "ban this one for ~60 seconds, try the next one" — multiplying
effective quota by N at the cost of provisioning a few extra keys.

Configuration (in priority order, first non-empty wins):

1. ``GEMINI_API_KEYS=key1,key2,key3`` — comma-separated, recommended.
2. ``GEMINI_API_KEY_1`` / ``GEMINI_API_KEY_2`` / ... — explicit numbered slots.
3. ``GEMINI_API_KEY`` or ``GOOGLE_API_KEY`` — single key fallback (existing
   behavior, no rotation).

Generate additional keys at https://aistudio.google.com/app/apikey — each
key takes ~30 seconds to provision and the free tier is generous enough
that a hackathon team can comfortably run 3–5.

This module is process-global. The pool is initialised lazily on first
``GLOBAL_POOL.next_key()`` so importing it doesn't read the environment
before ``load_dotenv()`` runs in the agent modules.
"""

from __future__ import annotations

import logging
import os
import threading
import time

from dotenv import load_dotenv

log = logging.getLogger(__name__)

# Default: a 429-banned key is excluded from rotation for this many
# seconds before being retried. Matches the typical per-minute window on
# Google AI Studio's free tier.
DEFAULT_BAN_SECONDS = 60.0


class KeyPool:
    """Thread-safe round-robin pool. Banned keys are skipped until their
    ban expires; if every key is banned, the pool returns the
    longest-banned one anyway (better to retry a stale key than fail the
    whole call)."""

    def __init__(self, keys: list[str]) -> None:
        self._keys = list(dict.fromkeys(k.strip() for k in keys if k and k.strip()))
        self._idx = -1
        self._banned: dict[str, float] = {}
        self._lock = threading.Lock()

    @classmethod
    def from_env(cls) -> "KeyPool":
        load_dotenv()  # idempotent; safe to call repeatedly
        # 1. Comma-separated single env var.
        multi = os.environ.get("GEMINI_API_KEYS", "")
        if multi.strip():
            keys = [k for k in multi.split(",") if k.strip()]
            log.info(
                "key pool loaded from GEMINI_API_KEYS: %d keys", len(keys)
            )
            return cls(keys)
        # 2. Numbered env vars GEMINI_API_KEY_1, _2, ...
        numbered: list[str] = []
        for i in range(1, 9):  # support up to 8 numbered keys
            v = os.environ.get(f"GEMINI_API_KEY_{i}", "").strip()
            if v:
                numbered.append(v)
        if numbered:
            log.info(
                "key pool loaded from GEMINI_API_KEY_N: %d keys", len(numbered)
            )
            return cls(numbered)
        # 3. Legacy single-key fallback.
        single = (
            os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
            or ""
        ).strip()
        if single:
            log.info("key pool loaded from GEMINI_API_KEY (single key, no rotation)")
            return cls([single])
        log.warning("key pool empty: no GEMINI_API_KEY* env var set")
        return cls([])

    @property
    def size(self) -> int:
        return len(self._keys)

    def __bool__(self) -> bool:
        return bool(self._keys)

    def next_key(self) -> str | None:
        """Return the next non-banned key (round-robin). Returns ``None``
        if the pool is empty. If every key is currently banned, returns
        whichever was banned longest ago."""
        with self._lock:
            if not self._keys:
                return None
            now = time.time()
            n = len(self._keys)
            # Try at most n hops to find a non-banned key.
            for _ in range(n):
                self._idx = (self._idx + 1) % n
                key = self._keys[self._idx]
                ban_until = self._banned.get(key, 0.0)
                if ban_until <= now:
                    return key
            # All banned. Return the one whose ban has been in place
            # longest (so its quota window is most likely to have reset).
            oldest = min(self._keys, key=lambda k: self._banned.get(k, 0.0))
            return oldest

    def ban(self, key: str, seconds: float = DEFAULT_BAN_SECONDS) -> None:
        """Mark ``key`` as throttled for the next ``seconds``. The key
        won't be picked by ``next_key()`` until the ban expires (unless
        every key is banned, in which case the round-robin still works)."""
        with self._lock:
            self._banned[key] = time.time() + seconds
        log.info(
            "key ...%s banned for %.0fs (429 / rate limit)",
            key[-6:] if len(key) >= 6 else key,
            seconds,
        )

    def status(self) -> dict[str, float]:
        """Snapshot of bans for diagnostics. Maps key suffix → seconds-until-unban."""
        now = time.time()
        with self._lock:
            return {
                f"...{k[-6:] if len(k) >= 6 else k}": max(0.0, self._banned.get(k, 0.0) - now)
                for k in self._keys
            }


# Lazy-init singleton: read env on first access so callers like
# ``load_dotenv()`` in the agent modules have already run.
_pool: KeyPool | None = None
_pool_lock = threading.Lock()


def get_pool() -> KeyPool:
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = KeyPool.from_env()
    return _pool
