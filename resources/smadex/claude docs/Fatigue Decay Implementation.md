# Fatigue Decay Implementation

## Steps

### Phase 1: Data Pre-Processing & Aggregation

- Read daily time-series data.
- Group by `creative_id` and `date`.
- Sum all metrics:
	- `impressions`
	- `clicks`
	- `conversions`
	- `spend_usd`
	- `revenue_usd`
	- `video_completions`
- Get the minimum `days_since_launch`.
- Derive base logic and compute:
	- `ctr`
	- `cvr`
	- `roas`
	- `vtr`
- Handle division-by-zero bounds:
	- Use denominator floor `1` for impression-based metrics.
	- Use denominator floor `0.01` for spend-based metrics.
- Sort the DataFrame by:
	1. `creative_id` (ascending)
	2. `days_since_launch` (ascending)
- Keep zero-impression rows where spend is null CTR.

### Phase 2: Layer 1 (First/Last Window Decay Ratio)

- Read summary data for `first_7d_ctr` and `last_7d_ctr`.
- Compute:

	`decay_ratio = (first_7d_ctr - last_7d_ctr) / max(first_7d_ctr, 1e-6)`

- Clamp `decay_ratio` to `[-1.0, 1.0]`.
- Apply target min-max normalization.
- Output boolean `l1_flag` where:

	`l1_flag = decay_ratio > 0.25`

### Phase 3: Layer 2 (Rolling Window Linear Trend)

- Compute 7-day trailing rolling mean `ctr_7d` per creative using `min_periods=3` (depends on Phase 1).
- For each `creative_id` with `>= 10` valid `ctr_7d` rows, run OLS linear regression on `days_since_launch`.
- Extract:
	- trend slope
	- two-tailed p-value
- Flag `l2_sig_negative` when:

	`slope < 0 and p_value < 0.05`

- Min-max normalize absolute significant slopes into `l2_score` across the global population.

### Phase 4: Layer 3 (Changepoint Detection - PELT)

- Interpolate null CTR values.
- For series with `>= 14` observations, run the PELT algorithm with RBF cost (`penalty = 3`).
- Filter structural breaks by verifying:

	`post_break_mean_ctr < pre_break_mean_ctr`

- Output:
	- first downward break index
	- mapped `detected_fatigue_day`
- Note: this layer is strictly for timeline annotation.

### Phase 5: Layer 4 (CUSUM Statistic)

- Standardize (z-score) the raw non-null CTR series per creative.
- Accumulate downward drift CUSUM iteratively:

	`S_t = max(0, S_{t-1} - z_t - k)`, initialized with `k = 0.5`

- Output:
	- max CUSUM value across series as `cusum_score_raw`
	- min-max normalized population score as `cusum_score`

### Phase 6: Composite Assembly & Output

- Join Layer 1, 2, 3, and 4 outputs per creative.
- Compute composite score:

	`composite_score = 0.40 * L1_norm + 0.35 * L2_norm + 0.25 * L4_norm`

- Classify:

	`predicted_fatigued = (composite_score >= 0.50)`

## Relevant Files

- New Python service file: `fatigue.py` — core logic mapped to phases.
- New Python router: `creatives.py` — output mapping and web exposure.
- Target documentation:
	[`resources/smadex/claude docs/fatigue_implementation_plan.md`](resources/smadex/claude docs/fatigue_implementation_plan.md) — destination file for the plan.

## Verification

- Execute validation script comparing `predicted_fatigued` vs ground-truth labels (`creative_status == "fatigued"`).
	- Target: **Recall > 80%**, **Precision > 70%**.
- Build layer ablation table (`L1+L2`, `L2+L4`, etc.) to evaluate marginal model contributions to F1 score.
- Validate timing annotations:
	- Verify median detection lag (`detected_fatigue_day - ground-truth fatigue_day`) delivers a **-3 to -7 day** early warning advantage.