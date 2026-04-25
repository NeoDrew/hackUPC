"""Per-creative fatigue prediction.

Two-stage system:

1. **Maximum-likelihood changepoint detector** locates *where* a
   creative's CTR broke, using a binomial likelihood-ratio scan over
   every candidate split point in the daily clicks/impressions series.
   This gives the changepoint day + the pre-/post-rates.

2. **Trained logistic regression classifier** decides *whether* what
   the changepoint detector found is actually fatigue, vs end-of-
   flight tail-off (which every creative has in this synthetic
   dataset). Features: launch CTR vs cohort baseline, late CTR vs
   cohort baseline, run-over-run drop, log-likelihood ratio, daily-CTR
   variance, days-active. Training labels = the dataset's
   ``creative_status == 'fatigued'`` column — used here as supervised
   ground truth, NOT as a runtime input.

The classifier is **trained offline** by ``scripts/train_fatigue.py``,
serialized with joblib to ``backend/models/fatigue_classifier.joblib``
and committed to the repo. ``Datastore`` loads this artifact at startup;
training only re-runs if the artifact is missing (first boot on a
fresh checkout, or after the dataset changes).

The dataset's ``fatigue_day`` column is never used.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ..datastore import Datastore

log = logging.getLogger(__name__)

MODEL_VERSION = "v2"
MODEL_PATH = (
    Path(__file__).resolve().parents[2] / "models" / f"fatigue_classifier_{MODEL_VERSION}.joblib"
)


# Minimum days a creative must have run before we'll attempt fatigue
# detection. Below this, the changepoint search is unstable.
_MIN_DAYS = 14
# Search window — leave at least 7 days on each side of any candidate
# breakpoint so the pre/post means are stable.
_MIN_PRE_DAYS = 7
_MIN_POST_DAYS = 7


def prepare_fatigue_timeseries(store: Datastore, creative_id: int) -> pd.DataFrame:
    """Pull the daily impressions/clicks series for a creative and build
    a 7-day rolling CTR (sum-of-numerators / sum-of-denominators, not a
    mean of daily ratios). Returns an empty frame with the expected
    columns if the creative has no data.

    Zero-impression days keep ``ctr = NaN`` so downstream consumers
    (charts, feature extraction) can distinguish "no traffic" from
    "served but nobody clicked" — per the dataset trap on un-served
    budget days documented in resources/smadex/dataset_notes.md.
    """
    points = store.timeseries_by_creative.get(creative_id)
    if not points:
        return pd.DataFrame(
            columns=[
                "date",
                "impressions",
                "clicks",
                "conversions",
                "spend_usd",
                "revenue_usd",
                "ctr",
                "rolling_7d_ctr",
            ]
        )

    df = pd.DataFrame(points).sort_values("date").reset_index(drop=True)
    df["date"] = pd.to_datetime(df["date"])
    impr = df["impressions"].astype(float)
    clk = df["clicks"].astype(float)
    df["ctr"] = clk / impr.replace(0, np.nan)

    rolling_imp = impr.rolling(window=7, min_periods=1).sum()
    rolling_clk = clk.rolling(window=7, min_periods=1).sum()
    df["rolling_7d_ctr"] = rolling_clk / rolling_imp.replace(0, np.nan)
    return df


def extract_features(
    df: pd.DataFrame,
    *,
    cohort_first_median: float = 0.0,
    cohort_last_p25: float = 0.0,
) -> dict[str, float] | None:
    """Compute the feature vector for one creative. Returns None if the
    series is too short to score reliably."""
    if df.empty or len(df) < _MIN_DAYS:
        return None
    impr = df["impressions"].to_numpy(dtype=float)
    clk = df["clicks"].to_numpy(dtype=float)
    n = len(impr)
    total_imp = impr.sum()
    total_clk = clk.sum()
    if total_imp <= 0 or total_clk <= 0:
        return None

    n_anchor = min(7, n // 3)
    f_imp = impr[:n_anchor].sum()
    f_clk = clk[:n_anchor].sum()
    l_imp = impr[-n_anchor:].sum()
    l_clk = clk[-n_anchor:].sum()
    p_first = float(f_clk / f_imp) if f_imp > 0 else 0.0
    p_last = float(l_clk / l_imp) if l_imp > 0 else 0.0
    drop_ratio = (p_last / p_first) if p_first > 0 else 1.0

    cp = _changepoint_lr(impr, clk)
    if cp is None:
        return None
    best_k, lr_stat, p_pre, p_post = cp

    daily_ctr = clk / np.maximum(impr, 1.0)
    ctr_mean = float(daily_ctr.mean())
    ctr_std = float(daily_ctr.std())

    # Peak-to-last drawdown: ratio of last 7-day rolling mean to its lifetime
    # peak. Captures decline from personal-best regardless of launch level.
    rolling = pd.Series(daily_ctr).rolling(7, min_periods=1).mean()
    peak_roll = float(rolling.max())
    last_roll = float(rolling.iloc[-1])
    peak_to_last_drawdown = (last_roll / peak_roll) if peak_roll > 1e-9 else 1.0

    first_vs_cohort = (
        p_first / cohort_first_median if cohort_first_median > 0 else 1.0
    )
    last_vs_cohort = (
        p_last / cohort_last_p25 if cohort_last_p25 > 0 else 1.0
    )

    return {
        "p_first": p_first,
        "p_last": p_last,
        "drop_ratio": drop_ratio,
        "first_vs_cohort": first_vs_cohort,
        "last_vs_cohort": last_vs_cohort,
        "lr_stat": float(lr_stat),
        "log_total_impr": float(np.log1p(total_imp)),
        "ctr_cv": float(ctr_std / max(ctr_mean, 1e-9)),
        "days_active": float(n),
        "best_k": float(best_k),
        "p_pre": float(p_pre),
        "p_post": float(p_post),
        "peak_to_last_drawdown": float(peak_to_last_drawdown),
    }


def _changepoint_lr(impr: np.ndarray, clk: np.ndarray) -> tuple[int, float, float, float] | None:
    """MLE binomial changepoint scan. Returns (best_k, LR, p_pre, p_post)
    or None if no valid candidate was found."""
    n = len(impr)
    cum_imp = np.cumsum(impr)
    cum_clk = np.cumsum(clk)
    total_imp = cum_imp[-1]
    total_clk = cum_clk[-1]
    p0 = total_clk / total_imp if total_imp > 0 else 0.0
    if p0 <= 0 or p0 >= 1:
        return None
    ll_null = total_clk * np.log(p0) + (total_imp - total_clk) * np.log(1 - p0)
    best_k = -1
    best_lr = -np.inf
    best_p1 = 0.0
    best_p2 = 0.0
    for k in range(_MIN_PRE_DAYS, n - _MIN_POST_DAYS + 1):
        pre_imp = cum_imp[k - 1]
        pre_clk = cum_clk[k - 1]
        post_imp = total_imp - pre_imp
        post_clk = total_clk - pre_clk
        if pre_imp <= 0 or post_imp <= 0:
            continue
        p1 = pre_clk / pre_imp
        p2 = post_clk / post_imp
        if p1 <= 0 or p2 <= 0 or p1 >= 1 or p2 >= 1:
            continue
        if p2 >= p1:
            continue
        ll_full = (
            pre_clk * np.log(p1)
            + (pre_imp - pre_clk) * np.log(1 - p1)
            + post_clk * np.log(p2)
            + (post_imp - post_clk) * np.log(1 - p2)
        )
        lr = 2.0 * (ll_full - ll_null)
        if lr > best_lr:
            best_lr = lr
            best_k = k
            best_p1 = p1
            best_p2 = p2
    if best_k < 0:
        return None
    return int(best_k), float(best_lr), float(best_p1), float(best_p2)


_FEATURE_NAMES: list[str] = [
    "first_vs_cohort",
    "last_vs_cohort",
    "drop_ratio",
    "lr_stat",
    "log_total_impr",
    "ctr_cv",
    "days_active",
    # Added: high permutation importance per research/fatigue_kpi_research.ipynb
    "p_pre",                  # rank 2 — absolute pre-changepoint CTR level
    "peak_to_last_drawdown",  # rank 3 — decline from personal-peak, not just first-7d
]


def train_classifier(
    feature_rows: list[dict[str, float]],
    labels: list[int],
) -> tuple[Any, float]:
    """Fit logistic regression on the engineered features. Returns
    (model, threshold) — threshold maximizes F1 on the training set
    (no held-out split since we only have 199 positives across 1080
    creatives)."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import Pipeline

    X = np.array([[r[f] for f in _FEATURE_NAMES] for r in feature_rows])
    y = np.array(labels)

    pipe = Pipeline([
        ("scale", StandardScaler()),
        ("lr", LogisticRegression(class_weight="balanced", max_iter=200)),
    ])
    pipe.fit(X, y)

    probs = pipe.predict_proba(X)[:, 1]
    # Sweep thresholds, pick F1-max.
    best_t = 0.5
    best_f1 = -1.0
    for t in np.linspace(0.05, 0.95, 91):
        pred = probs >= t
        tp = int(((pred == 1) & (y == 1)).sum())
        fp = int(((pred == 1) & (y == 0)).sum())
        fn = int(((pred == 0) & (y == 1)).sum())
        if tp == 0:
            continue
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        if f1 > best_f1:
            best_f1 = f1
            best_t = float(t)
    log.info(
        "fatigue classifier fit: F1=%.3f threshold=%.2f n_pos=%d n=%d",
        best_f1,
        best_t,
        int(y.sum()),
        len(y),
    )
    return pipe, best_t


def save_classifier(pipe: Any, threshold: float, feature_names: list[str]) -> Path:
    """Persist the trained pipeline + threshold + feature schema to
    ``MODEL_PATH``. The schema is bundled with the model so a future
    refactor can reject a stale artifact instead of mis-aligning
    features at inference time."""
    import joblib

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    artifact = {
        "model_version": MODEL_VERSION,
        "pipeline": pipe,
        "threshold": float(threshold),
        "feature_names": list(feature_names),
    }
    joblib.dump(artifact, MODEL_PATH)
    return MODEL_PATH


def load_classifier() -> tuple[Any | None, float]:
    """Load the trained pipeline + threshold from ``MODEL_PATH``.
    Returns ``(None, 0.5)`` if the artifact is missing, the version
    doesn't match, or the feature schema has drifted (so the caller
    can fall back to retraining)."""
    if not MODEL_PATH.exists():
        log.info("fatigue model artifact not found at %s — caller must train", MODEL_PATH)
        return None, 0.5
    try:
        import joblib

        artifact = joblib.load(MODEL_PATH)
    except Exception as e:  # noqa: BLE001
        log.warning("failed to load fatigue model: %s", e)
        return None, 0.5
    if artifact.get("model_version") != MODEL_VERSION:
        log.info(
            "fatigue model version mismatch (artifact=%s, code=%s) — retraining",
            artifact.get("model_version"),
            MODEL_VERSION,
        )
        return None, 0.5
    if artifact.get("feature_names") != _FEATURE_NAMES:
        log.info("fatigue model feature schema drifted — retraining")
        return None, 0.5
    log.info(
        "loaded fatigue classifier from %s (threshold=%.2f)",
        MODEL_PATH,
        artifact["threshold"],
    )
    return artifact["pipeline"], float(artifact["threshold"])


def identify_fatigue_changepoint(
    df: pd.DataFrame,
    *,
    cohort_first_median: float | None = None,
    cohort_last_p25: float | None = None,
    classifier: Any | None = None,
    threshold: float = 0.5,
) -> dict[str, Any]:
    """Score one creative's daily series.

    Runs the binomial-LR changepoint scan to locate the best break, then
    asks the trained classifier whether what was found is fatigue or
    end-of-flight noise. Returns a flat dict ready to attach to the
    creative detail payload.

    ``cohort_first_median`` / ``cohort_last_p25``: cohort baselines used
    by ``extract_features`` to compute ``first_vs_cohort`` and
    ``last_vs_cohort``. Computed once per (vertical, format) cohort at
    Datastore boot.

    ``classifier``: the fitted scikit-learn pipeline from
    ``load_classifier`` / ``train_classifier``. If ``None``, returns the
    base "no verdict" payload — the system intentionally has no heuristic
    fallback so a missing model is loud, not silent.
    """
    base = {
        "is_fatigued": False,
        "predicted_fatigue_day": None,
        "predicted_fatigue_date": None,
        "fatigue_ctr_drop": None,
        "p_value": None,
        "is_significant": False,
        "pre_ctr": None,
        "post_ctr": None,
        "cohort_first_median": round(cohort_first_median or 0.0, 6),
        "cohort_last_p25": round(cohort_last_p25 or 0.0, 6),
        "model_score": None,
    }
    if df.empty or len(df) < _MIN_DAYS:
        return base
    if classifier is None:
        log.warning("identify_fatigue_changepoint called without a classifier")
        return base

    impr = df["impressions"].to_numpy(dtype=float)
    clk = df["clicks"].to_numpy(dtype=float)

    cp = _changepoint_lr(impr, clk)
    if cp is None:
        return base
    best_k, best_lr, p_pre, p_post = cp

    feats = extract_features(
        df,
        cohort_first_median=cohort_first_median or 0.0,
        cohort_last_p25=cohort_last_p25 or 0.0,
    )
    if feats is None:
        return base

    x = np.array([[feats[f] for f in _FEATURE_NAMES]])
    prob = float(classifier.predict_proba(x)[0, 1])
    is_fatigued = prob >= threshold

    # Bonferroni-adjusted chi²(1) p-value over the candidate scan, kept
    # for transparency in the UI even though the verdict is the
    # classifier's, not the test's.
    from scipy.stats import chi2  # local import: heavy

    n = len(impr)
    k_search = max(1, n - _MIN_PRE_DAYS - _MIN_POST_DAYS + 1)
    p_raw = float(chi2.sf(best_lr, df=1))
    p_adj = float(min(1.0, p_raw * k_search))

    predicted_date = (
        pd.Timestamp(df.iloc[best_k]["date"]).strftime("%Y-%m-%d")
        if is_fatigued
        else None
    )

    return {
        "is_fatigued": bool(is_fatigued),
        "predicted_fatigue_day": int(best_k) if is_fatigued else None,
        "predicted_fatigue_date": predicted_date,
        "fatigue_ctr_drop": float(1.0 - (p_post / p_pre)) if is_fatigued and p_pre > 0 else None,
        "p_value": p_adj,
        "is_significant": bool(is_fatigued),
        "pre_ctr": round(p_pre, 6),
        "post_ctr": round(p_post, 6),
        "cohort_first_median": round(cohort_first_median or 0.0, 6),
        "cohort_last_p25": round(cohort_last_p25 or 0.0, 6),
        "model_score": round(prob, 4),
    }
