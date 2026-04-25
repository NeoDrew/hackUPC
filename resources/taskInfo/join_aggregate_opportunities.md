# Joins & aggregations we haven't fully exploited

The shipped product reads `creative_summary.csv` (one row per creative) for almost everything. That table collapses several dimensions the daily fact table still has — and there are cross-table rollups (campaign / advertiser / cohort) that aren't computed yet. Five candidates ranked by demo + product impact.

> **Companion files:** [`data_findings.md`](data_findings.md) (column-by-column EDA: what's signal, what's noise) and [`research/model_justification.md`](../../research/model_justification.md) (Andrew's fatigue classifier feature analysis).

---

## 1. Per-creative × country breakdown — biggest hidden information loss

**The problem.** `creative_summary.csv` collapses the country and OS dimensions, but `creative_daily_country_os_stats.csv` has them. A creative's CTR can be 3× higher in BR than in JP. Today we tell the user "this creative is fatigued globally" and walk them to a kill action — but the actual marketer decision is more surgical:

> *"Creative #500046 is fatigued globally — but in BR it's still beating cohort. Kill it in 8 countries, keep running in 2."*

**Why it matters.** That's a sharper recommendation than "kill globally" and a strong demo line. It's also information already in the data; we're just throwing it away in the rollup.

**Where it would live.** A "by country" table or sparkline-per-country panel on the creative detail page. Powers a per-country pause / scale recommendation in the assistant.

**My pick of the five.** Highest leverage, modest effort, integrates cleanly with existing per-creative surfaces.

## 2. `daily_country_os_stats` aggregated by `days_since_launch` → cohort fatigue curve

**The play.** Sum daily impressions / clicks across all creatives by `days_since_launch` → average lifetime CTR curve for the dataset. Each creative's own curve compared against that average curve = a much more visceral fatigue diagnostic than `ctr_decay_pct`.

**Status.** Andrew's fatigue classifier already does most of this internally. The gap is **exposure** — not the model. Adding the average-cohort curve as a faded overlay on the fatigue chart on the detail page is a strong visual demo move ("here's where your creative sits vs the average creative at the same age").

**Effort.** Tiny once the aggregate is computed once at startup.

## 3. Campaign → diversity index (Herfindahl over creative attributes)

**The hypothesis.** Each campaign holds 6 creatives. Compute concentration of `theme`, `hook_type`, `dominant_color` across the 6 → Herfindahl index per campaign. Hypothesis to test:

> *"Campaigns running 5/6 same hook_type fatigue at ~2× the rate of diverse campaigns."*

**Why it matters.** If true, it's a killer demo soundbite **and** justifies the `D` (diversity) term in the proposed per-campaign health formula in `data_findings.md` §"Per-campaign health". If false, drop the term and rebuild the formula without it.

**Effort.** ~10 min of pandas to test the hypothesis. Cheapest of the five.

## 4. Advertiser × peer rank within vertical

**The play.** Group `creative_summary` by `advertiser_name`, rank within `vertical` on Bayesian-shrunk ROAS / CTR / health. Surfaces:

> *"Your portfolio is outperforming peers in your vertical by +18% on ROAS this period."*

**Why it matters.** Smadex-customer-friendly framing — advertisers love "you vs peers" panels. Could power an "Advertiser intelligence" page or a single line in the cockpit hero.

**Caveat.** Andrew may already have something like this scaffolded in `queries.health_diagnostics` or similar — worth checking before duplicating.

## 5. Country × format ROAS map

**The play.** Group daily stats by `country × format` → ROAS / CPA matrix. Surfaces:

> *"Banner ads in MX have the lowest cost-per-conversion in your portfolio. Native ads in JP are the worst — pull back."*

**Why it matters.** Geo-expansion / geo-pullback recommendations. Pairs naturally with #1 (per-creative-country breakdown) — #1 is per-creative, this is per-cohort.

**Effort.** ~30 min of pandas + one new endpoint.

---

## Recommended order of attack

1. **#3 (diversity → fatigue correlation)** first — 10 min sanity check that either gives us a soundbite or kills the `D` term in the proposed campaign health formula before we build it.
2. **#1 (per-creative × country panel)** — biggest product upgrade and cleanest demo line.
3. **#2 (cohort fatigue curve overlay)** if there's time — visual polish that makes the fatigue chart pop.
4. #4 / #5 are valuable but lower-priority for the demo deadline.
