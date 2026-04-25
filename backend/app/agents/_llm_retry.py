"""Shared retry wrapper for Google AI Studio (Gemini / Gemma) calls.

The free / hobby tier rate-limits aggressively per minute and per day. A
single 429 has been crashing the chat orchestrator and silently suppressing
the recommendation_copy polish batch. This module gives every LLM call the
same retry policy: exponential backoff with jitter, a hard cap of 3
attempts, and respect for any ``Retry-After`` header the server sends.

We retry on:
- HTTP 429 (rate limit)
- HTTP 5xx (server errors)
- ``httpx.TransportError`` / ``httpx.TimeoutException`` (network blips)

We do NOT retry on:
- 4xx other than 429 (auth, malformed body — those won't get better)

Use:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await post_with_retry(client, url, json=body)
"""

from __future__ import annotations

import asyncio
import logging
import random
from typing import Any

import httpx

log = logging.getLogger(__name__)

# Backoff schedule in seconds. Total worst-case wait ~7s (1+2+4) before the
# final attempt; chat turn budget is 30s per request × 6 loop turns so this
# fits comfortably.
_DEFAULT_DELAYS = (1.0, 2.0, 4.0)
_MAX_RETRY_AFTER_S = 8.0


async def post_with_retry(
    client: httpx.AsyncClient,
    url: str,
    *,
    json: dict[str, Any] | None = None,
    delays: tuple[float, ...] = _DEFAULT_DELAYS,
    label: str = "LLM",
) -> httpx.Response:
    """POST with exponential backoff. Returns the final ``Response``
    (raised on the last attempt's failure) or raises the underlying
    exception.

    ``label`` is prefixed to retry log lines so a tail of the backend log
    distinguishes Gemini chat retries from Gemma polish retries.
    """
    last_exc: Exception | None = None
    for attempt, delay in enumerate([0.0, *delays]):
        if delay > 0:
            # Jitter in [0, 0.5s) so concurrent callers don't synchronise.
            jitter = random.random() * 0.5
            await asyncio.sleep(delay + jitter)

        try:
            resp = await client.post(url, json=json)
        except (httpx.TransportError, httpx.TimeoutException) as e:
            last_exc = e
            log.warning(
                "%s POST attempt %d/%d transport error: %s",
                label,
                attempt + 1,
                len(delays) + 1,
                e,
            )
            continue

        if resp.status_code < 400:
            return resp

        # Decide whether the failure is retryable.
        retryable = resp.status_code == 429 or 500 <= resp.status_code < 600
        if not retryable:
            # Surface the body for non-retryable 4xx so the caller can log.
            return resp

        if attempt >= len(delays):
            # Out of retries; return the final failed response so the
            # caller's existing raise_for_status() / parse path runs.
            log.warning(
                "%s POST giving up after %d attempts (status=%d)",
                label,
                attempt + 1,
                resp.status_code,
            )
            return resp

        # Honor Retry-After if the server provided one (number of seconds).
        retry_after = resp.headers.get("Retry-After")
        if retry_after is not None:
            try:
                ra = float(retry_after)
                if 0 < ra <= _MAX_RETRY_AFTER_S:
                    log.info(
                        "%s honoring Retry-After=%.1fs (status=%d)",
                        label,
                        ra,
                        resp.status_code,
                    )
                    await asyncio.sleep(ra)
            except ValueError:
                pass

        log.info(
            "%s POST attempt %d/%d → %d, will retry",
            label,
            attempt + 1,
            len(delays) + 1,
            resp.status_code,
        )

    # Shouldn't reach here, but if we do (transport failures all the way
    # through), surface the last exception.
    if last_exc is not None:
        raise last_exc
    raise RuntimeError(f"{label} POST failed without a captured response")
