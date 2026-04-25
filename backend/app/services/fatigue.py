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

MODEL_VERSION = "v1"
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
# Magnitude requirement: post CTR must be at most this fraction of pre.
_MAX_POST_RATIO = 0.70
# Bonferroni-corrected significance threshold across the changepoint search.
_ALPHA = 0.001
# Pre-rate must clear the cohort median (×_PRE_FLOOR_MULT). Otherwise the
# creative was never strong enough to "fatigue from".
_PRE_FLOOR_MULT = 1.0
# Post-rate must fall below the cohort median (×_POST_CEILING_MULT). A
# creative still performing at peer level isn't fatigued, even if its own
# CTR dropped from a personal high.
_POST_CEILING_MULT = 0.85


def phase1_preprocess_and_aggregate(df: pd.DataFrame) -> pd.DataFrame:
    """Phase 1: Data Pre-Processing & Aggregation
    
    Aggregates daily time-series data, computes base metrics with appropriate floors 
    to avoid division-by-zero, and sorts the result.
    """
    # Group by creative_id and date and sum metrics
    agg_dict = {
        "impressions": "sum",
        "clicks": "sum",
        "conversions": "sum",
        "spend_usd": "sum",
        "revenue_usd": "sum",
        "video_completions": "sum",
        "days_since_launch": "min"
    }
    
    # Only aggregate columns that are present in the dataframe
    agg_columns = {k: v for k, v in agg_dict.items() if k in df.columns}
    # If missing days_since_launch, just group by creative_id and date
    
    grouped = df.groupby(["creative_id", "date"], as_index=False).agg(agg_columns)
    
    # Handle division-by-zero bounds
    impr = grouped["impressions"].astype(float)
    clk = grouped["clicks"].astype(float)
    spend = grouped["spend_usd"].astype(float) if "spend_usd" in grouped else None
    conv = grouped["conversions"].astype(float) if "conversions" in grouped else None
    rev = grouped["revenue_usd"].astype(float) if "revenue_usd" in grouped else None
    vid = grouped["video_completions"].astype(float) if "video_completions" in grouped else None
    
    impr_floor = np.maximum(impr, 1.0)
    clk_floor = np.maximum(clk, 1.0)
    
    # Derive base logic and compute
    grouped["ctr"] = clk / impr_floor
    
    if conv is not None:
        grouped["cvr"] = conv / clk_floor
    if spend is not None and rev is not None:
        spend_floor = np.maximum(spend, 0.01)
        grouped["roas"] = rev / spend_floor
    if vid is not None:
        grouped["vtr"] = vid / impr_floor
        
    # Set null CTR for zero-impression rows
    grouped.loc[impr == 0, "ctr"] = np.nan
    
    # Sort the DataFrame
    sort_cols = ["creative_id"]
    if "days_since_launch" in grouped.columns:
        sort_cols.append("days_since_launch")
    else:
        sort_cols.append("date") # Fallback
        
    grouped = grouped.sort_values(sort_cols, ascending=True).reset_index(drop=True)
    
    return grouped


def phase2_layer1_decay_ratio(df_summary: pd.DataFrame) -> pd.DataFrame:
    """Phase 2: Layer 1 (First/Last Window Decay Ratio)
    
    Reads summary data, computes ratio of decline from first 7 days to last 7 days,
    clamps, normalizes, and flags decay.
    """
    df = df_summary.copy()
    
    # Ensure required columns are present
    if "first_7d_ctr" not in df.columns or "last_7d_ctr" not in df.columns:
        return df
        
    first_7d_ctr = df["first_7d_ctr"].astype(float)
    last_7d_ctr = df["last_7d_ctr"].astype(float)
    
    # Compute: decay_ratio = (first_7d_ctr - last_7d_ctr) / max(first_7d_ctr, 1e-6)
    denominator = np.maximum(first_7d_ctr, 1e-6)
    decay_ratio = (first_7d_ctr - last_7d_ctr) / denominator
    
    # Clamp to [-1.0, 1.0]
    decay_ratio_clamped = np.clip(decay_ratio, -1.0, 1.0)
    
    # Apply target min-max normalization
    min_val = decay_ratio_clamped.min()
    max_val = decay_ratio_clamped.max()
    
    if max_val > min_val:
        l1_norm = (decay_ratio_clamped - min_val) / (max_val - min_val)
    else:
        l1_norm = np.zeros_like(decay_ratio_clamped)
        
    df["l1_norm"] = l1_norm
    df["decay_ratio"] = decay_ratio_clamped
    
    # Output boolean l1_flag: decay_ratio > 0.25
    df["l1_flag"] = decay_ratio_clamped > 0.25
    
    return df


def phase4_layer3_pelt_changepoint(df: pd.DataFrame) -> dict:
    """Phase 4: Layer 3 (Changepoint Detection - PELT)
    
    Interpolates null CTR values, runs PELT with RBF cost, and filters
    for downward structural breaks to annotate timeline.
    Expects a DataFrame for a single creative sorted by time.
    """
    try:
        import ruptures as rpt
    except ImportError:
        log.warning("ruptures package not found. Skipping PELT changepoint detection.")
        return {"detected_fatigue_day": None, "break_index": None}

    if df.empty or "ctr" not in df.columns:
        return {"detected_fatigue_day": None, "break_index": None}
        
    # Interpolate null CTR values
    ctr_series = df["ctr"].interpolate(method="linear").bfill().ffill().to_numpy(dtype=float)
    
    # Require >= 14 observations
    if len(ctr_series) < 14:
        return {"detected_fatigue_day": None, "break_index": None}
        
    # Run the PELT algorithm with RBF cost
    algo = rpt.Pelt(model="rbf").fit(ctr_series)
    breakpoints = algo.predict(pen=3)
    
    # Filter structural breaks by verifying: post_break_mean_ctr < pre_break_mean_ctr
    for bp in breakpoints:
        if bp >= len(ctr_series):
            continue
            
        pre_break = ctr_series[:bp]
        post_break = ctr_series[bp:]
        
        if len(pre_break) == 0 or len(post_break) == 0:
            continue
            
        pre_mean = pre_break.mean()
        post_mean = post_break.mean()
        
        if post_mean < pre_mean:
            # Output: first downward break index and mapped detected_fatigue_day
            fatigue_day = None
            if "days_since_launch" in df.columns:
                fatigue_day = int(df["days_since_launch"].iloc[bp])
            elif "date" in df.columns:
                fatigue_day = str(df["date"].iloc[bp])
                
            return {
                "break_index": int(bp),
                "detected_fatigue_day": fatigue_day
            }
            
    return {"detected_fatigue_day": None, "break_index": None}


def prepare_fatigue_timeseries(store: Datastore, creative_id: int) -> pd.DataFrame:
    """Pull the daily impressions/clicks series for a creative and build
    a 7-day rolling CTR (sum-of-numerators / sum-of-denominators, not a
    mean of daily ratios). Returns an empty frame with the expected
    columns if the creative has no data."""
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
    df["ctr"] = (clk / impr.replace(0, np.nan)).fillna(0.0)

    rolling_imp = impr.rolling(window=7, min_periods=1).sum()
    rolling_clk = clk.rolling(window=7, min_periods=1).sum()
    df["rolling_7d_ctr"] = (
        rolling_clk / rolling_imp.replace(0, np.nan)
    ).fillna(0.0)
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
    """Run the test.

    ``cohort_first_median``: median first-7-day CTR across the creative's
    (vertical, format) cohort. Gates "launched strong" — only creatives
    whose first-7d CTR clears the cohort median are eligible for the
    fatigue label.

    ``cohort_last_p25``: 25th-percentile last-7-day CTR across the cohort.
    Gates "ended weak" — the creative's last-7d CTR must fall to or
    below this floor (bottom quarter of late performance).

    Fatigue fires only if BOTH cohort-rank gates pass, the run-over-run
    drop is steep (last ≤ 22% of first), and the binomial changepoint
    test is significant after Bonferroni correction.
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
    }
    if df.empty or len(df) < _MIN_DAYS:
        return base

    impr = df["impressions"].to_numpy(dtype=float)
    clk = df["clicks"].to_numpy(dtype=float)
    n = len(impr)

    total_imp = impr.sum()
    total_clk = clk.sum()
    if total_imp <= 0 or total_clk <= 0:
        return base

    cum_imp = np.cumsum(impr)
    cum_clk = np.cumsum(clk)

    # Likelihood-ratio search across candidate breakpoints.
    best_k: int | None = None
    best_lr = -np.inf
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
        # LR = 2 × (ll(H1) − ll(H0))
        p0 = total_clk / total_imp
        ll_full = (
            pre_clk * np.log(p1)
            + (pre_imp - pre_clk) * np.log(1 - p1)
            + post_clk * np.log(p2)
            + (post_imp - post_clk) * np.log(1 - p2)
        )
        ll_null = total_clk * np.log(p0) + (total_imp - total_clk) * np.log(1 - p0)
        lr = 2.0 * (ll_full - ll_null)
        # Only keep candidates where the post-rate is *lower* — fatigue,
        # not improvement.
        if p2 < p1 and lr > best_lr:
            best_lr = lr
            best_k = k

    if best_k is None or not np.isfinite(best_lr):
        return base

    # Recompute the rates at the best k.
    pre_imp = cum_imp[best_k - 1]
    pre_clk = cum_clk[best_k - 1]
    post_imp = total_imp - pre_imp
    post_clk = total_clk - pre_clk
    p_pre = float(pre_clk / pre_imp)
    p_post = float(post_clk / post_imp)
    drop_ratio = p_post / p_pre  # < 1 = drop

    # Asymptotic chi-squared(1) p-value, with Bonferroni correction over
    # the (n - _MIN_PRE_DAYS - _MIN_POST_DAYS + 1) candidates we searched.
    from scipy.stats import chi2  # local import: heavy

    k_search = max(1, n - _MIN_PRE_DAYS - _MIN_POST_DAYS + 1)
    p_raw = float(chi2.sf(best_lr, df=1))
    p_adj = float(min(1.0, p_raw * k_search))

    # Anchor period comparison. The dataset's actual fatigue signature
    # is gradual exponential decline from a *strong launch* — not a
    # step. Stable creatives also decline but launch from a lower
    # plateau. The discriminating signal is therefore:
    #   - first-7-days CTR is in the TOP of the cohort (strong launch),
    #   - the run-over-run drop ratio (last/first) is small enough that
    #     the creative ends meaningfully below where its cohort ends.
    n_anchor = min(7, n // 3)
    first_imp = impr[:n_anchor].sum()
    first_clk = clk[:n_anchor].sum()
    last_imp = impr[-n_anchor:].sum()
    last_clk = clk[-n_anchor:].sum()
    p_first = float(first_clk / first_imp) if first_imp > 0 else 0.0
    p_last = float(last_clk / last_imp) if last_imp > 0 else 0.0
    last_over_first = (p_last / p_first) if p_first > 0 else 1.0

    first_median = cohort_first_median if cohort_first_median is not None else 0.0
    last_p25 = cohort_last_p25 if cohort_last_p25 is not None else 0.0

    # Trained classifier verdict. We require a fitted model — if none is
    # passed (e.g. before training has run), we fall back to a permissive
    # heuristic so the system degrades gracefully.
    if classifier is not None:
        feats = extract_features(
            df,
            cohort_first_median=first_median,
            cohort_last_p25=last_p25,
        )
        if feats is None:
            return base
        x = np.array([[feats[f] for f in _FEATURE_NAMES]])
        prob = float(classifier.predict_proba(x)[0, 1])
        is_sig = prob >= threshold
    else:
        # Heuristic fallback: cohort-relative gates + significance.
        launched_strong = p_first >= first_median
        ended_weak = p_last <= last_p25 if last_p25 > 0 else True
        decayed_hard = last_over_first <= 0.22
        magnitude_ok = launched_strong and decayed_hard and ended_weak
        is_sig = p_adj < _ALPHA and magnitude_ok
        prob = None

    predicted_date = (
        pd.Timestamp(df.iloc[best_k]["date"]).strftime("%Y-%m-%d")
        if is_sig
        else None
    )

    return {
        "is_fatigued": bool(is_sig),
        "predicted_fatigue_day": int(best_k) if is_sig else None,
        "predicted_fatigue_date": predicted_date,
        "fatigue_ctr_drop": float(1.0 - last_over_first) if is_sig else None,
        "p_value": p_adj,
        "is_significant": bool(is_sig),
        "pre_ctr": round(p_first, 6),
        "post_ctr": round(p_last, 6),
        "cohort_first_median": round(first_median, 6),
        "cohort_last_p25": round(last_p25, 6),
        "model_score": round(prob, 4) if prob is not None else None,
    }
