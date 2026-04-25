# Q1 implementation spec: evidence-based health metric

## Readiness
**Status: implementation-ready as a baseline spec.**  
This document is suitable for another engineer to implement Q1 health scoring directly.

## Simple explanation
Think of the new health score as a balanced report card rather than a raw popularity contest. Instead of only looking at clicks, we evaluate each creative across fair dimensions.

We measure actual performance and confidence in that estimate so low-traffic/new creatives are not unfairly punished. We compare creatives only against similar peers (cohorts), avoiding unfair cross-format comparisons. We also evaluate time-based fatigue only after week one and include cost efficiency. The final score is a transparent 0-100 value used to decide scale/watch/rescue/cut.

## Revised health formula
Weights must sum to `1.0`.

`health_c = 100 * (w1*S + w2*C + w3*I(age_days >= 7)*T + w4*R + w5*E + w6*B)`

Initial baseline weights for ablation:
- `w1=0.30` (strength)
- `w2=0.15` (confidence)
- `w3=0.15` (trend)
- `w4=0.20` (cohort rank)
- `w5=0.10` (efficiency)
- `w6=0.10` (reliability bonus)

## Component definitions
- **Strength (`S`)**: posterior mean of selected objective, normalized to `[0,1]`.
- **Confidence (`C`)**: `1 - normalized_credible_interval_width`.
- **Trend (`T`)**: normalized signed slope of selected objective over recent windows; only active when `age_days >= 7`.
- **Cohort rank (`R`)**: percentile rank within cohort.
  - Primary cohort: `(vertical, format, country, os)`
  - Fallback if cohort size `< 5`: `(vertical, format)`
- **Efficiency (`E`)**: normalized business efficiency signal (objective-aware, e.g., ROAS or inverse CPA).
- **Reliability bonus (`B`)**: additive `[0,1]` bonus from effective sample size, replacing prior multiplicative penalty.

## Objective mapping
The same framework is objective-driven:
- CTR mode -> posterior CTR in `S`, CTR trend in `T`.
- CVR mode -> posterior CVR in `S`, CVR trend in `T`.
- ROAS mode -> normalized ROAS in `S`, ROAS slope in `T`.
- CPA mode -> inverse-normalized CPA in `S`, inverse-CPA slope in `T`.

## Required backend checks before UI rollout
1. **Ablation study**: compare ranking stability of new health vs raw-performance score on creatives with `age_days > 30`.
2. **Distribution check**: histogram of final 0-100 scores should avoid collapse at 0 or 100.
3. **Sanity check**: map score bands and run confusion matrix vs synthetic `creative_status`; major divergences must be explainable.

## Implementation contract (for engineers)
1. Compute/store per-creative components `S,C,T,R,E,B` and final `health`.
2. Return component breakdown in API payload so frontend can explain score contributions.
3. Keep deterministic defaults:
   - Missing metric values -> component `0.0`
   - Missing trend before day 7 -> `T=0.0` via gate
   - Missing cohort rank after fallback -> `R=0.5` neutral
4. Clamp all components to `[0,1]`; clamp health to `[0,100]`.
5. Preserve existing `status_band` mapping until recalibration is explicitly approved.
