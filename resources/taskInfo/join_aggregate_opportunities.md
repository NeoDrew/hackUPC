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

## 6. Within-campaign best-vs-worst CTR spread

**The play.** Each campaign has exactly 6 creatives — the cleanest cohort there is. Compute `max(ctr) − min(ctr)` per campaign. Big spread ("one clear winner, 5 mediocre") versus small spread ("uniform mediocrity") drives different recommendations:

> *"Big spread → shift budget to the winner, kill the other 5. Small spread → the whole campaign is tired, refresh all 6."*

**Why it matters.** Today we don't differentiate these two cases. A marketer staring at a $66k underperforming campaign needs to know which one it is — same total cost, very different fix. Also tightly correlated with the proposed `D` (diversity) term in `data_findings.md`'s campaign health formula; high concentration in performance shows up as both low diversity *and* huge max-min spread.

**Effort.** ~10 min — one groupby + a small column.

## 7. Spend-share vs performance-share alignment within campaign

**The play.** For each campaign, compute: does the spend-share across its 6 creatives match the performance-share? If creative A delivers 50% of the CTR but only gets 8% of the spend, the budget is misaligned with the winner.

> *"You're underfunding your winner by $X/day — shift it from the bottom 3 creatives."*

**Why it matters.** **Most actionable signal of all the joins** — a marketer can act on this immediately without changing any creative. Pure budget reallocation. Pairs with #1 (geo) for very surgical recommendations: *"shift $5k/day from creative A to creative B, but only on iOS in BR."*

**Effort.** ~20 min — daily-by-creative aggregate, normalised within campaign, deviation column.

## 8. Day-of-week pattern across daily fact table

**The play.** Group `creative_daily_country_os_stats` by `date.dayofweek` × `format` / `vertical`. Does CTR / CVR / ROAS systematically differ Mon-Fri vs Sat-Sun?

> *"Your fintech campaigns underperform 22% on weekends — pause weekend serving."*

**Why it matters.** Common in real ad data: travel + entertainment surge weekends, B2B / fintech dies. If the pattern exists in this synthetic dataset, surface it as a calendar recommendation; if not, drop it. Either outcome is informative.

**Effort.** ~10 min — one groupby on the daily table.

## 9. Conversion funnel per format

**The play.** Group daily fact by `format` → `impressions → viewable_impressions → clicks → conversions → revenue`. Compute the drop-off rate at each stage per format.

> *"Playable ads have 80% viewability but only 4% click-through — your audience watches but doesn't act."*

**Why it matters.** Diagnoses *which* format leaks *where*. Some formats might lose users at the viewable→click step (boring creative); others at click→conversion (post-click experience). Different fixes per format. Powers a per-format optimisation recommendation we don't have today.

**Effort.** ~15 min — one groupby + ratio columns.

## 10. Campaign launch-cohort fate (market vs creative effect)

**The play.** Group campaigns by `start_date` (week) × `vertical`. Do same-week / same-vertical campaigns trend together? Compare each campaign's CTR trajectory against the average trajectory of its launch cohort.

> *"This isn't your creative dying — the whole gaming category went down the week you launched. Three competitors launched the same week."*

**Why it matters.** Separates **market effects** (everyone in the category is fatiguing together — competitive launch, holiday, audience saturation) from **creative effects** (your creative specifically is the problem). Strong defence / explainability win for a marketer who's about to refresh a creative that didn't actually do anything wrong.

**Effort.** ~30 min — date-week binning + per-cohort trajectory.

---

## Recommended order of attack

1. **#3 (diversity → fatigue correlation)** first — 10 min sanity check that either gives us a soundbite or kills the `D` term in the proposed campaign health formula before we build it.
2. **#6 (best-vs-worst spread)** — also ~10 min; informs whether the campaign-health `D` term and a "shift budget to winner" recommendation are both warranted (they should correlate).
3. **#7 (spend-share alignment)** — strongest standalone product upgrade. Gives a concrete dollar number per campaign without requiring any creative changes.
4. **#1 (per-creative × country panel)** — biggest product upgrade and cleanest demo line. Validate via a quick #4 (geo-variance) check before building the panel.
5. **#2 (cohort fatigue curve overlay)** if there's time — visual polish that makes the fatigue chart pop.
6. **#8 / #9 / #10** are 10-30 min each; cherry-pick whichever yields the strongest soundbite for the pitch.
7. **#4 / #5** are valuable but lower-priority for the demo deadline.
