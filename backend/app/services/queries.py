"""Pure-function lookups over the in-memory Datastore.

These functions return JSON-serialisable dicts that pydantic schemas in
`app.schemas` validate. No FastAPI imports here — keeps the analysis layer
testable in isolation.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from ..agents import variant_brief as variant_brief_agent
from ..agents import vision_insight as vision_insight_agent
from ..datastore import Datastore, _band_from_health
from ..schemas import to_jsonable
from . import windowed


def list_advertisers(store: Datastore) -> list[dict[str, Any]]:
    return store.advertisers.to_dict("records")


def get_advertiser(store: Datastore, advertiser_id: int) -> dict[str, Any] | None:
    rows = store.advertisers[store.advertisers["advertiser_id"] == advertiser_id]
    if rows.empty:
        return None
    return rows.iloc[0].to_dict()


def list_campaigns_for_advertiser(
    store: Datastore, advertiser_id: int
) -> list[dict[str, Any]]:
    rows = store.campaigns[store.campaigns["advertiser_id"] == advertiser_id]
    return [_campaign_record(row) for _, row in rows.iterrows()]


def get_campaign(store: Datastore, campaign_id: int) -> dict[str, Any] | None:
    rows = store.campaigns[store.campaigns["campaign_id"] == campaign_id]
    if rows.empty:
        return None
    return _campaign_record(rows.iloc[0])


def list_creatives_for_campaign(
    store: Datastore, campaign_id: int
) -> list[dict[str, Any]]:
    rows = store.creatives[store.creatives["campaign_id"] == campaign_id]
    summary = store.creative_summary.set_index("creative_id")[
        "creative_status"
    ].to_dict()
    out: list[dict[str, Any]] = []
    for _, row in rows.iterrows():
        creative_id = int(row["creative_id"])
        out.append(
            {
                "creative_id": creative_id,
                "campaign_id": int(row["campaign_id"]),
                "advertiser_name": row["advertiser_name"],
                "vertical": row["vertical"],
                "format": row["format"],
                "theme": row["theme"],
                "creative_status": summary.get(creative_id),
                "asset_file": row["asset_file"],
            }
        )
    return out


def get_creative_detail(
    store: Datastore,
    creative_id: int,
    *,
    start: str | None = None,
    end: str | None = None,
) -> dict[str, Any] | None:
    record = store.creative_detail.get(creative_id)
    if record is None:
        return None
    record = dict(record)  # shallow copy so we don't mutate the cached dict
    if not windowed.is_full_range(store, start, end):
        s, e = windowed.normalize_window(store, start, end)
        win_row = windowed.compute_window(store, s, e)["rows_by_cid"].get(
            creative_id
        )
        if win_row is not None:
            # Override the perf-bearing fields with the windowed values; keep
            # all metadata (theme, hook_type, asset_file, fatigue_day...)
            # untouched since those are creative-intrinsic.
            for k in (
                "ctr",
                "cvr",
                "roas",
                "spend_usd",
                "impressions",
                "clicks",
                "conversions",
                "revenue_usd",
                "days_active",
                "health",
                "status_band",
            ):
                if k in win_row:
                    record[k] = win_row[k]
            # Map windowed flat-row keys back onto the detail-shaped names
            # the frontend reads.
            record["overall_ctr"] = win_row["ctr"]
            record["overall_cvr"] = win_row["cvr"]
            record["overall_roas"] = win_row["roas"]
            record["total_spend_usd"] = win_row["spend_usd"]
            record["total_impressions"] = win_row["impressions"]
            record["total_clicks"] = win_row["clicks"]
            record["total_conversions"] = win_row["conversions"]
            record["total_revenue_usd"] = win_row["revenue_usd"]
            record["total_days_active"] = win_row["days_active"]
    return to_jsonable(record)


def get_creative_timeseries(
    store: Datastore, creative_id: int
) -> dict[str, Any] | None:
    points = store.timeseries_by_creative.get(creative_id)
    if points is None:
        return None
    return {"creative_id": creative_id, "points": points}


# --- Cockpit / portfolio queries ---


_STATUS_BANDS = {"scale", "watch", "rescue", "cut"}

_ROW_SORTABLE = {
    "ctr",
    "cvr",
    "roas",
    "spend_usd",
    "revenue_usd",
    "impressions",
    "clicks",
    "conversions",
    "health",
    "days_active",
}


def portfolio_kpis(
    store: Datastore, *, start: str | None = None, end: str | None = None
) -> dict[str, Any]:
    if windowed.is_full_range(store, start, end):
        return store.portfolio_kpis
    s, e = windowed.normalize_window(store, start, end)
    return windowed.compute_window(store, s, e)["kpis"]


def tab_counts(
    store: Datastore, *, start: str | None = None, end: str | None = None
) -> dict[str, int]:
    if windowed.is_full_range(store, start, end):
        return store.tab_counts
    s, e = windowed.normalize_window(store, start, end)
    return windowed.compute_window(store, s, e)["tab_counts"]


def health_diagnostics(store: Datastore) -> dict[str, Any]:
    """Return the precomputed Q1 health diagnostics payload (stability,
    distribution, synthetic-label sanity checks). Computed at startup
    inside ``Datastore._compute_health_scores``."""
    return store.health_diagnostics


# --- Apply-variant queue (process-lifetime, cleared on restart) ---


def queue_variant(
    store: Datastore, creative_id: int, rationale: str | None
) -> dict[str, Any]:
    from datetime import datetime, timezone

    entry = {
        "creative_id": int(creative_id),
        "rationale": rationale,
        "queued_at": datetime.now(timezone.utc).isoformat(),
        "eta_hours": 24,
    }
    store.applied_variants[int(creative_id)] = entry
    return {"creative_id": int(creative_id), "queued": True, "entry": entry}


def dequeue_variant(store: Datastore, creative_id: int) -> dict[str, Any]:
    cid = int(creative_id)
    removed = store.applied_variants.pop(cid, None)
    return {"creative_id": cid, "queued": False, "entry": removed}


def list_applied_variants(store: Datastore) -> list[dict[str, Any]]:
    return list(store.applied_variants.values())


# --- Cohort attribute prevalence (winning patterns in this cohort) ---


_PATTERN_ATTRS: list[tuple[str, str, str]] = [
    # (column, "true value" check key, descriptive trait name)
    ("has_discount_badge", "true", "Visible price / discount proof"),
    ("has_ugc_style", "true", "User-generated style framing"),
    ("has_gameplay", "true", "Gameplay or product-in-action shot"),
    ("has_price", "true", "Price prominently shown"),
]

_PATTERN_CATEGORICAL: list[tuple[str, str]] = [
    # (column, "what it means" — short label)
    ("hook_type", "hook"),
    ("dominant_color", "dominant colour"),
    ("emotional_tone", "tone"),
    ("cta_text", "CTA"),
]


def winning_patterns(
    store: Datastore, creative_id: int, max_patterns: int = 3
) -> dict[str, Any]:
    """Compute the top attributes that distinguish *top performers* from the
    rest within the same (vertical, format) cohort as ``creative_id``.

    Lift = P(attribute | top performer) / P(attribute | other) − 1, expressed
    as a percentage. We surface the highest-lift binary flag plus the most
    common categorical pick (e.g. "playable runs at 30s", "primary colour
    blue") among top performers. No LLM here — it's a deterministic count
    over the attribute table.
    """
    detail = store.creative_detail.get(int(creative_id))
    if detail is None:
        return {"creative_id": creative_id, "segment": {}, "patterns": []}

    vertical = detail.get("vertical")
    fmt = detail.get("format")
    if vertical is None or fmt is None:
        return {"creative_id": creative_id, "segment": {}, "patterns": []}

    creatives = store.creatives
    summary = store.creative_summary.set_index("creative_id")["creative_status"].to_dict()

    cohort = creatives[
        (creatives["vertical"] == vertical) & (creatives["format"] == fmt)
    ].copy()
    if cohort.empty:
        return {
            "creative_id": creative_id,
            "segment": {"vertical": vertical, "format": fmt},
            "patterns": [],
        }

    cohort["status"] = cohort["creative_id"].map(summary)
    winners = cohort[cohort["status"] == "top_performer"]
    others = cohort[cohort["status"] != "top_performer"]
    if winners.empty:
        return {
            "creative_id": creative_id,
            "segment": {"vertical": vertical, "format": fmt},
            "patterns": [],
        }

    n_winners = len(winners)
    n_others = max(len(others), 1)
    candidates: list[dict[str, Any]] = []

    # Binary flags — easy lift signal.
    for col, _, trait in _PATTERN_ATTRS:
        if col not in winners.columns:
            continue
        win_rate = float((winners[col] == True).mean())  # noqa: E712
        oth_rate = float((others[col] == True).mean()) if not others.empty else 0.0  # noqa: E712
        if win_rate < 0.30:
            # Filter out attributes that only show up sporadically in winners.
            continue
        lift = (win_rate / oth_rate - 1.0) if oth_rate > 0 else win_rate
        candidates.append({
            "trait": trait,
            "what": _describe_binary(col, win_rate, vertical, fmt),
            "prevalence_winners": win_rate,
            "prevalence_others": oth_rate,
            "lift": lift,
            "count_winners": int((winners[col] == True).sum()),  # noqa: E712
        })

    # Categorical attributes — pick the modal value among winners and report
    # how dominant it is.
    for col, label in _PATTERN_CATEGORICAL:
        if col not in winners.columns:
            continue
        modes = winners[col].value_counts(dropna=True)
        if modes.empty:
            continue
        top_value = modes.index[0]
        top_count = int(modes.iloc[0])
        win_rate = top_count / n_winners
        if win_rate < 0.35:
            continue
        oth_count = int((others[col] == top_value).sum()) if not others.empty else 0
        oth_rate = oth_count / n_others
        lift = (win_rate / oth_rate - 1.0) if oth_rate > 0 else win_rate
        candidates.append({
            "trait": f"{label.capitalize()}: {top_value}",
            "what": (
                f"{int(round(win_rate * 100))}% of top performers in this "
                f"cohort use this {label}; {int(round(oth_rate * 100))}% of "
                f"the rest do."
            ),
            "prevalence_winners": win_rate,
            "prevalence_others": oth_rate,
            "lift": lift,
            "count_winners": top_count,
        })

    # Rank by lift (descending), tie-break on prevalence among winners.
    candidates.sort(
        key=lambda p: (round(p["lift"], 4), p["prevalence_winners"]),
        reverse=True,
    )
    top_patterns = candidates[:max_patterns]

    return {
        "creative_id": int(creative_id),
        "segment": {"vertical": str(vertical), "format": str(fmt)},
        "cohort_size": int(len(cohort)),
        "winner_count": int(n_winners),
        "patterns": [
            {
                "trait": p["trait"],
                "what": p["what"],
                "lift_pct": round(p["lift"] * 100, 1),
                "prevalence_pct": round(p["prevalence_winners"] * 100, 0),
                "winner_count": p["count_winners"],
            }
            for p in top_patterns
        ],
    }


def _describe_binary(col: str, win_rate: float, vertical: Any, fmt: Any) -> str:
    pct = int(round(win_rate * 100))
    if col == "has_discount_badge":
        return (
            f"Concrete value proof — {pct}% of top {fmt} ads in {vertical} "
            "carry a visible discount badge. Where the headline lacks proof, "
            "winners overwhelmingly substitute price."
        )
    if col == "has_ugc_style":
        return (
            f"{pct}% of winners use UGC-style framing. Reads as authentic "
            "rather than produced; lifts attention on rewarded video and "
            "interstitial slots."
        )
    if col == "has_gameplay":
        return (
            f"{pct}% of winners show gameplay or the product in action. "
            "Stops the scroll because viewers can simulate the experience "
            "before the CTA."
        )
    if col == "has_price":
        return (
            f"{pct}% of winners surface the price up front. Eliminates the "
            "biggest dropout step in the funnel."
        )
    return (
        f"{pct}% of top performers in this cohort share this attribute — "
        "above the cohort baseline."
    )


# --- Variant brief (Gemma-generated, fallback to template) ---


async def get_variant_brief(
    store: Datastore, creative_id: int
) -> dict[str, Any] | None:
    """Compose the brief for the next ad creative.

    Reuses the same twin lookup the Twin page uses, then asks Gemma to write
    a fresh headline / subhead / CTA / rationale grounded in the source-vs-
    winner attribute diffs. Falls back to a deterministic template (the
    winner's metadata + canned rationale) when Gemma is unavailable so the
    page never breaks.
    """
    twin = await get_twin_stub(store, creative_id)
    if twin is None:
        return None

    source = store.creative_detail.get(int(twin["fatigued_id"]))
    winner = store.creative_detail.get(int(twin["winner_id"]))
    if source is None or winner is None:
        return None

    segment = twin["segment"]
    diffs = twin.get("diffs", [])

    llm_brief = await variant_brief_agent.generate_brief(
        source=source,
        winner=winner,
        diffs=diffs,
        segment=segment,
    )

    if llm_brief is not None:
        return {
            "creative_id": int(twin["fatigued_id"]),
            "winner_id": int(twin["winner_id"]),
            "segment": segment,
            "headline": llm_brief["headline"],
            "subhead": llm_brief["subhead"],
            "cta": llm_brief["cta"],
            "dominant_color": llm_brief["dominant_color"],
            "emotional_tone": llm_brief["emotional_tone"],
            "rationale": llm_brief["rationale"],
            "is_stub": False,
        }

    # Template fallback. Pulls from the winner's metadata + a few generic
    # but truthful sentences keyed on the cohort. The marketer still sees
    # the page; only the wording is canned.
    fallback_rationale = [
        f"Mirror the winner's hook type ({winner.get('hook_type') or 'direct'}). "
        "Adjacent combos in this cohort tend to convert above the average.",
        f"Keep visual clutter low (target {winner.get('clutter_score') or 0.3}). "
        "Fatigued ads in this cohort drift higher.",
        f"Run at {winner.get('duration_sec') or 15}s — the winning duration "
        f"ceiling in {segment.get('format', '')} ads.",
    ]
    if winner.get("has_discount_badge"):
        fallback_rationale.append(
            "Restate the discount proof — it's the single biggest CVR driver "
            "in this vertical."
        )

    return {
        "creative_id": int(twin["fatigued_id"]),
        "winner_id": int(twin["winner_id"]),
        "segment": segment,
        "headline": str(winner.get("headline") or source.get("headline") or "New variant"),
        "subhead": str(winner.get("subhead") or source.get("subhead") or ""),
        "cta": str(winner.get("cta_text") or "Try now"),
        "dominant_color": str(winner.get("dominant_color") or "purple"),
        "emotional_tone": str(winner.get("emotional_tone") or "urgent"),
        "rationale": fallback_rationale,
        "is_stub": True,
    }


def search_creatives(
    store: Datastore, query: str, limit: int = 8
) -> list[dict[str, Any]]:
    """Return weighted-relevance matches for ``query`` across creative fields.

    Priority order (descending weight):
      - Exact creative_id match (numeric query)
      - Headline substring
      - Advertiser name substring
      - Theme / hook_type / cta_text substring
      - Vertical / format substring
    """
    q = query.strip().lower()
    if not q:
        return []
    rows = list(store.flat_row_by_creative.values())

    # Pull richer fields from creative_detail for theme/hook/cta matches.
    detail_lookup = store.creative_detail

    matches: list[tuple[float, dict[str, Any]]] = []
    for row in rows:
        cid = row["creative_id"]
        d = detail_lookup.get(cid, {})
        score = 0.0

        # Exact creative-id match (when the user types a number).
        if q.isdigit() and int(q) == cid:
            score += 10.0

        headline = (row.get("headline") or "").lower()
        if q in headline:
            # Boost when the headline starts with the query.
            score += 6.0 if headline.startswith(q) else 5.0

        advertiser = (row.get("advertiser_name") or "").lower()
        if q in advertiser:
            score += 3.0

        for field in ("theme", "hook_type", "cta_text"):
            v = str(d.get(field) or "").lower()
            if v and q in v:
                score += 1.5

        for field in ("vertical", "format"):
            v = (row.get(field) or "").lower()
            if v and q in v:
                score += 1.0

        if score <= 0:
            continue
        matches.append((score, row))

    matches.sort(key=lambda t: (t[0], t[1].get("health") or 0), reverse=True)
    out: list[dict[str, Any]] = []
    for score, row in matches[:limit]:
        d = detail_lookup.get(row["creative_id"], {})
        out.append(
            {
                "creative_id": row["creative_id"],
                "headline": row.get("headline"),
                "advertiser_name": row.get("advertiser_name"),
                "vertical": row.get("vertical"),
                "format": row.get("format"),
                "status_band": row.get("status_band"),
                "status": row.get("status"),
                "health": row.get("health"),
                "asset_file": row.get("asset_file"),
                "theme": d.get("theme"),
                "hook_type": d.get("hook_type"),
                "score": round(float(score), 2),
            }
        )
    return out


def list_creatives_flat(
    store: Datastore,
    *,
    tab: str | None = None,
    status: str | None = None,
    vertical: str | None = None,
    format: str | None = None,
    sort: str | None = None,
    desc: bool = True,
    limit: int | None = None,
    start: str | None = None,
    end: str | None = None,
) -> dict[str, Any]:
    """Flat creative list, wrapped with pre-pagination ``total``.

    Lifetime mode (no window): tab filters via ``creative_status`` →
    ``_STATUS_TAB_MAP``. Windowed mode: tab filters by our computed
    ``status_band`` directly, since the dataset's lifetime label can't
    speak to a sub-window it didn't see.
    """
    if windowed.is_full_range(store, start, end):
        rows = list(store.flat_row_by_creative.values())
        windowed_mode = False
    else:
        s, e = windowed.normalize_window(store, start, end)
        rows = list(windowed.compute_window(store, s, e)["rows_by_cid"].values())
        windowed_mode = True

    if tab and tab != "explore":
        if tab not in _STATUS_BANDS:
            return {"rows": [], "total": 0, "limit": limit}
        # Both lifetime and windowed paths now filter on the computed
        # status_band — the lifetime band is set by the Q1 health score,
        # so it's the same axis in both modes.
        rows = [r for r in rows if r.get("status_band") == tab]
    elif status:
        rows = [r for r in rows if r["status"] == status]

    if vertical:
        rows = [r for r in rows if r["vertical"] == vertical]
    if format:
        rows = [r for r in rows if r["format"] == format]

    if sort and sort in _ROW_SORTABLE:
        rows.sort(key=lambda r: r.get(sort) or 0, reverse=desc)
    else:
        rows.sort(key=lambda r: r.get("health") or 0, reverse=True)

    total = len(rows)
    if limit is not None:
        rows = rows[:limit]
    return {"rows": rows, "total": total, "limit": limit}


# --- Twin stub ---


_VISION_TEMPLATES: dict[str, dict[str, str]] = {
    "text_density": {
        "headline": "Twin runs leaner copy",
        "body": (
            "Your fatigued creative carries roughly twice the on-screen text. "
            "The cohort leader keeps text density low and lets the product hero "
            "carry the message; the audience reads it in under a second."
        ),
    },
    "clutter_score": {
        "headline": "Twin reduces visual clutter",
        "body": (
            "The winner sits on a cleaner background with one clear focal point. "
            "Lower clutter correlates with higher CTR in this cohort: the eye "
            "lands on the offer instead of having to scan."
        ),
    },
    "has_discount_badge": {
        "headline": "Twin leans on a price proof",
        "body": (
            "The winner shows a discount badge prominently; your fatigued "
            "creative does not. In this cohort the winning attribute combo "
            "average 1.6× the conversion rate of equivalents without it."
        ),
    },
    "novelty_score": {
        "headline": "Twin feels less repetitive",
        "body": (
            "The winner's novelty score sits well above average for its cohort. "
            "Your fatigued creative is one of several near-duplicates in the "
            "portfolio — audience saturation is suppressing CTR."
        ),
    },
    "default": {
        "headline": "Twin is winning on attribute fit",
        "body": (
            "The winning creative in this cohort outperforms on the dominant "
            "attributes for its vertical and format. The diffs below show "
            "where to focus the next test."
        ),
    },
}


_TWIN_FIELDS: list[str] = [
    "theme",
    "hook_type",
    "cta_text",
    "dominant_color",
    "emotional_tone",
    "duration_sec",
    "text_density",
    "clutter_score",
    "novelty_score",
    "has_discount_badge",
    "has_ugc_style",
    "faces_count",
]


async def get_twin_stub(
    store: Datastore,
    creative_id: int,
    *,
    start: str | None = None,
    end: str | None = None,
) -> dict[str, Any] | None:
    """Pick the *most attribute-similar* top performer within the same
    (vertical, format) cohort using cosine similarity over a per-creative
    feature vector (one-hot categoricals + normalised numerics + binary
    flags). Returns the real similarity score in ``similarity``.

    Lifetime mode: winner pool = creatives with ``creative_status ==
    'top_performer'``. Windowed mode: winner pool = creatives whose
    *windowed* ``status_band == 'scale'`` (the lifetime label can't speak
    to a sub-window it didn't see). Cosine vectors themselves are built
    from creative metadata, so they don't recompute.
    """
    import numpy as np

    source = store.creative_detail.get(creative_id)
    if source is None:
        return None

    if windowed.is_full_range(store, start, end):
        summary = store.creative_summary
        cohort = summary[
            (summary["vertical"] == source["vertical"])
            & (summary["format"] == source["format"])
            & (summary["creative_status"] == "top_performer")
            & (summary["creative_id"] != creative_id)
        ]
        if cohort.empty:
            cohort = summary[
                (summary["vertical"] == source["vertical"])
                & (summary["creative_status"] == "top_performer")
                & (summary["creative_id"] != creative_id)
            ]
        cohort_ids = [int(c) for c in cohort["creative_id"].tolist()]
    else:
        s, e = windowed.normalize_window(store, start, end)
        rows_by_cid = windowed.compute_window(store, s, e)["rows_by_cid"]
        # Tight filter first: same (vertical, format) + scale band. Then
        # progressively widen — in narrower windows entire cohorts can be
        # empty of scale-band creatives, so we accept watch and finally any
        # vertical, rather than 404.
        def find_pool(*, by_cohort: bool, by_vertical: bool, bands: tuple[str, ...]) -> list[int]:
            return [
                cid
                for cid, r in rows_by_cid.items()
                if cid != creative_id
                and r["status_band"] in bands
                and (not by_vertical or r["vertical"] == source["vertical"])
                and (not by_cohort or r["format"] == source["format"])
            ]

        cohort_ids = find_pool(by_cohort=True, by_vertical=True, bands=("scale",))
        if not cohort_ids:
            cohort_ids = find_pool(by_cohort=False, by_vertical=True, bands=("scale",))
        if not cohort_ids:
            cohort_ids = find_pool(by_cohort=True, by_vertical=True, bands=("scale", "watch"))
        if not cohort_ids:
            cohort_ids = find_pool(by_cohort=False, by_vertical=True, bands=("scale", "watch"))
        if not cohort_ids:
            cohort_ids = find_pool(by_cohort=False, by_vertical=False, bands=("scale", "watch"))
    if not cohort_ids:
        return None

    source_vec = store.creative_vectors.get(creative_id)
    if source_vec is None:
        # Vector unavailable for some reason — fall back to the first cohort member.
        winner_id = cohort_ids[0]
        similarity = 0.0
    else:
        best_id: int | None = None
        best_sim = -1.0
        for cid_int in cohort_ids:
            v = store.creative_vectors.get(cid_int)
            if v is None:
                continue
            sim = float(np.dot(source_vec, v))
            if sim > best_sim:
                best_sim = sim
                best_id = cid_int
        if best_id is None:
            return None
        winner_id = best_id
        similarity = max(0.0, min(1.0, best_sim))

    winner = store.creative_detail.get(winner_id)
    if winner is None:
        return None

    diffs: list[dict[str, Any]] = []
    largest_field = "default"
    largest_template_magnitude = 0.0
    for field_name in _TWIN_FIELDS:
        sv = source.get(field_name)
        wv = winner.get(field_name)
        if sv == wv:
            continue
        diffs.append(_diff_row(field_name, sv, wv))
        # Only score template-eligible fields against each other so 0–1 scores
        # are not dominated by raw counts.
        if field_name in _VISION_TEMPLATES:
            magnitude = _diff_magnitude(field_name, sv, wv)
            if magnitude > largest_template_magnitude:
                largest_template_magnitude = magnitude
                largest_field = field_name

    segment = {"vertical": source["vertical"], "format": source["format"]}
    template = _VISION_TEMPLATES.get(largest_field, _VISION_TEMPLATES["default"])
    template_insight = {
        "headline": template["headline"],
        "body": template["body"],
        "confidence": 0.74,
    }

    # Try Gemma; on success the response is non-stub (UI hides [preview] chip).
    llm_insight = await vision_insight_agent.generate_insight(
        source=source,
        winner=winner,
        diffs=diffs,
        segment=segment,
    )
    insight = llm_insight or template_insight
    is_stub = llm_insight is None

    return {
        "fatigued_id": creative_id,
        "winner_id": winner_id,
        "similarity": round(similarity, 3),
        "segment": segment,
        "diffs": diffs,
        "vision_insight": insight,
        # is_stub now reflects only the Vision Insight provenance — the twin
        # pick itself is real attribute-cosine matching.
        "is_stub": is_stub,
    }


def _diff_row(field_name: str, sv: Any, wv: Any) -> dict[str, Any]:
    direction = "neu"
    impact = "low"
    if isinstance(sv, (int, float)) and isinstance(wv, (int, float)):
        delta = (wv - sv) if sv is not None and wv is not None else 0
        if delta > 0:
            direction = "pos"
        elif delta < 0:
            direction = "neg"
        magnitude = abs(delta) / (abs(sv) + 1e-6) if sv else abs(delta)
        if magnitude > 0.5:
            impact = "high"
        elif magnitude > 0.15:
            impact = "medium"
    elif isinstance(wv, str) and isinstance(sv, str):
        impact = "medium"
    return {
        "field": field_name,
        "source_value": sv,
        "twin_value": wv,
        "direction": direction,
        "impact": impact,
    }


def _diff_magnitude(field_name: str, sv: Any, wv: Any) -> float:
    if isinstance(sv, (int, float)) and isinstance(wv, (int, float)):
        return abs((wv or 0) - (sv or 0))
    if sv != wv:
        return 1.0
    return 0.0


def _campaign_record(row: pd.Series) -> dict[str, Any]:
    record = row.to_dict()
    return to_jsonable(record)
