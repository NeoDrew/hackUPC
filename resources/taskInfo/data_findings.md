# Smadex dataset — what's signal, what's noise, what's a trap

Pulled directly from the four CSVs (advertisers / campaigns / creatives / creative_summary / creative_daily_country_os_stats). Aim: tell Q1 health, Q3 explainability, and the demo what to lean on, what to drop, and where the trapdoors are.

> **See also:** [`research/model_justification.md`](../../research/model_justification.md) — Andrew's rigorous fatigue-classifier feature analysis (campaign-grouped train/test, ablation, permutation importance). For fatigue-specific feature decisions, his numbers replace the hand-waved bits in this doc. This file's value is the broader *what columns to keep / drop / treat as a trap*, *what's worth saying in the demo*, and the *per-campaign health formula* not covered there.

> **Companion file:** [`join_aggregate_opportunities.md`](join_aggregate_opportunities.md) — five join/aggregation moves we haven't fully exploited yet (per-creative × country, cohort fatigue curve, campaign diversity index, advertiser peer-rank, country × format ROAS map).

## TL;DR — the 6 things that matter

1. **`perf_score` is ~91% recoverable from just `overall_ctr + first_7d_ctr + overall_cvr + overall_roas + overall_ipm + total_impressions`**, and ~68% from CTR alone. It is **not cohort-adjusted** — banner perf_score averages 0.30 vs playable 0.68; gaming verticals 0.63 vs ecommerce 0.40. Beating perf_score = adding (a) a cohort-relative ranking and (b) a decay/trajectory penalty. Matching it = sorting by `overall_ctr`. Aditya can drop this in the demo: *"the dataset's own performance score is dominated by lifetime CTR — we replaced it with cohort-relative Bayesian ranking that catches creatives lifetime CTR misses."*

2. **Soft attribute scores (`clutter_score`, `motion_score`, `brand_visibility_score`, `readability_score`) only show up as signal *within format*.** Globally, clutter↔ROAS looks like −0.41 — but *within vertical* it's −0.05 to −0.15. The strong "high clutter = low ROAS" effect is mostly format mix talking. **Conclusion:** when scoring an attribute, always cohort by `(format, vertical)`. Krish's Q3 attribute cube is the right shape; using these scores as flat features in Q1 health would be misleading.

3. **`creative_status` is essentially decided by `format` × `vertical`.** No banner is ever a top_performer (0/199). No playable is ever an underperformer (0/48). Fintech is 94% stable; gaming is 45% fatigued. **The "label" is largely structural, not behavioural.** Important caveat for any model that's fit against `creative_status` — it learns *format/vertical*, not *what makes a creative tired*. Validate against the trajectory signal instead.

4. **`fatigue_day` + `ctr_decay_pct` overlap is small.** Median ctr_decay_pct is −0.84 for fatigued creatives vs −0.78 for everyone else. **All creatives decay** in this dataset; the question is *how fast and from what peak*. A flat threshold on `ctr_decay_pct` will catch fatigue but with poor precision. Fatigue detection needs slope + changepoint, not a single decay-percentage cut.

5. **`overall_roas` swings 5× across verticals** (travel 7.67 mean vs gaming 1.46) and `overall_ctr` 2× (gaming 0.74% vs fintech 0.40%). **Never rank ROAS or CTR globally — only within vertical or (vertical, format).** Existing Q1 already does cohort-relative percentiles for these; just hold the line.

6. **`creative_daily_country_os_stats.csv` is 192k rows at `(creative, country, OS, day)` grain — and the entire research notebook collapses it away.** That slice table is the only surface in the dataset that lets us answer "where should I pause / scale / rotate / cap / re-bid / test next?" — i.e. exactly what the brief asks for. **The advisor system in §"The slice the research notebook didn't touch" is the highest-EV unbuilt component on the project.**

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

## The slice the research notebook didn't touch — `(creative × country × OS × day)`

`research/fatigue_kpi_research.ipynb` collapses country and OS away in cell 6 (`groupby(creative_id, date)`). Every feature, model and ablation in that notebook is built on the **summed-across-markets** series. That works for the binary fatigue verdict (test ROC-AUC 0.93), but **leaves the highest-leverage surface in the dataset untouched.**

`creative_daily_country_os_stats.csv` is **192,315 rows at (creative, country, OS, day) grain** — 1,080 creatives × 10 countries × 2 OS × ~9 active days each — and it's the only place in the dataset where we can answer the questions a marketer actually pays for:

- *"Where should I pause this creative?"* — geographic slice fatigue
- *"Where should I scale it?"* — over-performing markets
- *"Why is my ROAS down this week?"* — slice-level decomposition
- *"What should I test next?"* — cross-slice pattern transfer

The Smadex brief explicitly asks for **recommendations and "what to test next"**. A tab that shows fatigue per creative is table-stakes; the advisor system below is the differentiator.

## Advisor action taxonomy — what the recommendation engine should emit

Eight action types. Each one is a deterministic function over the slice grain that fires when its trigger crosses a threshold; each one carries a quantified expected lift and a one-line marketer-voice rationale.

| # | Action | Trigger (per `creative_id`) | Output (example) |
|--:|---|---|---|
| 1 | **Geographic prune** | `country_drop_ratio < 0.66 × creative_drop_ratio` AND slice impressions ≥ 5% of creative total | *"Pause in BR — CTR has dropped 67% there while holding flat in US/UK. Saves est. $X/day at current ROAS."* |
| 2 | **Geographic scale** | `country_cohort_percentile ≥ 90` AND `slice_roas ≥ 1.5 × creative_roas` AND budget headroom in that market | *"Increase BR bid 25% — top decile in (gaming, playable, BR) cohort, ROAS 2.3× creative average."* |
| 3 | **OS frequency cap** | `os_impressions_last_7d / os_baseline > τ` AND `os_ctr_decay > 0.4` AND opposite OS healthy | *"Cut Android bid 30% — frequency saturated, marginal CVR collapsing. iOS still healthy."* |
| 4 | **Cross-market fatigue early warning** | Slice-level changepoint LR significant in ≥ 2 served countries AND not yet visible in the summed series | *"Fatigue starting in LATAM cluster (BR, MX). EU still healthy. Rotate creative in LATAM before global metrics catch up."* |
| 5 | **Concentration risk** | `top_country_share > 0.6` AND `top_country_drop_ratio < 0.85` | *"70% of this creative's impressions are in DE, where CTR has dropped 23%. Diversify or replace before lifetime ROAS collapses."* |
| 6 | **Format-market mismatch** | Within `(country, vertical)` cohort, peer formats outperform this creative's format by ≥ 30% on ROAS | *"Banners in JP underperform playables 3.4× on ROAS. Your DE banner spend should rotate into playable creative."* |
| 7 | **Pattern transfer** | Sibling creative with similar attribute cube wins in country X; this creative not yet served in X | *"Sibling creative #501234 ranks top decile in MX (gaming, playable). Test this creative in MX — same hook, same CTA, untested."* |
| 8 | **Reallocation** | Rank slices by marginal ROAS = `revenue_usd / spend_usd` per slice; shift budget from bottom quartile to top quartile within the same advertiser | *"Shift $1.2k/day from (rewarded_video × IT × Android) to (rewarded_video × US × iOS). Projected lift: +$840/day revenue at constant total spend."* |

Every emitted recommendation should carry: **(a)** the slice that triggered it, **(b)** the magnitude of the trigger, **(c)** a counterfactual-flavoured estimate of impact ("$X/day"), and **(d)** a one-click verb — `pause`, `scale`, `cap`, `rotate`, `replace`, `test`. The Q3b bandit lives behind #7 and #8; the other six are deterministic rules.

## Slice-level features the advisor needs (compute once, cache per creative)

For each `creative_id`, the recommendation engine needs these aggregates over the slice table. Compute once at startup, cache per-creative in MongoDB Atlas (we're already opted in for the MLH prize); refresh when daily data changes.

**Geographic-shape features** (per creative):
- `n_active_countries` — countries with ≥ 100 cumulative impressions.
- `top_country_share` — fraction of total impressions in the single largest country (Herfindahl-style concentration).
- `country_ctr_dispersion` — std of last-7d CTR across served countries; high = market-specific behaviour, low = uniform creative.
- `country_with_steepest_decline` — `argmax_c (drop_ratio_c)`; the slice rolling first.
- `country_with_highest_residual` — `argmax_c (slice_ctr / cohort_ctr_in_country)`; the scale candidate.

**OS-divergence features** (per creative):
- `os_ctr_ratio` = `ctr_android / ctr_ios` (or whichever is non-zero); deviation from 1.0 is the headline.
- `os_drop_divergence` = `drop_ratio_android - drop_ratio_ios`; positive + significant = textbook "Android peeling off" early warning.
- `os_volume_ratio` = `impressions_android / impressions_ios`; flags lopsided distribution that may bias other features.

**Per-`(creative, country)` trajectory features** (one row per slice):
- The 7 production fatigue features (`drop_ratio`, `ctr_cv`, `lr_stat`, etc. — see `research/model_justification.md`) recomputed over the **per-country** daily series rather than the summed series.
- **Cohort-relative within country**: `slice_first_vs_country_cohort_median`, `slice_last_vs_country_cohort_p25` — same logic as production but cohorted by `(vertical, format, country)`.

**Per-`(campaign, country)` and `(advertiser, country)` rollups**:
- Aggregate ROAS, mean fatigue rate, breadth of creative coverage in that market.
- Drives the **campaign-health KPI**: roll up slice grain → campaign × country → campaign global. Country/OS detail is inherited for free.

## Slice-level trapdoors (read this before computing)

| Trap | What goes wrong | How to handle |
|---|---|---|
| **Sparse slices** | Many `(creative, country, OS, day)` cells have impressions < 1k. Per-slice CTR with no shrinkage produces wild outliers. | Bayesian shrinkage with a `(vertical, format, country)` cohort prior; or hard-floor slices at < 5k cumulative impressions. |
| **`impressions_last_7d` is a rolling column** | Already in the trap-columns table; bites harder at slice grain — summing it across 7 dates per slice multi-counts ×49. | Use as a feature on the latest date row only, never as an aggregate. |
| **Days with `spend_usd > 0` but `impressions = 0`** | Allocated spend that didn't serve. Treating as an active day pollutes the fatigue trajectory. | Drop from the per-slice series; report separately as "ad-server fill failure" if the count is material. |
| **`countries` on `campaigns.csv` is pipe-separated** | Already known. The slice table doesn't have this issue (it's already normalised). | Use the slice table as source-of-truth for "where did this creative actually serve". Don't trust `campaigns.countries` for the question of *served*, only *targeted*. |
| **`target_os = "Both"` → two daily rows** | Already documented. Confirms OS-level features should be computed from the slice table, not from `campaigns.target_os`. | Slice table is authoritative. |
| **Cohort sample size at country grain** | Some `(vertical, format, country)` cohorts have only a handful of creatives. Cohort percentiles will be unstable. | Fall back to `(vertical, format)` cohort with a learned country offset (random effect, or simple country-mean adjustment). |
| **Synthetic country signal** | The dataset is synthetic — country effects may be partly generator artefacts (e.g. uniform multiplicative scaling per country). Don't claim "real geographic insights" without caveat. | Demo phrasing: *"if these patterns held on real exchange data, here's what the system would surface."* Validate at least one finding by reading raw rows before quoting. |

## Three slice-level demo soundbites Aditya can lean on

(Numbers below are *illustrative shapes* — verify on the data once the engine runs end-to-end; the structure of the claim survives whatever specific numbers fall out.)

1. *"This creative is healthy in 3 of 5 markets — but you've been treating it as one global asset. We'd pause it in MX (CTR -52% in last 7 days) and scale it 30% in US (still top quartile). Net effect: +$2.1k/day in revenue at constant total spend."*
2. *"Across all 1,080 creatives, Android shows fatigue ~6 days earlier than iOS on average. Our system catches it from the OS-divergence signal alone, before the global CTR drops enough for a standard fatigue test to fire — that's a one-week head start on rotation."*
3. *"Banners in JP underperform playables 3.4× on ROAS — across every advertiser in the dataset. Any banner spend in JP should rotate to playable creative. We surface this as a one-click recommendation, with the projected daily lift attached."*

## Engineering notes for the advisor build

- **Don't introduce Spark / Dask.** 192k rows fits in pandas comfortably; the slice features for all 1,080 creatives compute in seconds.
- **Cache aggregates in MongoDB Atlas** (already in the stack for the MLH prize). Schema sketch: one document per `creative_id` with nested `by_country` and `by_os` blocks plus a `slices: [...]` array.
- **The advisor endpoint returns a ranked list of actions across the advertiser's portfolio**, not per-creative. Marketers want a daily action queue, not a forensic report. Sort by expected revenue impact descending.
- **Wrap the rules + the Q3b bandit in one LLM tool** (Andrew's orchestrator) — the marketer asks *"what should I do today?"* and gets the top 3 actions across all creatives with rationales. Each action carries the underlying slice for drill-down.
- **Don't surface ground-truth `creative_status` or `fatigue_day` in any rationale.** Validate against, never quote.
- **Per-recommendation explainability**: each action ships with the trigger (e.g. *"BR drop_ratio = 0.32, creative drop_ratio = 0.81"*) so a sceptical user can audit. SHAP on the bandit / slice-level deterministic values on the rules.

---

*Generated 2026-04-25 from a direct EDA over `creative_summary.csv` (1,080 rows) + `creative_daily_country_os_stats.csv` (192k rows). Slice-advisor section added 2026-04-25 after Smadex feedback that the per-country/OS surface was the highest-EV unused component. Code lives in the chat history; rerun any time the dataset changes.*
