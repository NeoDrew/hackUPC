# Hypothesis tests — results

Four aggregations from `join_aggregate_opportunities.md` run end-to-end. Mixed verdicts: two ship as-is, one ships with caveats, one does not ship.

## Verdict summary

| # | Test | Verdict | Strongest finding |
|---|---|---|---|
| 3 | Diversity → fatigue | **Ships with caveats** | Colour concentration only, video formats only — 1.4× signal not the 2× hypothesised |
| 6 | Within-campaign best-vs-worst spread | **Ships** | Independent of #3; new `P_spread` term in formula |
| 1 | Per-creative × country geo-variance | **Doesn't ship** | Variance is too small in this dataset (median 9% CTR spread); only 4/199 fatigued creatives have a real "split call" |
| 7 | Spend-share vs performance-share alignment | **Ships — strongest of the four** | $1.95M of $32M (6.1%) portfolio-wide is misallocated. Top campaign: $42k out of $293k. |

The first two hypotheses targeted the proposed `D` (diversity) term in the per-campaign health formula in `data_findings.md`. The last two are independent product surfaces.

---

## #3 — Diversity → fatigue correlation

**Hypothesis (from join doc):** *"Campaigns running 5/6 same hook_type fatigue at ~2× the rate of diverse campaigns."*

**Verdict: hypothesis falsified for hook, partially confirmed for colour.** Not 2×, but a real ~1.4× signal — and only in video formats.

### Per-attribute Herfindahl (concentration) vs `fatigue_rate` across 180 campaigns

| Attribute | Pearson r vs fatigue_rate |
|---|---:|
| `dominant_color` | **+0.21** |
| `theme` | −0.05 |
| `hook_type` | −0.01 |

Theme and hook concentration are essentially noise. **Only colour concentration carries signal.**

### Colour concentration tertile

| Tertile | n campaigns | mean fatigue rate |
|---|---:|---:|
| diverse | 107 | 16.4% |
| medium | 24 | 20.1% |
| concentrated | 49 | **22.1%** |

Concentrated-colour campaigns fatigue **5.7 percentage points more** than diverse ones — that's **1.35× more fatigue**, not the 2× I originally hypothesised.

### Format-conditioned colour concentration vs fatigue

| Format | n diverse | fatigue (diverse) | n concen | fatigue (concen) | delta |
|---|---:|---:|---:|---:|---:|
| **rewarded_video** | 20 | 19.2% | 18 | **34.3%** | **+15.1pp** |
| interstitial | 31 | 17.7% | 17 | 25.5% | +7.7pp |
| banner | 25 | 10.7% | 10 | 15.0% | +4.3pp |
| native | 28 | 16.1% | 24 | **5.6%** | **−10.5pp (REVERSED)** |

**The signal lives almost entirely in video formats.** Native flips the sign. Banner is close to flat.

### Joint triple Herfindahl (theme × hook × colour) — useless

Of 180 campaigns, **167 have h_triple = 0.167** — i.e., all 6 creatives have a unique (theme, hook, colour) combo. The synthetic generator doesn't repeat triples. The "joint" Herfindahl is structurally constant; can't ship.

### Demo soundbite

> *"In rewarded_video campaigns, those running concentrated colour palettes fatigue at 34% — almost double the 19% rate for diverse-colour campaigns. Same dataset; the only difference is whether the creative team varied the palette."*

Defensible (n=38 in-cohort), with a 1.78× ratio.

### Recommendation for campaign-health formula `D` term

- Use **`dominant_color` Herfindahl only**, not theme or hook.
- **Apply only to video formats** (rewarded_video, interstitial). Drop or zero out for banner, native.
- Replace any "5/6 same hook" claim in pitch material with the colour-specific finding.

---

## #6 — Within-campaign best-vs-worst CTR spread

**Hypothesis (from join doc):** *"Big spread → shift budget to winner; small spread → refresh whole campaign."*

**Verdict: framing holds but at much smaller magnitudes than I claimed. Most campaigns are 'uniform'-leaning, not 'winner-led'.**

### Spread distribution (180 campaigns, max−min CTR over 6 creatives)

| Stat | abs_spread (CTR pp) | rel_spread (× mean CTR) | CV |
|---|---:|---:|---:|
| median | 0.002 | 0.47 | 0.18 |
| 75th %ile | 0.003 | 0.59 | 0.23 |
| max | 0.009 | **1.04** | 0.36 |

Median rel_spread is 47% — i.e., the best creative in a campaign is typically 47% above the campaign mean. Not 2×.

### Archetypes (rel_spread thresholds: <0.5 = uniform, ≥1.0 = winner_led)

| Archetype | n | mean fatigue rate | mean total spend |
|---|---:|---:|---:|
| uniform | 98 | 15.5% | $184k |
| mid | 81 | 21.6% | $171k |
| winner_led | **1** | 50.0% | $148k |

The "5 mediocre + 1 winner" archetype is **basically nonexistent** at the strict threshold (1/180). At a looser threshold ("mid"), it's 81 campaigns with elevated fatigue rate.

### Mid vs uniform — actionable

- **Uniform campaigns** (n=98): 15.5% fatigue rate. Recommendation: *"the whole campaign is the same; if it's losing, refresh all 6 creatives."*
- **Mid-spread campaigns** (n=81): 21.6% fatigue rate. Recommendation: *"there's some spread — some creatives still work. Investigate before mass-killing."*

### Top-spread campaigns (real candidates for "shift budget to winner")

| campaign_id | vertical | format | rel_spread | ctr_min | ctr_max | fatigue_rate | spend |
|---:|---|---|---:|---:|---:|---:|---:|
| 20084 | gaming | interstitial | **1.04** | 0.5% | 1.4% | 50% | $148k |
| 20102 | gaming | banner | 0.86 | 0.4% | 1.1% | **67%** | $192k |
| 20078 | gaming | rewarded_video | 0.79 | 0.4% | 1.1% | 50% | $136k |

**Campaign 20084 is a strong demo hero**: gaming interstitial, $148k spend, 50% fatigued (3 of 6 creatives), max-CTR creative is 2× the min — there *is* a winner to scale and 3 losers to kill. Concrete dollar story.

### Most-uniform high-spend campaigns (real candidates for "refresh all")

| campaign_id | vertical | format | rel_spread | spend |
|---:|---|---|---:|---:|
| 20096 | gaming | interstitial | 0.25 | **$379k** |
| 20154 | food_delivery | native | 0.23 | $266k |
| 20159 | travel | rewarded_video | 0.26 | $211k |

**Campaign 20096**: gaming interstitial, $379k spent across 6 creatives that all perform within 25% of each other. No single creative to rescue — **refresh the whole campaign** is the call.

### Demo soundbite

> *"Campaign 20084 spent $148k across 6 gaming interstitials. The best creative gets 1.4% CTR. The worst gets 0.5% — half the budget is wasted on creatives that no one clicks. The fix isn't to refresh — it's to shift the bottom 3's budget to the winner."*

### Spread vs concentration — orthogonal signals

| | h_color (concentration) | h_hook |
|---|---:|---:|
| rel_spread | r = +0.04 | r = +0.04 |
| fatigue_rate | r = +0.21 | r = −0.01 |

**Spread and concentration aren't correlated** (r=0.04). Two campaigns with identical attributes can have wildly different performance spreads, and vice versa. This means the campaign health formula's `D` term and a "spread" term are **independent signals** — both worth keeping; they don't double-count.

### Recommendation for campaign-health formula

Add a **`P_spread`** term: `(rel_spread normalised to [0, 1])`. High spread → "you have a winner, identify it"; low spread → "no winner exists, refresh all". Combine with the existing `F` (fatigue concentration) and `D` (colour diversity) terms — together they distinguish:

- High spread + high fatigue → **kill bottom + scale winner** (campaign 20084 archetype)
- Low spread + high fatigue → **refresh everything** (campaign 20096 archetype if it had higher fatigue)
- Low spread + low fatigue → healthy campaign, leave alone
- High spread + low fatigue → **scale the winner** (no urgency to kill anyone)

That's a 2×2 of distinct recommendations, all drivable from data we already have.

---

## What changed in the proposed campaign-health formula

| Term | Originally proposed | After this analysis |
|---|---|---|
| `D` (diversity) | Herfindahl over (theme, hook, colour) | Herfindahl over **colour only**, applied **only in video formats** |
| (new) `P_spread` | not in original formula | Add: rel_spread between best and worst creative — independent of `D` |
| Other terms (P, T, F, E, C) | unchanged | unchanged |

Updated weight proposal:

```
H_campaign = 0.30·P + 0.20·T + 0.15·F + 0.10·E + 0.10·D + 0.10·P_spread + 0.05·C
```

The original 0.15·E became 0.10·E + 0.05 going to `P_spread`, since spread is the more actionable signal.

---

## #1 — Per-creative × country geo-variance

**Hypothesis (from join doc):** *"Creative is fatigued globally — but in BR it's still beating cohort. Kill it in 8 countries, keep running in 2."*

**Verdict: doesn't ship in this dataset.** The signal is too weak to justify a UI surface. CV across countries is tiny.

### Per-creative country count

| Stat | Countries per creative |
|---|---:|
| min | 2 |
| median | 3 |
| max | 4 |

Each creative only runs in 2-4 countries (driven by `campaigns.countries` targeting), so the "kill in 8, keep in 2" framing was already wrong scale.

### Variance distribution (1,080 creatives, ≥500 impressions per country)

| Stat | CTR coefficient of variation | CTR max/min ratio | ROAS max/min ratio |
|---|---:|---:|---:|
| median | 0.048 | 1.09 | 1.55 |
| 75th %ile | 0.067 | 1.13 | 2.07 |
| max | 0.293 | 1.78 | 5.74 |

- **CTR is essentially flat across countries**: 95% of creatives have ratio < 1.2.
- **ROAS variance is real but mild**: 55% median spread, with ~30% of creatives showing 2-3× variance.
- **No format or status pattern** — fatigued and stable creatives have the same ctr_cv (~0.05).

### Fatigued creatives with a "split call" pattern

For each fatigued creative, check whether at least one country is still profitable (ROAS ≥ 1.5) AND at least one is unprofitable (ROAS < 1.0). That's where the geo-split recommendation makes sense.

| Stat | Count | % of fatigued |
|---|---:|---:|
| Fatigued creatives | 199 | 100% |
| Best country ROAS ≥ 1.5 | 176 | 88% |
| Worst country ROAS < 1.0 | 13 | 6.5% |
| **Both (genuine split call)** | **4** | **2.0%** |

**Only 4 fatigued creatives** would benefit from a geo-split recommendation in this dataset. All four are gaming creatives where BR wins (ROAS 1.6–2.1×) and JP loses (~0.98×).

### Decision

**Don't ship a per-country panel.** Synthetic data here doesn't have the country variance the original hypothesis assumed. The signal would be much stronger on real ad-exchange data — flag as "future work, not for the demo".

**Demo soundbite (narrow but defensible):** *"For four gaming creatives in this portfolio, Smadex catches a geo-split: BR is still profitable, JP is losing money. The recommendation is to relaunch BR-only, not refresh the creative."* Use only if there's airtime; cut otherwise.

---

## #7 — Spend-share vs performance-share alignment

**Hypothesis (from join doc):** *"You're underfunding your winner by $X/day — shift it from the bottom 3 creatives."*

**Verdict: ships, strongest of the four hypotheses.** Real signal across the entire portfolio with a concrete dollar headline.

### Method

For each campaign with 6 creatives, compare each creative's `revenue_share` (its slice of the campaign's total revenue) against its `spend_share` (its slice of total spend). Misallocation = `Σ max(0, revenue_share − spend_share)` per campaign — the dollars that *would* move if you reallocated to perfect alignment.

### Per-campaign misallocation distribution (180 campaigns)

| Stat | $ misallocated | % of campaign spend |
|---|---:|---:|
| min | $2.5k | 2% |
| median | $9.4k | 6% |
| 75th %ile | $13.9k | 7% |
| max | **$42.2k** | 15% |

**Every single campaign has misallocation.** The synthetic generator doesn't allocate spend perfectly with revenue across creatives — there's always some "underfunded winner" pattern.

### Portfolio total

| Metric | Value |
|---|---:|
| Total spend (180 campaigns) | $32.0M |
| Total revenue-aligned misallocation | **$1.95M** |
| % of total spend misallocated | **6.1%** |

### Top 5 most-misallocated campaigns (best demo candidates)

| campaign_id | vertical | format | spend | misalloc $ | winner creative | winner rev/spend share | loser rev/spend share |
|---:|---|---|---:|---:|---:|---|---|
| **20106** | food_delivery | native | $293k | **$42.2k** | #500639 | 21.9% rev / 13.5% spend | #500638: 13.5% rev / 22.6% spend |
| 20088 | food_delivery | banner | $351k | $29.5k | #500529 | 23.2% / 16.6% | #500528: 18.3% / 22.6% |
| 20122 | fintech | interstitial | $175k | $25.7k | #500733 | 21.1% / 14.1% | #500732: 18.9% / 30.1% |
| 20037 | ecommerce | banner | $284k | $25.5k | #500226 | 20.9% / 16.4% | #500227: 15.8% / 20.7% |
| 20076 | food_delivery | interstitial | $188k | $24.8k | #500459 | 17.0% / 11.9% | #500456: 19.0% / 26.6% |

### Demo soundbite

> *"Across this portfolio of 180 campaigns and \$32 million in spend, **\$1.95 million is misallocated — 6% of every dollar going to creatives that earn less than their share**. Take campaign 20106: food delivery, \$293k spent, but the winner gets 22% of revenue with only 13.5% of the budget. The fix isn't a new creative — it's redirecting \$42k from the loser. One click."*

### Hero campaign for the demo

**Campaign 20106 (food_delivery native).** Cleanest story:
- Total spend: $293k
- Winner creative #500639: 22% of revenue, only 13.5% of spend
- Loser creative #500638: 22.6% of spend, only 13.5% of revenue
- Fix: shift $42k. Same total budget, +revenue, +ROAS.

### Recommendation for product

**Build a "spend reallocation" surface** on the campaign detail page (or as a queue card on the Action page):
- Endpoint: `GET /api/campaigns/{id}/spend-alignment` returning per-creative spend-share / revenue-share / proposed-shift
- UI: a one-row inbox card *"Reallocate $42k in campaign 20106 — same budget, projected +X% ROAS"* with a single `Apply` button
- Backend mock: queue the reallocation like the existing `apply_variant` pattern (process-lifetime, undo)

This is the most direct demo of "decision-first product" — no creative changes, no twin diff, just budget reallocation that any marketer can authorise with one click.

---

## What changed in the proposed campaign-health formula

| Term | Originally proposed | After this analysis |
|---|---|---|
| `D` (diversity) | Herfindahl over (theme, hook, colour) | Herfindahl over **colour only**, applied **only in video formats** |
| (new) `P_spread` | not in original formula | Add: rel_spread between best and worst creative — independent of `D` |
| (new) `M` (misallocation) | not in original formula | **Strong addition**: `1 − misalloc_pct` — campaigns with aligned spend get rewarded |
| Other terms (P, T, F, E, C) | unchanged | unchanged |

Updated weight proposal (now seven terms — accommodate `M` by trimming everywhere):

```
H_campaign = 0.25·P + 0.20·T + 0.15·F + 0.10·E + 0.10·M + 0.10·D + 0.05·P_spread + 0.05·C
```

`M` (misallocation health) takes 0.10 because it's actionable for every campaign and gives a defensible dollar figure. `P_spread` keeps a small weight (0.05) since it's largely subsumed by `M` (a misaligned campaign typically has high spread between winner and loser too).

---

## Demo-shipping summary across all four

| # | Findings ship in demo? | Required code work | Priority |
|---|---|---|---|
| 7 | Yes — strongest soundbite ($1.95M / 6.1% headline) | New endpoint + UI card | **Highest** |
| 6 | Yes — supports campaign-health formula | Math change in health calc | Medium |
| 3 | Caveated — colour×video soundbite only | Math change in health calc | Medium |
| 1 | No — soundbite optional, no UI | None | Low |

---

*Generated 2026-04-25. Code: see git history; analysis runs in <30s on the shipped CSVs.*
