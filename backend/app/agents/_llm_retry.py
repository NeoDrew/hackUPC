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
import re
from typing import Any, Callable

import httpx

from ._key_pool import get_pool

log = logging.getLogger(__name__)

_KEY_QS_RE = re.compile(r"([?&])key=[^&\s'\"]+")


def scrub_keys(s: str) -> str:
    """Redact ``?key=...`` / ``&key=...`` query params from any string.
    Use on httpx error messages before returning them to clients — httpx
    exceptions stringify with the full request URL, which embeds the
    Google AI Studio API key."""
    return _KEY_QS_RE.sub(r"\1key=REDACTED", s)

# Backoff schedule in seconds. Total worst-case wait ~7s (1+2+4) before the
# final attempt; chat turn budget is 30s per request × 6 loop turns so this
# fits comfortably.
_DEFAULT_DELAYS = (1.0, 2.0, 4.0)
_MAX_RETRY_AFTER_S = 8.0


def _default_key_extractor(url: str) -> str | None:
    """Pull the ``key=`` query parameter out of a Google AI Studio URL.
    Returns ``None`` if the URL doesn't carry one (e.g. test stub)."""
    if "key=" not in url:
        return None
    tail = url.split("key=", 1)[1]
    # Stop at next query-param separator.
    for sep in ("&", "#"):
        if sep in tail:
            tail = tail.split(sep, 1)[0]
            break
    return tail or None


async def post_with_retry(
    client: httpx.AsyncClient,
    url_or_factory: str | Callable[[], str],
    *,
    json: dict[str, Any] | None = None,
    delays: tuple[float, ...] = _DEFAULT_DELAYS,
    label: str = "LLM",
    key_for_url: Callable[[str], str | None] | None = _default_key_extractor,
) -> httpx.Response:
    """POST with exponential backoff and (optional) rotating-key swap.

    ``url_or_factory`` is either a single URL string (legacy), or a
    zero-arg callable returning a fresh URL each retry. Use the callable
    form to opt into key rotation: each retry asks the factory for a URL
    with the next-best key from the global pool. On 429 the prior key is
    banned in the pool for ~60s, then the factory delivers a different
    key.

    ``key_for_url`` extracts the key from a URL so the wrapper can ban
    it on 429 (for the legacy single-URL path). Defaults to parsing
    ``?key=...`` query params.

    ``label`` is prefixed to retry log lines so a tail of the backend log
    distinguishes Gemini chat retries from Gemma polish retries.
    """
    is_factory = callable(url_or_factory)

    def _next_url() -> str:
        if is_factory:
            return url_or_factory()  # type: ignore[operator]
        return url_or_factory  # type: ignore[return-value]

    pool = get_pool()
    last_exc: Exception | None = None

    for attempt, delay in enumerate([0.0, *delays]):
        if delay > 0:
            jitter = random.random() * 0.5
            await asyncio.sleep(delay + jitter)

        url = _next_url()

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

        retryable = resp.status_code == 429 or 500 <= resp.status_code < 600
        if not retryable:
            return resp

        # On 429, ban the offending key in the pool so the next factory
        # call returns a different one. Even with a single key this is
        # harmless — the pool falls back to the one banned-longest.
        if resp.status_code == 429 and key_for_url is not None:
            try:
                used_key = key_for_url(url)
            except Exception:  # noqa: BLE001
                used_key = None
            if used_key:
                pool.ban(used_key)

        if attempt >= len(delays):
            log.warning(
                "%s POST giving up after %d attempts (status=%d) pool=%s",
                label,
                attempt + 1,
                resp.status_code,
                pool.status(),
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
            "%s POST attempt %d/%d → %d, will retry%s",
            label,
            attempt + 1,
            len(delays) + 1,
            resp.status_code,
            " (rotating key)" if is_factory and pool.size > 1 else "",
        )

    if last_exc is not None:
        raise last_exc
    raise RuntimeError(f"{label} POST failed without a captured response")
