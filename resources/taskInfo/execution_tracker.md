# Smadex execution tracker (continuous)

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
7. **Wire campaign feedback loop**: from insight to action (scale/pause/test/generate variant) and track next-iteration outcomes.
8. **Integrate final 3-tab UX**: Explorer, Fatigue+Clusters, Explain+Recommend with consistent filters and state.
9. **Validation/demo hardening**: baseline comparisons, metrics callouts, and stable demo path with fallback.

## Notes
- Ground-truth columns are for validation only, never direct outputs.
- Keep three-tab flow only; avoid scope creep.
- Update this file continuously at each major milestone.
