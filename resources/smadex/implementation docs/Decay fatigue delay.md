# Fatigue Decay Detection — Engineering Specification

**Module:** Creative Fatigue Detection  
**Version:** 1.0  
**Status:** Ready for Implementation  
**Depends on:** Smadex Creative Intelligence Dataset (pre-processed)  
**Produces:** Per-creative fatigue scores, timing estimates, and classification flags

***

## 1. Purpose and Scope

This document specifies the complete implementation of creative fatigue detection for the Smadex Creative Intelligence prototype. Fatigue detection identifies ad creatives that are losing performance over time, assigns each a composite fatigue score, and — for creatives confirmed fatigued — estimates the day on which deterioration became material.

The system is built from four independent analytical layers, each producing a signal that feeds into a single composite score. The composite score is the primary classification output. A separate changepoint layer (Layer 3) is used exclusively for timing annotation and is not a classification input.

This specification covers all four layers in full:

- **Layer 1:** First/Last Window Decay Ratio (heuristic baseline)
- **Layer 2:** Rolling Window Linear Trend with Statistical Filtering
- **Layer 3:** Changepoint Detection for Fatigue-Day Estimation (annotation only)
- **Layer 4:** CUSUM Statistic for Sustained Drift Detection

The ground-truth columns `creative_status` and `fatigue_day` from `creative_summary.csv` are reserved exclusively for post-hoc validation. They must not be used as inputs to any layer.

***

## 2. Source Data and Join Requirements

### 2.1 Primary Tables

| Table | File | Role in this module |
|---|---|---|
| Daily time-series | `creative_daily_country_os_stats.csv` | Primary signal source for Layers 2, 3, and 4 |
| Creative summary | `creative_summary.csv` | Source for Layer 1 pre-aggregated columns; validation ground truth |
| Creatives metadata | `creatives.csv` | Enrichment for cohort benchmarking and explainability |
| Campaigns | `campaigns.csv` | Used for within-campaign normalisation |

### 2.2 Columns Required from Each Table

**`creative_daily_country_os_stats.csv`** — all of the following columns are required:

| Column | Type | Notes |
|---|---|---|
| `creative_id` | string/integer | Primary join key |
| `date` | date | Parse as datetime; used to derive `days_since_launch` ordering |
| `days_since_launch` | integer | Preferred x-axis for regressions; avoids date-alignment issues across creatives with different launch dates |
| `impressions` | integer | Denominator for all rate metrics |
| `clicks` | integer | Numerator for CTR |
| `conversions` | integer | Numerator for CVR |
| `spend_usd` | float | Denominator for ROAS |
| `revenue_usd` | float | Numerator for ROAS |
| `video_completions` | integer | Used only for `rewarded_video` and `playable` formats; treat zero values for other formats as expected, not missing |

Columns not listed above are not required for this module and may be ignored.

**`creative_summary.csv`** — only the following columns are required for Layer 1 and validation:

| Column | Type | Notes |
|---|---|---|
| `creative_id` | string/integer | Join key |
| `first_7d_ctr` | float | Pre-aggregated average CTR over the first 7 days after launch |
| `last_7d_ctr` | float | Pre-aggregated average CTR over the last 7 days of available data |
| `creative_status` | string | Ground truth: `top_performer`, `stable`, `fatigued`, `underperformer` — validation only |
| `fatigue_day` | integer or null | Ground truth: day number when fatigue became material; blank for non-fatigued creatives — validation only |

**`creatives.csv`** — required for cohort enrichment only:

| Column | Type | Notes |
|---|---|---|
| `creative_id` | string/integer | Join key |
| `format` | string | Used to segment CUSUM benchmarks by format type |
| `vertical` | string | Used for within-vertical normalisation |
| `campaign_id` | string/integer | Used for within-campaign ranking |

***

## 3. Pre-Processing: Global Daily Aggregation

Before any layer can run, the daily time-series table must be aggregated to remove the country and OS dimensions. Every layer in this module operates on one row per `(creative_id, date)`, not one row per `(creative_id, date, country, os)`.

### 3.1 Aggregation Specification

Group by `creative_id` and `date`. For each group, sum all numeric metric columns: `impressions`, `clicks`, `conversions`, `spend_usd`, `revenue_usd`, `video_completions`. Take the minimum value of `days_since_launch` within each group (it should be constant per creative-date pair, but take the minimum defensively to avoid duplicates from any data anomalies).

### 3.2 Derived Metric Columns

After aggregation, compute the following derived columns. These are the actual signal columns used by Layers 2, 3, and 4:

| Derived Column | Formula | Notes |
|---|---|---|
| `ctr` | `clicks / max(impressions, 1)` | Clip denominator at 1 to prevent division by zero |
| `cvr` | `conversions / max(clicks, 1)` | Clip denominator at 1 |
| `roas` | `revenue_usd / max(spend_usd, 0.01)` | Clip denominator at 0.01 USD |
| `vtr` | `video_completions / max(impressions, 1)` | Only meaningful for `rewarded_video` and `playable` formats |

CTR is the primary fatigue signal. CVR and ROAS are secondary confirmation signals and are not used in the composite score formula but should be computed for display purposes.

### 3.3 Sorting Requirement

After aggregation and metric derivation, sort the resulting frame by `creative_id` ascending, then `days_since_launch` ascending. This sort order must be maintained for all rolling and sequential operations in Layers 2, 3, and 4. Any operation that groups by `creative_id` and performs row-sequential logic depends on this sort being stable.

### 3.4 Critical Data Handling Notes

- **`impressions_last_7d` is a rolling window column in the source data.** It must not be summed across dates; doing so double-counts. Do not carry this column into the aggregated frame.
- **Zero `video_completions` for banner and native formats** is by design, not missing data. Do not flag or impute these rows.
- **Rows where `impressions = 0` but `spend_usd > 0`** may exist on early days of a campaign (allocated but un-served budget). These rows should be retained in the frame but excluded from rolling CTR window calculations by treating them as null CTR values rather than zero CTR values. The distinction matters: a zero CTR from a day with real impressions is a genuine signal; a zero CTR from an un-served day is noise.

***

## 4. Layer 1 — First/Last Window Decay Ratio

### 4.1 Purpose

Layer 1 is the simplest and most interpretable fatigue signal. It measures the proportional drop in CTR between a creative's launch period and its most recent period using the pre-aggregated `first_7d_ctr` and `last_7d_ctr` columns from `creative_summary.csv`. It requires no time-series processing and runs directly on the summary table.

### 4.2 Input

One row per `creative_id` from `creative_summary.csv`, specifically the columns `creative_id`, `first_7d_ctr`, and `last_7d_ctr`.

### 4.3 Computation Steps

**Step 1: Compute raw decay ratio.**

For each creative, compute the proportional CTR decline as:

$$ \text{decay\_ratio} = \frac{\text{first\_7d\_ctr} - \text{last\_7d\_ctr}}{\max(\text{first\_7d\_ctr},\; \epsilon)} $$

where $$\epsilon$$ is a small constant (recommended: 1×10⁻⁶) to prevent division by zero for creatives with effectively zero early CTR.

**Step 2: Clamp to valid range.**

Clamp the result to the range [−1.0, 1.0]. A negative value indicates the creative improved over time (last period better than first); a value of 1.0 indicates complete collapse. Both extremes are meaningful and should be preserved, not zeroed.

**Step 3: Apply threshold flag.**

Set a binary `l1_flag` to true if `decay_ratio` exceeds 0.25 (i.e., a 25% or greater proportional CTR decline). This threshold is the initial recommended value based on industry norms, but it should be treated as a tuneable parameter during validation against the ground truth.

### 4.4 Output Columns

| Column | Type | Description |
|---|---|---|
| `creative_id` | key | Join key |
| `decay_ratio` | float [−1, 1] | Proportional CTR decline; positive = declining |
| `l1_flag` | boolean | True if `decay_ratio > 0.25` |

### 4.5 Limitations

Layer 1 is blind to the timing and shape of the decline. A creative that peaked on day 10 and stabilised at a new lower level produces the same `decay_ratio` as one that is still actively declining on the final day. It is also sensitive to noisy first-7-day data when early impressions are low. These limitations are addressed by Layers 2 and 4.

***

## 5. Layer 2 — Rolling Window Linear Trend

### 5.1 Purpose

Layer 2 detects whether a creative's CTR is in a statistically significant downward trend. It operates on the aggregated daily time-series frame (one row per `creative_id` × `date`) and uses a rolling 7-day smoothed CTR as input to a per-creative linear regression.

### 5.2 Input

The global daily aggregated frame produced in Section 3, sorted by `creative_id` ascending then `days_since_launch` ascending. Required columns: `creative_id`, `days_since_launch`, `ctr` (derived), and — for rows where `impressions = 0` — the null CTR flag described in Section 3.4.

### 5.3 Computation Steps

**Step 1: Compute 7-day rolling CTR, grouped per creative.**

Within each `creative_id` group, compute a trailing 7-day rolling mean of `ctr`. Use a minimum window of 3 valid (non-null) observations to produce a value; rows with fewer than 3 valid observations in the trailing window produce a null rolling CTR. This operation must be performed on the sorted frame described in Section 3.3, and the result must be written back to the same frame as a new column `ctr_7d`.

> **Implementation note:** The rolling window and the regression groupby must operate on the same dataframe. The rolling window computation produces `ctr_7d` as a column on the daily frame. The per-creative regression then reads this column from the same frame. Using two different frames for these two operations is a bug that will cause the regression to fall back to raw `ctr` or raise an error.

**Step 2: Per-creative linear regression.**

For each `creative_id`, collect all rows where `ctr_7d` is not null. If fewer than 10 such rows exist, skip regression for this creative and assign a slope of 0.0 and a p-value of 1.0. This minimum-row guard prevents unstable regressions on short-lived or sparse creatives.

For creatives passing the guard, fit a simple ordinary least-squares linear regression of `ctr_7d` on `days_since_launch`. Record the fitted slope and the associated two-tailed p-value for the slope coefficient.

> **Do not forward-fill null `ctr_7d` values before regression.** Forward-filling artificially extends the last known rolling mean across sparse periods, which biases the slope toward zero in the early portion of a series where windows are still filling. Instead, pass only non-null rows to the regression (using a `dropna` on `ctr_7d`). The `len(valid_rows) < 10` guard mitigates instability from short series.

**Step 3: Statistical significance filter.**

A negative slope is only meaningful if statistically significant. Set a binary `l2_sig_negative` flag to true only if the slope is strictly negative AND the p-value is strictly less than 0.05. Creatives with a negative slope that does not meet the significance threshold are treated as stable for Layer 2's purposes.

**Step 4: Normalise slope for composite input.**

Compute `l2_score` as the normalised absolute value of the slope across all creatives where `l2_sig_negative` is true. Creatives where the flag is false receive `l2_score = 0.0`. Normalisation is min-max across the full creative population (not per-campaign or per-vertical), so that the score is on a [1] scale for composite assembly.

### 5.4 Output Columns

| Column | Type | Description |
|---|---|---|
| `creative_id` | key | Join key |
| `slope` | float | OLS slope of `ctr_7d` on `days_since_launch`; negative = declining |
| `slope_pval` | float [1] | Two-tailed p-value for the slope coefficient |
| `l2_sig_negative` | boolean | True if slope < 0 AND p-value < 0.05 |
| `l2_score` | float [1] | Normalised magnitude of significant negative slope; 0 if not significant |

***

## 6. Layer 3 — Changepoint Detection (Timing Annotation)

### 6.1 Purpose and Scope

Layer 3 estimates the day on which a creative's CTR underwent a structural break — the point in time where the level or trend changed significantly. This output is used **exclusively for UI annotation and timing comparison against the ground-truth `fatigue_day`**. Layer 3 output does not contribute to the composite fatigue score.

The reason for this separation is that changepoint detection is well-suited for answering "when did fatigue start?" but adds minimal incremental lift for the binary classification question of "is this creative fatigued?", which Layers 1, 2, and 4 already handle with fewer hyperparameters.

### 6.2 Input

The global daily aggregated frame from Section 3. Required columns: `creative_id`, `days_since_launch`, `ctr` (raw derived CTR, not the rolling mean). Raw CTR is preferred here because PELT is designed to find structural breaks in the underlying signal, and smoothing before detection can obscure the breakpoint location.

### 6.3 Algorithm: PELT with RBF Cost

Use the PELT (Pruned Exact Linear Time) algorithm with a radial basis function (RBF) cost. PELT finds the globally optimal segmentation of a time series for a given penalty. RBF cost is appropriate here because it detects changes in both mean and variance of the signal, which matches the pattern of creative fatigue (declining mean CTR, sometimes with increasing variance as the creative becomes less consistently effective).

The penalty parameter controls the sensitivity of detection. A lower penalty detects more changepoints; a higher penalty detects fewer. For this dataset, a recommended starting penalty of 3 is appropriate for 75-day series. This should be validated and potentially adjusted during the calibration phase described in Section 10.

A minimum segment size of 5 days is required. This prevents the algorithm from detecting one-day anomalies (e.g., a holiday spike or a data quality issue) as structural breaks.

### 6.4 Computation Steps

**Step 1: Per-creative series extraction.**

For each `creative_id`, extract the CTR values in `days_since_launch` order as a one-dimensional array. Null CTR values (from zero-impression days as defined in Section 3.4) should be linearly interpolated before passing to PELT. PELT requires a dense, gap-free series.

**Step 2: Minimum length guard.**

If the series has fewer than 14 observations, skip changepoint detection for this creative. Set `detected_fatigue_day` to null.

**Step 3: Run PELT.**

Fit the PELT model to the 1D CTR array. If the algorithm returns more than one segment (i.e., at least one changepoint was detected), record the index of the first detected changepoint. Convert this index back to a `days_since_launch` value by indexing into the sorted `days_since_launch` array for that creative. If no changepoints are found, set `detected_fatigue_day` to null.

**Step 4: Direction filter.**

A detected changepoint is only meaningful as a fatigue signal if the post-break mean is lower than the pre-break mean. If the post-break mean is equal to or higher than the pre-break mean, the changepoint represents recovery or a launch ramp-up, not fatigue. Set `detected_fatigue_day` to null in this case even if a break was detected.

### 6.5 Output Columns

| Column | Type | Description |
|---|---|---|
| `creative_id` | key | Join key |
| `detected_fatigue_day` | integer or null | The `days_since_launch` value of the first downward structural break; null if none detected or series too short |

### 6.6 Validation Use

After the full pipeline runs and validation is performed (Section 10), compute the difference `detected_fatigue_day − fatigue_day` for all creatives where both are non-null. Report the median and mean of this difference. A negative value indicates early detection (the system detected fatigue before the ground-truth label); a positive value indicates lag. The ideal headline is a median of −3 to −7 days (early warning advantage).

***

## 7. Layer 4 — CUSUM Statistic for Sustained Drift

### 7.1 Purpose

Layer 4 detects creatives that exhibit slow, persistent downward drift in CTR — a pattern that neither the first/last window (Layer 1) nor the linear regression (Layer 2) catches reliably. Layer 1 misses gradual declines because the final 7-day window is not much lower than the first 7-day window in absolute terms. Layer 2 may not reach statistical significance for a slow trend over 75 days if day-to-day variance is high. The CUSUM statistic accumulates small deviations from the mean and produces a large value when those deviations are consistently negative.

### 7.2 Algorithm: Lower-Tailed CUSUM

CUSUM (Cumulative Sum Control Chart) is a sequential analysis technique originally developed for quality control. The lower-tailed variant used here accumulates evidence of values falling below expectation. It requires no curve fitting, no hyperparameter optimisation beyond a single sensitivity constant `k`, and is straightforward to explain to non-technical users.

The algorithm operates on a standardised version of the creative's CTR time series and accumulates negative deviations. The maximum accumulated deviation over the series lifetime is the CUSUM score — higher values indicate a more severe and sustained decline.

### 7.3 Input

The global daily aggregated frame from Section 3. Required columns: `creative_id`, `days_since_launch`, `ctr` (raw derived CTR). Null CTR rows (from zero-impression days) should be excluded from CUSUM computation, not interpolated — CUSUM handles gaps natively by simply not accumulating on those days.

### 7.4 Computation Steps

**Step 1: Per-creative standardisation.**

For each `creative_id`, compute the mean and standard deviation of all non-null CTR values across the creative's full lifetime. If the standard deviation is effectively zero (less than 1×10⁻⁹), the creative's CTR is perfectly flat and CUSUM will return zero; set `cusum_score = 0.0` and skip further computation.

Standardise each non-null CTR value: subtract the mean and divide by the standard deviation. This produces a z-score series for the creative.

**Step 2: Accumulate lower CUSUM.**

Initialise an accumulator `S` at zero. For each standardised CTR value `z` in `days_since_launch` order, update the accumulator:

$$ S_{t} = \max(0,\; S_{t-1} - z_t - k) $$

where `k` is the sensitivity constant. The recommended value is `k = 0.5`, which corresponds to detecting shifts of approximately 1 standard deviation or more. A lower `k` makes the statistic more sensitive (catches smaller drifts but increases false positives). A higher `k` makes it less sensitive.

The subtraction of `z_t` (not its negation) means the accumulator grows when CTR falls below the mean (negative z-score), and resets toward zero when CTR is above the mean. The `max(0, ...)` wrapper prevents the accumulator from going negative, ensuring it always reflects accumulated downward pressure rather than accumulated recovery.

**Step 3: Record the maximum accumulated value.**

The `cusum_score` for this creative is the maximum value of `S` across all timesteps. A high maximum indicates a sustained and uninterrupted period of below-average CTR. A value of zero indicates the creative's CTR never drifted persistently below its own mean.

**Step 4: Normalise for composite input.**

Apply min-max normalisation across all creatives to bring `cusum_score` to a [1] scale. This normalisation must use the full creative population, not per-cohort subsets.

### 7.5 Output Columns

| Column | Type | Description |
|---|---|---|
| `creative_id` | key | Join key |
| `cusum_score_raw` | float ≥ 0 | Raw CUSUM maximum; higher = more sustained downward drift |
| `cusum_score` | float [1] | Min-max normalised for composite assembly |

### 7.6 Interpretability Note

For the UI, `cusum_score_raw` can be surfaced directly alongside a plain-language explanation: "This creative's CTR has been consistently below its own average for an extended period." This is meaningful to a non-technical marketer without requiring any understanding of the underlying statistics.

***

## 8. Composite Score Assembly

### 8.1 Formula

The composite fatigue score combines the outputs of Layers 1, 2, and 4. Layer 3 is excluded from this formula (it is a timing annotation only).

Before applying the formula, all three component scores must be on the [1] scale:

- **Layer 1:** Normalise `decay_ratio` using min-max across all creatives. Negative values (improving creatives) are clamped to 0 before normalisation.
- **Layer 2:** Use `l2_score` as computed in Section 5.3, Step 4, which is already normalised.
- **Layer 4:** Use `cusum_score` as computed in Section 7.4, Step 4, which is already normalised.

The composite formula with recommended weights:

$$ \text{fatigue\_score} = 0.40 \times \text{decay\_ratio\_norm} + 0.35 \times \text{l2\_score} + 0.25 \times \text{cusum\_score} $$

### 8.2 Classification Threshold

Apply a classification threshold of 0.50 to produce a binary `predicted_fatigued` flag. Creatives with `fatigue_score ≥ 0.50` are classified as fatigued; those below are classified as not fatigued.

This threshold should be reviewed during validation (Section 10). If precision is more important than recall (i.e., the product prefers not to flag a healthy creative incorrectly), raise the threshold. If recall is more important (the product must not miss a genuinely fatigued creative), lower it.

### 8.3 Weight Rationale

The 40/35/25 split reflects the following reasoning: Layer 1 carries the most weight because `first_7d_ctr` vs `last_7d_ctr` is a direct, high-confidence comparison that is available for every creative. Layer 2 carries the second-most weight because statistical significance filtering makes its contribution robust, but it requires ≥10 days of data to activate. Layer 4 carries the least weight because CUSUM is a cumulative statistic that grows monotonically — very long-running creatives will naturally accumulate higher CUSUM values regardless of the severity of decline. The weight difference compensates for this mild duration bias.

### 8.4 Output Columns

| Column | Type | Description |
|---|---|---|
| `creative_id` | key | Join key |
| `decay_ratio_norm` | float [1] | Normalised Layer 1 input |
| `l2_score` | float [1] | Layer 2 composite input (from Section 5) |
| `cusum_score` | float [1] | Layer 4 composite input (from Section 7) |
| `fatigue_score` | float [1] | Weighted composite; higher = more fatigued |
| `predicted_fatigued` | boolean | True if `fatigue_score ≥ 0.50` |
| `detected_fatigue_day` | integer or null | From Layer 3; timing annotation only |

***

## 9. Final Output Table Schema

The full output of the fatigue detection module is a single flat table joined to creative metadata. One row per creative. All columns from Section 8.4 plus the following enrichment columns joined from `creatives.csv` and `creative_summary.csv`:

| Column | Source | Role |
|---|---|---|
| `creative_id` | — | Primary key |
| `campaign_id` | `creatives.csv` | Within-campaign ranking context |
| `format` | `creatives.csv` | Format-level benchmarking |
| `vertical` | `creatives.csv` | Vertical-level benchmarking |
| `decay_ratio` | Layer 1 | Raw (un-normalised) for display |
| `decay_ratio_norm` | Composite | Normalised for score contribution |
| `slope` | Layer 2 | Raw slope for display |
| `slope_pval` | Layer 2 | P-value for transparency |
| `l2_sig_negative` | Layer 2 | Significant negative trend flag |
| `l2_score` | Composite | Layer 2 contribution to score |
| `cusum_score_raw` | Layer 4 | Raw CUSUM for display |
| `cusum_score` | Composite | Layer 4 contribution to score |
| `fatigue_score` | Composite | Final composite score |
| `predicted_fatigued` | Composite | Classification output |
| `detected_fatigue_day` | Layer 3 | Timing annotation |
| `creative_status` | `creative_summary.csv` | Ground truth — validation use only |
| `fatigue_day` | `creative_summary.csv` | Ground truth timing — validation use only |

***

## 10. Validation Requirements

Validation must be performed after the full pipeline is assembled and before any results are surfaced in the UI. The following checks are mandatory.

### 10.1 Binary Classification Metrics

Using `predicted_fatigued` as the prediction and `(creative_status == "fatigued")` as the ground truth binary label, compute and report:

- Confusion matrix (true positives, false positives, true negatives, false negatives)
- Precision, recall, F1 score
- The number of creatives flagged as predicted-fatigued that are not in the ground-truth fatigued set — these are additional candidates and should be inspected manually by checking their CTR curves

The target headline for the demo is a recall of at least 80% with a precision above 70%. If these targets are not met, adjust the composite weights or the classification threshold and re-run.

### 10.2 Layer Ablation

Run the composite score with each layer removed one at a time and compare F1 scores. This produces a table of the form:

| Configuration | F1 | Notes |
|---|---|---|
| L1 + L2 + L4 (full) | — | Baseline |
| L2 + L4 (no L1) | — | Tests L1 marginal contribution |
| L1 + L4 (no L2) | — | Tests L2 marginal contribution |
| L1 + L2 (no L4) | — | Tests L4 marginal contribution |

Include this table in the demo. It demonstrates that the approach was evaluated, not just assumed.

### 10.3 Timing Validation (Layer 3)

For all creatives where both `detected_fatigue_day` and ground-truth `fatigue_day` are non-null, compute:

- Mean detection lag: `detected_fatigue_day − fatigue_day` (negative = early)
- Median detection lag
- Percentage of detected fatigue days within ±7 days of the ground-truth label

Include the median early-warning lead in the demo narrative.

### 10.4 Cohort Sanity Checks

The following checks guard against the known dataset quirks:

- Confirm that CUSUM scores are not systematically higher for creatives with longer `days_active` after controlling for `predicted_fatigued`. If they are, reduce the CUSUM weight in the composite or apply a duration-adjustment normalisation.
- Confirm that Layer 2 recall is not systematically lower for creatives in `fintech` compared to `gaming`. Because gaming CTR is synthetically ~2× fintech CTR, the absolute slope magnitudes differ; the standardisation in CUSUM handles this, but the regression slope in Layer 2 does not. If a systematic vertical bias is found, consider running Layer 2 with within-vertical z-scored CTR rather than raw CTR.
- Confirm that Layer 1 does not return null `decay_ratio` for any creative. A null indicates that `first_7d_ctr` or `last_7d_ctr` is missing from `creative_summary.csv`, which should not occur in this dataset but should be handled defensively with a fallback of 0.0.

***

## 11. Integration and UI Guidance

### 11.1 Recommended Surface Points

The fatigue detection module produces data for the following UI sections. These are data contracts; visual design is left to the implementing team.

| UI Section | Data Required | Primary Column |
|---|---|---|
| Fatigue Leaderboard table | Full output table, sorted by `fatigue_score` descending | `fatigue_score`, `predicted_fatigued` |
| CTR Decay Curve chart | Daily aggregated frame (`ctr`, `ctr_7d`) per creative | `ctr`, `ctr_7d`, `days_since_launch` |
| Score Breakdown panel | Layer-level scores per creative | `decay_ratio_norm`, `l2_score`, `cusum_score` |
| Changepoint Annotation | `detected_fatigue_day` overlaid on CTR curve | `detected_fatigue_day` |
| Validation Panel | Confusion matrix from Section 10.1 | `predicted_fatigued`, `creative_status` |
| Cohort Benchmark | Median `fatigue_score` grouped by `format` and `vertical` | `fatigue_score`, `format`, `vertical` |

### 11.2 Display Rules

- `fatigue_day` from the ground-truth column should never be rendered as `NaN` in the UI; it is intentionally blank for non-fatigued creatives. Render it as a dash or "N/A" string.
- `detected_fatigue_day` may be null for creatives where the series is too short or no downward break was detected. Render these as "No structural break detected."
- Raw CUSUM scores (`cusum_score_raw`) are more intuitive for debugging but less useful for marketers. Surface `cusum_score` (normalised) in the user-facing UI and reserve `cusum_score_raw` for internal inspection or the validation panel.
- The composite `fatigue_score` should be rendered as a percentage (multiply by 100) in the marketer-facing UI.

### 11.3 Performance Expectations

The full pipeline (pre-processing + all four layers) should complete in under 60 seconds on a standard laptop using pandas. The most computationally intensive step is the per-creative loop in Layer 3 (PELT). If runtime exceeds 60 seconds, the PELT loop can be parallelised across creatives using Python's `multiprocessing.Pool` or `joblib.Parallel`.

***

## 12. Dependency Summary

| Library | Layer | Purpose |
|---|---|---|
| `pandas` | All | Data manipulation, groupby, rolling |
| `scipy.stats.linregress` | Layer 2 | OLS regression with p-value |
| `ruptures` | Layer 3 | PELT changepoint detection |
| `numpy` | Layer 4 | Sequential CUSUM accumulation |
| `sklearn.metrics` | Validation | Confusion matrix, precision, recall, F1 |

No other dependencies are required for this module. All libraries listed above are available in standard Python data science environments.

***

## 13. Open Questions for Engineer Review

The following items require a decision or empirical check during implementation:

1. **PELT penalty tuning:** The recommended penalty of 3 for Layer 3 is a starting point. During validation, check whether reducing it to 2 improves the timing median without introducing too many false changepoints on stable creatives.
2. **CUSUM duration bias:** Validate Section 10.4's cohort check. If longer-running creatives systematically outscore shorter ones regardless of actual CTigue, consider normalising `cusum_score_raw` by `days_active` before normalisation.
3. **Layer 2 vertical bias:** If fintech creatives show systematically lower Layer 2 recall, switch Layer 2 to use within-vertical z-scored CTR as the regression input rather than raw CTR.
4. **Threshold calibration:** The 0.50 composite threshold is a recommendation. After computing the full precision-recall curve on the ground-truth labels, the engineer should select the threshold that best matches the product's priorities (recall-oriented for "catch everything"; precision-oriented for "only flag certain cases").
5. **VTR as secondary signal:** Video Completion Rate (VTR) for rewarded_video and playable formats is computed during pre-processing but not included in the composite. If the validation shows weaker recall for those formats specifically, consider adding a format-conditioned VTR decay ratio as an additional Layer 1 signal for rewarded_video and playable creatives only.