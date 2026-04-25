# Smadex execution tracker (continuous)

## Current focus (first problem): Q1 health metric redesign
### Problem statement
Current health is a heuristic driven partly by synthetic labels (`creative_status`) and precomputed `perf_score`/`ctr_decay_pct`. We need an evidence-based health score that is statistically defensible, objective-aware, cohort-fair, and explainable to judges.

### Where the feature is currently implemented
- Core computation: `backend/app/datastore.py`
  - `_compute_health(...)`
  - `_band_from_health(...)`
  - `_compute_flat_rows(...)` (writes `health` and `status_band` onto API rows/details)
- API consumption/sorting:
  - `backend/app/services/queries.py` (`list_creatives_flat` sorts by `health` by default)
- Contract/schema:
  - `backend/app/schemas.py` (`CreativeRow.health`, `CreativeRow.status_band`, `CreativeDetail.health`, `CreativeDetail.status_band`)
- Frontend display only:
  - `frontend/src/lib/health.ts`
  - `frontend/src/components/design/HealthRing.tsx`
  - `frontend/src/components/design/BandPill.tsx`
  - `frontend/src/app/creatives/[creativeId]/page.tsx`
  - `frontend/src/components/design/CreativeRow.tsx`

### Proposed evidence-based health framework (review before ship)
Build health as a weighted composite of validated components:
1. **Performance strength** (posterior mean on selected objective: CTR/CVR/ROAS/IPM/CPA proxy)
2. **Uncertainty/confidence** (posterior interval width; penalize low evidence)
3. **Trend/fatigue pressure** (rolling-window slope + significance)
4. **Cohort-relative lift** (percentile/z-score within fair cohort)
5. **Efficiency** (revenue/spend and cost efficiency depending on objective)
6. **Scale/reliability guardrail** (impression/click/conversion volume reliability)
7. **Novelty/saturation pressure** (optional Q2b-linked penalty for creative crowding)

Health target remains 0-100, but each component is standardized, weighted, and auditable.

### Full candidate metric pool (for your double-check)
#### Primary outcome metrics
- CTR = clicks / impressions
- CVR = conversions / clicks
- IPM = impressions-normalized conversion metric (if used in brief)
- ROAS = revenue_usd / spend_usd
- CPA proxy = spend_usd / conversions (lower is better)
- Revenue per impression (RPI) = revenue_usd / impressions
- Spend efficiency = conversions / spend_usd

#### Bayesian/statistical reliability metrics
- Beta-binomial posterior mean CTR
- Beta-binomial posterior mean CVR
- Posterior 95% credible interval width (CTR/CVR)
- Probability(creative > cohort median) on chosen objective
- Probability(creative in top-k of cohort)
- Effective sample size (impressions/clicks/conversions)
- Empirical-Bayes shrinkage distance (raw vs shrunk)

#### Trend/fatigue metrics (Q2a-aligned inputs reused in Q1 health)
- 7-day vs first-7-day delta (absolute and %)
- Rolling-window slope (CTR/CVR)
- Exponential decay coefficient
- Monotonicity score (how consistently downward trend is)
- Change-point presence and post-change drop magnitude
- Significance of decline (proportion test / posterior probability of drop)
- Days since launch interaction with trend (early volatility guard)

#### Cohort fairness metrics
- Percentile rank within (vertical, format, country, OS)
- Z-score within cohort
- Within-campaign rank (1..6) and confidence
- Cross-cohort stability (variance of rank across segments)

#### Efficiency/business utility metrics
- Margin-style proxy: (revenue - spend) / spend
- Cost per click (CPC) and trend
- Cost per conversion proxy and trend
- Objective-aligned utility score (toggle-driven)

#### Exposure/risk metrics
- Impression concentration risk (single segment dependence)
- Country/OS robustness (performance spread across slices)
- Small-sample risk flag
- Volatility score (day-to-day variance)

#### Creative novelty/saturation metrics (optional for Q1, stronger in Q2b)
- Advertiser-level duplicate density in attribute space
- Cluster cannibalization risk (performance spread within cluster)
- Novelty score vs advertiser historical portfolio

### Recommended minimal-v1 score formula
For each creative c:
- `strength_c`: posterior mean on objective (0-1 scaled)
- `confidence_c`: 1 - normalized credible interval width
- `trend_c`: normalized signed trend (decline lowers score)
- `cohort_c`: normalized cohort percentile
- `efficiency_c`: normalized business efficiency metric
- `reliability_c`: sample-size reliability factor

`health_c = 100 * (w1*strength_c + w2*confidence_c + w3*trend_c + w4*cohort_c + w5*efficiency_c) * reliability_c`

Initial default weights to test:
- `w1=0.35, w2=0.15, w3=0.20, w4=0.20, w5=0.10`

### Validation plan (must pass before shipping)
1. Correlate health with `perf_score` on stable creatives only.
2. Check divergence cases (small sample, high variance) are explainable.
3. Measure confusion-style agreement for band mapping vs `creative_status` as validation only.
4. Run ablation: confirm Bayesian + cohort components improve ranking stability.
5. Produce per-creative score breakdown payload for UI explainability.

### Q1 planning todos (this sub-problem)
1. Freeze objective set and metric definitions.
2. Define normalization and cohort granularity.
3. Finalize Bayesian priors and posterior outputs returned by API.
4. Define v1 weight set + ablation grid.
5. Define band-threshold calibration method from score distribution.
6. Add explainability payload schema (component-level contributions).
7. Implement/ship only after your metric list sign-off.

## Problem and approach
We need to deliver a marketer-facing product that ships all 5 Smadex capabilities with an end-to-end loop: run campaign -> inspect performance/fatigue/similarity/explanations -> act (scale/pause/test) -> generate next variant or recommendation -> reiterate.

Approach: keep the current FastAPI + Next.js foundation, replace current stubs with statistically grounded modules from the challenge strategy, and wire a single three-tab flow that is demo-ready and measurable against ground-truth labels (`creative_status`, `fatigue_day`, `perf_score`) without using them as the answer.

## Current stage
**Stage:** Foundation complete, feature modules in progress.

### Progress made so far
1. Backend + frontend scaffolding is live (FastAPI app, Next.js app, dataset loading, static assets, hierarchy APIs).
2. Portfolio cockpit exists (`scale/watch/rescue/cut/explore`) with KPIs, filters, detail pages, and per-creative time series.
3. Twin and variant UX flow exists as a working stub path (`/creatives/[id]/twin` and `/variant`), including Gemma-powered Vision Insight fallback behavior.
4. Dataset gotchas are already documented in `resources/smadex/dataset_notes.md`, and strategy for all 5 capabilities is defined in `resources/taskInfo/strategy.md`.

### What is not complete yet
1. Q1 is still using synthetic labels/perf-based health logic; Bayesian shrinkage + cohort-adjusted ranking is not wired.
2. Q2a fatigue detection model and confusion-matrix validation are not implemented.
3. Q2b CLIP + HDBSCAN + UMAP clustering pipeline and cluster-performance panel are not implemented.
4. Q3a LightGBM + SHAP explainability is not implemented.
5. Q3b Thompson/UCB bandit recommendation engine and diversity-aware next-test ranking are not implemented.
6. End-to-end campaign feedback loop (actions + rerun + insight refresh + variant push) is not fully wired.

## Todo list (execution order)
1. **Align data/metrics contract**: define canonical feature tables and API payloads used by all five capabilities.
2. **Implement Q1 ranking**: beta-binomial Bayesian shrinkage + credible intervals + cohort-adjusted rankings + objective switch.
3. **Implement Q2a fatigue**: daily trend model + significance gating + fatigue flags + confusion matrix vs label.
4. **Implement Q2b similarity**: metadata features + CLIP embeddings + HDBSCAN/UMAP + blended clusters + cluster insights.
5. **Implement Q3a explainability**: LightGBM model + SHAP attribution endpoints + per-creative explanation payload.
6. **Implement Q3b recommendations**: attribute-cube bandit (Thompson/UCB), peer benchmark, diversity penalty, ranked actions.

### Simple explanation for the new health score
Think of the new health score as a balanced report card rather than a raw popularity contest. Instead of just looking at whether an ad gets clicks, we evaluate it across five fair dimensions.

First, we measure its actual performance and how confident we are in that data, so new ads are not unfairly penalized for having low traffic. Second, we compare the ad only to similar peers (its cohort), ensuring we do not compare a cheap banner ad to an expensive video. Finally, we check if the ad is fatigue-dropping over time (but only after its first week) and whether it is cost-efficient. We combine these into a 0-100 score, giving the user a transparent and mathematically fair view of when to scale an ad or cut it.

### Revised health formula
The core formula uses an additive reliability bonus and a time-gated trend penalty to prevent early-lifecycle ads from collapsing in score. The weights must sum to `1.0`.

`health_c = 100 * (w1*S + w2*C + w3*1[age >= 7]*T + w4*R + w5*E + w6*B)`

The weights `(w1...w6)` will be calibrated via an ablation study against stable creatives, starting with a baseline hypothesis of:
- `w1=0.30` for strength
- `w2=0.15` for confidence
- `w3=0.15` for trend
- `w4=0.20` for cohort rank
- `w5=0.10` for efficiency
- `w6=0.10` for reliability bonus

### Component definitions
Each variable in the formula addresses a specific business or statistical requirement. The metrics are dynamically swapped based on the user's selected objective (e.g., CTR vs CVR).

- **Strength (`S`)**: The posterior mean of the chosen objective, scaled 0-1.
- **Confidence (`C`)**: `1 - normalized credible interval width`.
- **Trend (`T`)**: The normalized slope of performance, applied only if the creative is older than 7 days (`1[age >= 7]`).
- **Cohort Rank (`R`)**: The percentile rank within its cohort. If the 4-way cohort `(vertical, format, country, OS)` has fewer than 5 creatives, it falls back to a 2-way cohort `(vertical, format)`.
- **Efficiency (`E`)**: The normalized business metric, such as ROAS or inverse CPA.
- **Reliability Bonus (`B`)**: A small additive reward for high effective sample sizes, replacing the previous multiplicative penalty.

### Validation steps
Before deploying this to the frontend UI, the backend must pass three statistical checks to ensure the metric behaves logically. These steps prevent shipping a degenerate score distribution.

1. **Ablation study**: Compare the ranking stability of the new score versus the raw performance score on creatives with over 30 days of data.
2. **Distribution check**: Generate a histogram of the final 0-100 scores across the dataset to confirm a roughly normal or uniform spread, ensuring scores do not cluster entirely at 0 or 100.
3. **Sanity check**: Map the new scores to bands (e.g., `>80` is Scale, `<40` is Cut) and run a confusion matrix against the synthetic `creative_status` to ensure major divergences are explainable.
7. **Wire campaign feedback loop**: from insight to action (scale/pause/test/generate variant) and track next-iteration outcomes.
8. **Integrate final 3-tab UX**: Explorer, Fatigue+Clusters, Explain+Recommend with consistent filters and state.
9. **Validation/demo hardening**: baseline comparisons, metrics callouts, and stable demo path with fallback.

## Notes
- Ground-truth columns are for validation only, never direct outputs.
- Keep three-tab flow only; avoid scope creep.
- Update this file continuously at each major milestone.
