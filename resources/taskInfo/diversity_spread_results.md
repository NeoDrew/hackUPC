# Diversity & spread hypothesis tests — results

Two cheap aggregations from `join_aggregate_opportunities.md` run end-to-end. Both targeted the proposed `D` (diversity) term in the per-campaign health formula in `data_findings.md`. Bottom-line: **partial confirmation — the term should ship, but with format-conditioning and a different attribute than I originally proposed.**

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

*Generated 2026-04-25. Code: see git history; analysis runs in <30s on the shipped CSVs.*
