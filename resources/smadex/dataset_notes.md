# Smadex dataset — engineering notes

Distilled from `Smadex_Creative_Intelligence_Dataset_FULL/README.md` + `data_dictionary.csv` + a direct inspection of every CSV. Read this before touching the data.

## Scale

| Entity | Count | Notes |
|---|---|---|
| Advertisers | 36 | 6 per vertical |
| Campaigns | 180 | exactly **5 per advertiser** (uniform) |
| Creatives | 1,080 | exactly **6 per campaign** (uniform) |
| Daily fact rows | 192,315 | date × creative × country × OS |
| Asset PNGs | 1,080 | `assets/creative_<id>.png` |
| Date range | 2026-01-01 → 2026-03-16 | ~75 days |
| Countries | 10 | BR, CA, DE, ES, FR, IT, JP, MX, UK, US |
| OS | 2 | Android, iOS |
| Verticals | 6 | ecommerce, entertainment, fintech, food_delivery, gaming, travel (180 each) |
| Formats | 5 | banner (199), interstitial (344), native (289), playable (48), rewarded_video (200) |

All of it fits comfortably in memory. Total on-disk: ~18 MB of CSVs + ~15 MB of PNGs. Pandas is fine; no Spark needed.

## Files & join graph

```
advertisers (36)
  └── advertiser_id ──> campaigns (180)
                          └── campaign_id ──> creatives (1,080)
                                               └── creative_id ──> creative_daily_country_os_stats (192k)
```

- `creative_summary.csv` — pre-aggregated per creative (one row per creative) with `creative_status`, `fatigue_day`, `overall_ctr/cvr/ipm/roas`, `first_7d_*`, `last_7d_*`, decay %, `perf_score`, plus every creative-metadata column copied through.
- `campaign_summary.csv` — pre-aggregated per campaign with overall CTR/CVR/ROAS.
- `creative_daily_country_os_stats.csv` — **the only time-series table**. One row per `(date, creative, country, os)`. Columns: `impressions`, `viewable_impressions`, `clicks`, `conversions`, `revenue_usd`, `spend_usd`, `video_completions`, `days_since_launch`, `impressions_last_7d`.

## Metadata columns on each creative (rich — use this)

String/categorical: `theme`, `hook_type`, `cta_text`, `headline`, `subhead`, `dominant_color`, `emotional_tone`, `language`, `format`, `vertical`.

Numeric 0–1 scores: `text_density`, `readability_score`, `brand_visibility_score`, `clutter_score`, `novelty_score`, `motion_score`.

Integers: `duration_sec`, `copy_length_chars`, `faces_count`, `product_count`, `width`, `height`.

Binary flags: `has_price`, `has_discount_badge`, `has_gameplay`, `has_ugc_style`.

Use these directly for Q3's attribute cube — **no need to re-extract from images**. CLIP remains useful for visual similarity / clustering, but not as the primary attribute source.

## Ground-truth labels (use carefully)

- `creative_status ∈ {top_performer (46), stable (740), fatigued (199), underperformer (95)}` — synthetic label from the generator.
- `fatigue_day` — integer day number when fatigue became material. **Blank** for non-fatigued creatives; don't render as NaN in the UI.
- `perf_score` — synthetic composite score on 0–1 scale.

**Do not** `filter status=="fatigued"` and call that your fatigue detector — judges will flag it instantly. Instead:

- Compute our own fatigue signal (daily time series → decay model).
- Report confusion matrix against the ground-truth label.
- Headline: *"we catch 87% of ground-truth fatigued creatives and also flag 14 more the label missed, validated by manual inspection of their CTR curves."*

Same logic for `perf_score`: compute Bayesian-shrunk ranking, show it correlates with perf_score on the stable bucket, diverges where perf_score is over-confident on small-sample creatives.

## Known quirks (from `README.md`)

1. **Perfectly uniform portfolio** — every advertiser = 5 campaigns × 6 creatives. Drop "most active advertiser / biggest portfolio" slides.
2. **`fatigue_day` is blank** for non-fatigued creatives — `pd.notna()` filter is equivalent to `status=="fatigued"` but less readable.
3. **Synthetic images** — they're rendered from the metadata. CLIP embeddings will partly cluster by rendering style, not semantic content. Caveat any visual similarity claim.

## Gotchas we'd only notice at runtime

- **Spend per (creative, country, OS, day) is non-zero even when impressions = 0** on early days? Worth checking. If so, the row represents allocated spend that didn't serve.
- **Zero-video-completion rows** for `format ∈ {banner, native}` — `video_completions` is 0 there by design, not missing data. Don't treat 0 as missing.
- **`impressions_last_7d` is a rolling window column**, not a raw aggregate — if you sum it across dates you'll double-count. Use it only as a feature, not as a sum target.
- **`target_os ∈ {Android, iOS, Both}`**. Campaigns with `target_os="Both"` generate daily rows for both OS; campaigns with a single target OS still have daily rows for that OS only.
- **`countries` column in `campaigns.csv` is pipe-separated** (e.g. `"CA|US|ES|JP"`). Explode before joining.
- **Metric scales vary by vertical**. Gaming has ~2× the CTR of fintech on these synthetic patterns — cohort-adjust before ranking across verticals.

## Vertical × format × country → fair benchmarks

The uniform 6-per-campaign structure means every campaign has exactly 6 creatives across the same format/theme/CTA mix. This makes **within-campaign ranking** the cleanest unit of comparison. Use it:

- "Within this campaign, creative X is best; creative Y is bottom."
- Much stronger than global rankings that mix verticals.

## Recommended pre-processing pipeline (runs in < 30 s on a laptop)

```python
import pandas as pd
from pathlib import Path

ROOT = Path("resources/smadex/Smadex_Creative_Intelligence_Dataset_FULL")

advertisers = pd.read_csv(ROOT / "advertisers.csv")
campaigns   = pd.read_csv(ROOT / "campaigns.csv", parse_dates=["start_date", "end_date"])
creatives   = pd.read_csv(ROOT / "creatives.csv", parse_dates=["creative_launch_date"])
daily       = pd.read_csv(ROOT / "creative_daily_country_os_stats.csv", parse_dates=["date"])
cr_summary  = pd.read_csv(ROOT / "creative_summary.csv", parse_dates=["creative_launch_date"])

# Explode pipe-separated country lists on campaigns
campaigns["country_list"] = campaigns["countries"].str.split("|")

# Daily time series per creative (global, country-agnostic)
daily_per_creative = (
    daily.groupby(["creative_id", "date"], as_index=False)
         .agg(impressions=("impressions", "sum"),
              clicks=("clicks", "sum"),
              conversions=("conversions", "sum"),
              spend_usd=("spend_usd", "sum"),
              revenue_usd=("revenue_usd", "sum"))
)
daily_per_creative["ctr"] = daily_per_creative["clicks"] / daily_per_creative["impressions"].clip(lower=1)
daily_per_creative["cvr"] = daily_per_creative["conversions"] / daily_per_creative["clicks"].clip(lower=1)
```

Cache the resulting DataFrames to MongoDB (or a local parquet) once so every UI interaction hits memory, not disk.
