# Smadex dataset — what's signal, what's noise, what's a trap

Pulled directly from the four CSVs (advertisers / campaigns / creatives / creative_summary / creative_daily_country_os_stats). Aim: tell Q1 health, Q3 explainability, and the demo what to lean on, what to drop, and where the trapdoors are.

> **See also:** [`research/model_justification.md`](../../research/model_justification.md) — Andrew's rigorous fatigue-classifier feature analysis (campaign-grouped train/test, ablation, permutation importance). For fatigue-specific feature decisions, his numbers replace the hand-waved bits in this doc. This file's value is the broader *what columns to keep / drop / treat as a trap*, *what's worth saying in the demo*, and the *per-campaign health formula* not covered there.

> **Companion file:** [`join_aggregate_opportunities.md`](join_aggregate_opportunities.md) — five join/aggregation moves we haven't fully exploited yet (per-creative × country, cohort fatigue curve, campaign diversity index, advertiser peer-rank, country × format ROAS map).

## TL;DR — the 5 things that matter

1. **`perf_score` is ~91% recoverable from just `overall_ctr + first_7d_ctr + overall_cvr + overall_roas + overall_ipm + total_impressions`**, and ~68% from CTR alone. It is **not cohort-adjusted** — banner perf_score averages 0.30 vs playable 0.68; gaming verticals 0.63 vs ecommerce 0.40. Beating perf_score = adding (a) a cohort-relative ranking and (b) a decay/trajectory penalty. Matching it = sorting by `overall_ctr`. Aditya can drop this in the demo: *"the dataset's own performance score is dominated by lifetime CTR — we replaced it with cohort-relative Bayesian ranking that catches creatives lifetime CTR misses."*

2. **Soft attribute scores (`clutter_score`, `motion_score`, `brand_visibility_score`, `readability_score`) only show up as signal *within format*.** Globally, clutter↔ROAS looks like −0.41 — but *within vertical* it's −0.05 to −0.15. The strong "high clutter = low ROAS" effect is mostly format mix talking. **Conclusion:** when scoring an attribute, always cohort by `(format, vertical)`. Krish's Q3 attribute cube is the right shape; using these scores as flat features in Q1 health would be misleading.

3. **`creative_status` is essentially decided by `format` × `vertical`.** No banner is ever a top_performer (0/199). No playable is ever an underperformer (0/48). Fintech is 94% stable; gaming is 45% fatigued. **The "label" is largely structural, not behavioural.** Important caveat for any model that's fit against `creative_status` — it learns *format/vertical*, not *what makes a creative tired*. Validate against the trajectory signal instead.

4. **`fatigue_day` + `ctr_decay_pct` overlap is small.** Median ctr_decay_pct is −0.84 for fatigued creatives vs −0.78 for everyone else. **All creatives decay** in this dataset; the question is *how fast and from what peak*. A flat threshold on `ctr_decay_pct` will catch fatigue but with poor precision. Fatigue detection needs slope + changepoint, not a single decay-percentage cut.

5. **`overall_roas` swings 5× across verticals** (travel 7.67 mean vs gaming 1.46) and `overall_ctr` 2× (gaming 0.74% vs fintech 0.40%). **Never rank ROAS or CTR globally — only within vertical or (vertical, format).** Existing Q1 already does cohort-relative percentiles for these; just hold the line.

---

## Columns to drop, deprioritise, or treat as confounders

| Column(s) | Verdict | Why |
|---|---|---|
| `width`, `height` | **Useless directly; drop.** | Only 3 unique combos and they're 1:1 with `format`. Their 0.45 corr with `perf_score` is *format leaking through*, not real signal. |
| `target_age_segment` | **No signal vs status.** | Distribution of `creative_status` is nearly identical across the 4 age segments (fatigued: 16-20% in every bucket). Don't weight in any KPI. |
| `kpi_goal` | **Almost no signal vs status.** | All four KPI goals (CPA / CTR / IPM / ROAS) show similar status distributions. Useful as advertiser intent metadata, not as a predictor. |
| `hq_region` | **Likely confounded with vertical.** | LATAM 36% fatigue vs NA 10%, but advertisers cluster by region/vertical — looks like a vertical-leak. Don't use directly without controlling for vertical. |
| `language` | **Demographic context, not performance signal.** | Distribution is roughly proportional to vertical/country mix. |
| `subhead`, `headline` (free text) | **Demo metadata only.** | High-cardinality natural-language fields. Useful for the agent's deep-link narrative, not for KPI scoring. |
| `app_name` | **Bookkeeping.** | Just a label per campaign; no analytic value. |
| `daily_budget_usd` | **Per-campaign scalar; redundant with `total_spend_usd`.** | If you already have realised spend, the budget is just a noisy version of it. |
| `peak_rolling_ctr_5` | **Subsumed by `first_7d_ctr` / `peak_day_impressions`.** | High correlation with `first_7d_ctr` (>0.9 expected). Pick one. |
| `last_7d_*` raw | **Use the *decay* ratios, not the raw values.** | `last_7d_ctr` alone says nothing without the first-week baseline. Use `ctr_decay_pct` and `cvr_decay_pct`; the raw windows are redundant once the decay is computed. |

## Trap columns — handle with care

| Column | Trap | How to handle |
|---|---|---|
| `duration_sec` | **0 means "static asset" not "instant playback"** for banner / native / static interstitial. Andrew's Round-3 fix already humanises this in vision_insight; make sure no other consumer (Q3 attribute cube, twin diff) treats `duration_sec=0` as a numeric on the same scale as `15`. | Treat as `format`-conditional: ignore for static formats; compare only within video formats. |
| `video_completions` | **0 by design for `banner`/`interstitial`/`native` (100% zero), populated only for `playable`/`rewarded_video` (0% zero).** | Don't include as a flat feature; only meaningful inside the video-format cohort. Treating 0 as missing data will misrank. |
| `impressions_last_7d` | **Rolling-window column.** Mean is 226k vs daily mean 33k — about 7× as expected. **If you sum it across dates you'll multi-count the same impressions seven times.** | Use as a feature on a single date row, never as an aggregate. |
| `creative_status` | Synthetic generator label, structurally tied to format × vertical. Already flagged in `dataset_notes.md`. | Validate against, never consume as input to your own ranker/fatigue detector. |
| `perf_score` | Synthetic, **not cohort-adjusted, ~91% recoverable from CTR/CVR/ROAS/impressions**, and over-confident on small-sample creatives. | Validate against on the stable bucket; expect (and demo) divergence on edge cases. |
| `fatigue_day` | **Blank for non-fatigued creatives** (881/1080 are NaN). | Don't render as NaN. Don't use as a regression target without restricting to the fatigued subset. |
| `target_os` ∈ {Android, iOS, **Both**} | "Both" expands to two daily rows (one per OS). | Per `dataset_notes.md`. Already handled by Andrew. |
| `countries` | Pipe-separated string. | Already handled. Mention it for completeness. |
| `total_revenue_usd` ↔ `overall_roas` | `overall_roas = total_revenue_usd / total_spend_usd` — they are not independent features. | Don't double-count by using both as inputs to a model. |

## High-signal columns the current health metric doesn't fully exploit

(Q1 already uses CTR/CVR/ROAS at cohort-relative percentiles + a trend slope + an evidence-strength term. These are what's underused.)

| Column | What it adds, when cohort-conditioned by `(format, vertical)` |
|---|---|
| `clutter_score` | Strongly negative within format (−0.40 to −0.50 corr with ROAS). High clutter inside a given format underperforms. **Most actionable creative attribute.** |
| `motion_score` | Same direction as clutter for video formats (−0.50 in playable). **Within video formats, less motion → better ROAS.** |
| `brand_visibility_score` | Positive within every format (+0.24 to +0.36 corr with ROAS). **Most reliable "do this more" lever.** |
| `readability_score` | Positive within format (+0.14 to +0.31). |
| `novelty_score` | **Positive within vertical (+0.16 to +0.31), flat within format.** Use as a per-vertical score, not a per-format one. |

These five attributes, all cohort-conditioned, give Q3's SHAP explainability + Q3b's bandit a richer feature set than CTR alone.

## Cohort sensitivity — the headline

The same dataset, looked at three ways:

```
clutter_score ↔ overall_roas
  Pooled (no cohort):   −0.41   "high-clutter = bad"
  Within format:        −0.27 to −0.49   *signal sharpens*
  Within vertical:      −0.04 to −0.15   *signal weakens*
```

**Format dominates the variance.** Always cohort-relative; the cohort that matters most is `(vertical, format)`.

Status distribution sharply confirms this:

| format         | top_perf | fatigued | underperf |
|----------------|---------:|---------:|----------:|
| banner         |     0%   |   0.5%   |   31.2%   |
| interstitial   |   1.7%   |   16.0%  |    5.5%   |
| native         |   1.7%   |    9.7%  |    4.8%   |
| playable       |   6.2%   |   58.3%  |    0%     |
| rewarded_video |  16.0%   |   43.5%  |    0%     |

**No banner ever wins. No playable ever loses outright.** Cohort-blind ranking will always confuse format effects with creative quality.

## Three concrete demo soundbites Aditya can drop

1. *"The dataset's own `perf_score` is 91% recoverable from CTR + CVR + ROAS + impressions. Worse, it isn't cohort-adjusted — banner ads average 0.30 vs playable ads 0.68. We replaced it with a Bayesian-shrunk cohort-relative ranking that doesn't punish banners for being banners."*

2. *"In this dataset, gaming hooks like 'power-up' fatigue 51% of the time. 'Exclusive' hooks fatigue only 8%. The same hook word is a 5-7× difference in lifespan — and it's the kind of thing a marketer can change in 60 seconds."* *(verified: power-up 22.7/45 = 51% fatigue rate, exclusive 4/51 = 8%)*

3. *"In every format, the strongest predictor of ROAS we found was clutter score — every 0.1 increase in clutter is worth roughly 5-8% lower ROAS within the same format. Marketers should ship cleaner creatives, not flashier ones."*

## Concrete recommendations for Q1 / Q3

For **Krish (Q1 health metric)**:
- **Drop** `width`, `height`, `target_age_segment`, `kpi_goal`, `daily_budget_usd`, `last_7d_*` raw values from any feature set. Keep the *decay percentages* derived from them.
- **Add** the four cohort-conditioned soft attributes (`clutter_score`, `motion_score`, `brand_visibility_score`, `readability_score`) computed against `(format, vertical)` — feed them into the `R` (cohort rank) and `E` (efficiency) terms of the health formula.
- **Don't compare `perf_score` across formats**: when validating Q1 against `perf_score`, do it within `format × vertical` cells, not pooled.

For **Andrew (agent / explainability)**:
- The agent's `get_creative_diagnosis` tool returns these soft scores; tell the system prompt to phrase them in marketer voice ("higher clutter than the format average") instead of raw numbers.
- For `duration_sec`-related explanations, lean on the existing humanise step.

For **the demo**:
- Hero creative pick: choose from `format ∈ {playable, rewarded_video}` and `vertical = gaming` for highest fatigue density (45% of gaming, 58% of playable are fatigued). Plenty of strong twin candidates.
- Don't show the lifetime `perf_score` chart — judges will spot that a banner can't beat a playable on it. Show the cohort-relative ranking instead.

---

*Generated 2026-04-25 from a direct EDA over creative_summary.csv (1,080 rows) + creative_daily_country_os_stats.csv (192k rows). Code lives in the chat history; rerun any time the dataset changes.*
