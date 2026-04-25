# Strategy — Smadex "Creative Intelligence for Mobile Advertising"

**Decision:** team has committed 100% to the Smadex challenge. This doc is the plan.

## The brief (verbatim — from `resources/smadex/hackaton.md`)

> Build a tool that helps advertisers analyze ad creatives and make better creative decisions. Your prototype should include **at least two** of:
>
> 1. Creative Performance Explorer
> 2. Creative Fatigue Detection
> 3. Explainability Layer
> 4. Recommendation Engine
> 5. Creative Similarity / Clustering
>
> **Bonus points** for: combining image understanding with performance data · detecting patterns across many creatives automatically · generating clear next-step recommendations · making complex data easy for non-technical users.

Evaluation: Usefulness, Clarity, Technical Quality, Creativity, Demo Quality.

**We're shipping all five capabilities. Depth on each beats scope trade-offs.**

## Dataset at a glance

See `resources/smadex/dataset_notes.md` for full engineering notes. One-liner:

- 1,080 creatives (6 verticals × 6 formats × rich metadata), 180 campaigns, 36 advertisers.
- 192k daily rows over 75 days, sliced by country (10) × OS (Android/iOS).
- Every creative has ~20 hand-labelled attribute columns (theme, hook_type, dominant_color, emotional_tone, motion_score, faces_count, has_discount_badge, …). **No need to re-extract from images** — the attribute cube is half-built.
- Ground-truth `creative_status ∈ {top_performer (46), stable (740), fatigued (199), underperformer (95)}` is present. **Use as validation, not as your answer** — judges will penalise a team that filters on it directly.
- 1,080 synthetic PNG assets. CLIP still useful for visual similarity, but caveat: synthetic rendering may leak into the clusters.

## Why this is our challenge to win

- **Andrew did 4 months SWE at The Trade Desk**, one of the world's largest DSPs. He has hands-on intuition for DSP mechanics: CTR/CVR/CPA, frequency capping, creative rotation, cohort-adjusted performance, A/B testing, attribution. Smadex's CTO is ex-FIB/UPC ad-tech — we speak their vocabulary.
- **Aditya ran BigQuery analytics at Virgin Media O2** across a 30-person team. Data-app shape (CSV → aggregate → insight → UI) is his lane.
- **Krish** brings ML/CV muscle (CLIP, HDBSCAN, UMAP) and hackathon velocity.
- **The dataset + brief are tightly scoped.** Hard to over-scope in 36 hours.

## What separates a winning submission from a median one

Median team: loads `creative_summary.csv`, plots bar charts by CTR, `filter status=="fatigued"` for fatigue, LLM-prompts "what to test next". They will lose on every evaluation axis.

Our edge is **statistical rigour + cohort-aware analysis + independently-validated fatigue detection + principled bandit recommendations + a polished marketer-facing UI**. Explicitly beat the precomputed columns (`perf_score`, `ctr_decay_pct`, `creative_status`) rather than consume them.

### Q1 — Creative Performance Explorer

Naïve: sort by `overall_ctr` descending. Wrong. Judges will pick on:
- Small-sample creatives with 10 impressions / 3 clicks look like 30% CTR — noise.
- High-spend creatives got premium placements — selection bias.
- CTR alone ignores CVR: high CTR + low CVR = clickbait.
- Performance varies massively by vertical, country, OS — global ranking lies.

Our approach:

- **Bayesian shrinkage** on CTR and CVR using a beta-binomial prior fit from the pool. Low-sample creatives regress to the mean, not to 30%.
- **95% credible intervals** next to every point estimate — the single strongest visual signal that we know what we're doing.
- **Cohort-adjusted ranking** — compute percentile rank *within* `(vertical, country, OS, format)` slice, then roll up. Creative's "cohort rank" is more defensible than raw rank.
- **Within-campaign ranking** — perfect unit of comparison given the uniform 6-per-campaign structure. "Within this campaign, creative X ranks 1/6 on CVR with 85% posterior confidence."
- **Objective selector** — let the marketer toggle CTR / CVR / IPM / ROAS / CPA (derived from `spend_usd / conversions`) / composite. Ranking re-sorts live.
- **Validation panel** — correlate our ranking against the dataset's `perf_score` on the stable bucket (expected: high correlation). Diverge on the top-performer and underperformer buckets and show *why* — small samples, high variance.

### Q2 — Fatigue Detection + Creative Similarity

Two independent sub-tools, both mapped to bonus-point criteria.

**(a) Temporal fatigue.**

- Use `creative_daily_country_os_stats.csv` — aggregate to daily per creative.
- Fit a per-creative trend: simple choice is exponential decay on 7-day rolling CTR. Robust choice is **isotonic regression** (monotone decreasing fit) + **changepoint detection** (ruptures library or a simple breakpoint test).
- Flag criteria: `last_7d_ctr < first_7d_ctr × threshold` **and** decay is statistically significant under beta-binomial difference-of-proportions test.
- Use the dataset's existing `first_7d_ctr` / `last_7d_ctr` / `ctr_decay_pct` as a **baseline** we must beat — they're simple ratios that miss significance testing.
- **Frequency-response curve** — plot CTR vs `days_since_launch` × `impressions_last_7d` to show where the audience saturates. This is DSP-native vocabulary the Smadex team will recognise.
- **Validation:** confusion matrix of our flags vs `creative_status == "fatigued"`. Headline: *"our detector catches 87% of ground-truth fatigued creatives and flags 14 more that the synthetic label missed — their CTR curves confirm the call."*

**(b) Visual + semantic similarity clustering.**

Two parallel representations; combine them.

- **Attribute clustering.** Use the existing hand-labelled metadata. Feature vector per creative = one-hot(theme, hook_type, dominant_color, emotional_tone, format) + normalised numeric scores + binary flags. Cluster with HDBSCAN — handles variable density, no need to pick `k`. Project to 2D with UMAP for the marketer-facing scatter.
- **Image clustering.** Embed every PNG with **CLIP ViT-B/32** (`open-clip-torch`, CPU-friendly, ~2 min for 1,080 images). Separate HDBSCAN + UMAP over CLIP embeddings.
- **Blended view.** Concatenate attribute-feature-vector with PCA-reduced CLIP embedding (e.g. 64 dims); one final HDBSCAN. This is the "combine image understanding with performance data" bonus-point criterion.
- **Cluster-level performance panel.** For each cluster: average CVR, spread (top vs bottom creative performance), total spend. Flag clusters where spread is small → cannibalising each other. "*Cluster #7 (discount_badge + orange + urgency) has 12 creatives; top CVR 2.9%, bottom CVR 2.7% — consolidate to 3.*"

### Q3 — Explainability Layer + Recommendation Engine

This is the killer. Most teams will punt to an LLM with a vague prompt.

**Explainability (Q3a).**

Per creative or per cluster, explain performance through attribute contribution:

- Fit a **gradient-boosted tree** (LightGBM) to predict CVR from the attribute features. Tiny model, trains in seconds.
- Extract **SHAP values** per creative — which attributes push its CVR up or down.
- Marketer-facing tooltip: "*This creative overperforms by 23% because of `has_discount_badge=1` + `emotional_tone=urgency`; underperforms on `clutter_score=0.71` (too busy).*"
- This is model-agnostic explainability grounded in numbers, not LLM hand-waving.

**Recommendation (Q3b).**

1. **Attribute cube.** Group creatives by `(theme, hook_type, dominant_color, emotional_tone, format, has_discount_badge, has_ugc_style)` — or a chosen subset of high-leverage attributes. Each cell has mean CVR + sample size + spend.
2. **Bandit framing.** Treat untested or thinly-tested combos within an advertiser's portfolio as arms of a multi-armed bandit. Rank by **Upper Confidence Bound** or **Thompson sampling** posterior. Under-explored cells next to high-performing cells float to the top.
3. **Peer benchmarking.** *"Advertiser VantaStyle has never tested `testimonial + discount_badge + blue`. Peers in ecommerce vertical average 2.1× VantaStyle's CVR on this combo."*
4. **Diversity penalty.** Penalise recommendations that would deepen existing clusters — favour combos that explore white space.
5. **Gemma-4 rationale.** Template LLM prose over the structured bandit output. Not the decision-maker — the narrator. *"Test testimonial + product close-up + green palette. Adjacent combos average 2.1× baseline CVR. Under Thompson sampling this arm has 71% probability of beating your current champion within 30 days at current spend."*
6. **Three action types per creative** — **scale / pause / test next** — as the brief requests. Maps directly to ranking output and fatigue flags.

Killer demo line when judges ask *why*: **"because under Thompson sampling on the attribute-combo bandit, this arm has 71% probability of outperforming the current champion within the advertiser's spend window."** That is the moment they stop looking at other teams.

## Product spec

Single-page web app, tab layout, one polished demo flow.

- **Global filter bar** — advertiser, vertical, date range, country, OS, format, objective (CTR / CVR / IPM / ROAS / composite).
- **Tab 1 — Top Performers.** Ranked table with credible intervals, sample sizes, cohort rank. Toggle raw ↔ Bayesian-shrunk ↔ cohort-adjusted — ranking visibly changes. Validation panel correlating our rank vs `perf_score`.
- **Tab 2 — Fatigue & Clusters.** UMAP scatter (colour = performance, size = spend). Click a point → show its cluster + daily CTR time-series. Side panel lists fatigue-flagged creatives with decay curves and the baseline `ctr_decay_pct` we beat. Confusion matrix vs ground-truth.
- **Tab 3 — Explain & Recommend.** Click any creative → SHAP contribution waterfall. Recommendation section: ranked list with attribute combo, expected uplift CI, diversity-gain score, Gemma rationale, risk-tolerance slider.

## Tech stack

- **Backend:** Python 3.12 + FastAPI. `pandas`, `numpy`, `scipy` (beta-binomial posteriors), `scikit-learn`, `lightgbm`, `shap`, `hdbscan`, `umap-learn`, `open-clip-torch` (CPU), `ruptures` (optional, for fatigue changepoints).
- **Frontend:** Next.js + TypeScript + Tailwind. `recharts` for time-series + distributions, `deck.gl` or `plotly` for the UMAP scatter.
- **Persistence:** **MongoDB Atlas** — stores cached embeddings, SHAP outputs, precomputed aggregations, session filters. Pre-populate during a one-time setup script. **Grabs MLH MongoDB Atlas prize.**
- **Domain:** **GoDaddy** free domain → **MLH GoDaddy prize.**
- **LLM:** **Gemma 4** via Google AI Studio for Q3 rationales. Structured-data-to-prose only. **MLH Gemma 4 prize.**
- **Deploy:** Vercel (frontend) + Render or Fly.io (FastAPI backend). Pre-warm backend before demo.
- **Explicit skips:** ElevenLabs (voice in an ad-tech dashboard is gimmicky), Solana, hardware, JetBrains Koog.

**Notebook/Streamlit fallback**: if the Next.js UI slips on Sunday morning, the brief explicitly accepts *"a notebook with a strong interactive demo"*. Keep a Streamlit scratch version running in parallel as risk insurance.

## Timeline (36-hour window — hacking Fri 21:00 → Sun 09:00, submit by Sun 09:15)

| Phase | Hours | Owner | Deliverable |
|---|---|---|---|
| **Skeleton** | 0–3 | Andrew (backend) + Krish (frontend) | Data browser: FastAPI loads 7 CSVs + serves hierarchy + time-series endpoints + static PNG mount. Next.js app shows advertiser → campaign → creative → detail with time-series chart. No analysis, no agents, no styling. (See `~/.claude/plans/curious-skipping-hinton.md`.) |
| **Q1 Ranking** | 3–8 | Krish | Beta-binomial shrinkage ranking + cohort adjustment + raw/shrunk/cohort toggle. Validation against `perf_score`. Andrew wires the route + panel. |
| **Q2a Fatigue** | 6–12 | Krish | Daily-level decay fit + significance test + confusion matrix vs `creative_status`. Frequency-response curve. Andrew wires the route + panel. |
| **Q2b Similarity** | 8–16 | Krish | CLIP embed pipeline, HDBSCAN + UMAP over attributes and images, blended clustering. Cluster-performance panel. Andrew wires the route + scatter component. |
| **Q3a Explain** | 14–20 | Krish | LightGBM fit, SHAP per creative, waterfall component. Andrew wires the route + panel. |
| **Q3b Recommend** | 18–22 | Krish | Attribute cube, Thompson bandit, peer benchmark, diversity penalty. Andrew wires the route + UI. |
| **Orchestrator** | 22–26 | Andrew | LLM agent + tool surface wrapping every Phase-2 route. Chat UI with inline tool-call cards. |
| **Actions** | 26–28 | Andrew | In-memory `ActionLog` + pause/scale/budget endpoints as agent write-tools + "Actions taken" right-rail. |
| **Mongo + Rationales** | 28–30 | Andrew | Mongo persistence of CLIP/SHAP/bandit. One-shot Gemma precompute of per-creative rationales. |
| **Deploy** | 30–32 | Andrew | Vercel + Render + GoDaddy. Pre-warm. |
| **Rehearsal** | 32–34 | Aditya lead | Two timed dry-runs. GIF fallbacks of every demo beat. Devs fix only what Aditya flags. |
| **Submit** | 34–36 | Aditya + devs | Devpost submission by Sunday 08:00. |

**Hard checkpoint at hour 8:** Q1 must be end-to-end in the UI. If not, cut Q2b visual clustering first (keep attribute clustering), then Q3a SHAP second.

## Roles

- **Andrew — backend + LLM orchestrator + deploy + ad-tech framing.** Owns all backend scaffolding (FastAPI, data loading, routes, pydantic schemas), the single LLM orchestrator with tool calls, action endpoints (pause/scale/budget), the frontend panels surfacing Krish's math, deploy (Vercel + Render + GoDaddy), and DSP-accurate vocabulary in the pitch.
- **Krish — all mathematical / ML modules (no LLM work).** Owns Q1 Bayesian shrinkage + cohort-adjusted ranking, Q2a creative stagnation / fatigue detection, Q2b CLIP + HDBSCAN + UMAP similarity clustering, Q3a LightGBM + SHAP, Q3b Thompson-sampling bandit. Also builds the minimal frontend panels that surface each module's output.
- **Aditya — no dev work; demo ownership.** Writes and rehearses the 3-minute pitch in parallel with dev work, runs the verification checklist on every Phase-1 and Phase-2 module the devs complete, curates demo-worthy creative / advertiser IDs, prepares GIF fallbacks for each demo beat, leads the two Sunday dry-runs, carries the pitch at both expo tables (A3 HackUPC + A4 Smadex). Drives the Devpost submission form at the end.

## Demo script (3 min, no slides, same script for HackUPC + Smadex)

**0:00–0:20 Aditya:** *"Mobile advertisers launch hundreds of creative variants. They don't know which to scale, which are tired, or what to try next. Smadex's 1,080-creative dataset lets us answer all three. Andrew's driving."*

**0:20–1:00 Andrew (Q1):** Raw CTR ranking. Flip to Bayesian-shrunk cohort-adjusted. The top creative with 10 impressions vanishes. Show credible intervals. Toggle CVR → CPA → ROAS, rank shifts. *"Ranking depends on objective, sample size, and cohort. We respect all three. Our rank correlates 0.92 with Smadex's `perf_score` on the stable bucket and diverges cleanly on small-sample creatives."*

**1:00–1:45 Krish / Andrew (Q2):** UMAP scatter. Click the densest cluster — *"VantaStyle has 11 testimonial-style creatives with less than 0.3 percentage-point spread on CVR — cannibalising their own spend"*. Switch to fatigue panel — show a detected fatigued creative the ground-truth label missed. Confusion matrix: 87% recall on ground truth, 14 extra flags validated by visible decay curves.

**1:45–2:30 Andrew (Q3):** SHAP waterfall on the worst-performing creative: *"this one loses 41% CVR because `clutter_score=0.78` and `text_density=0.62`."* Switch to Recommendations: *"for PixelForge, test 'gameplay + power-up + green + discount_badge'. Under Thompson sampling, 71% probability of beating their current champion. Adjacent combos average 2.1× CVR. You've never run this combo; three peers in gaming have and all won."* Risk slider shifts rankings.

**2:30–3:00 Aditya:** *"Built in 36 hours on Smadex's own dataset. Deployed at [domain]. Thanks."*

## What we're deliberately not doing

- No voice interface. ElevenLabs in an ad-tech dashboard reads as unfocused.
- No custom model training (beyond the fast LightGBM for SHAP). CLIP zero-shot + classical stats is the right toolkit for 36 hours.
- No slides at judging — code demo only, 3 min max, same project for A3 HackUPC + A4 Smadex.
- No Q4 or Q5 "bonus" tabs. Three tabs, five capabilities inside them, one demo flow.

## Prize stack

- **Smadex prize** — primary.
- **HackUPC general** (DJI Neo / Asus screen / Lego) — HackUPC demo in A3 is mandatory anyway for travel reimbursement.
- **MLH MongoDB Atlas** — we're using it for real.
- **MLH Gemma 4** — rationale generation layer.
- **MLH GoDaddy** — free domain, free prize.
- **MLH ElevenLabs / Solana** — skip. Forcing either loses more on focus than it gains in side-prize.
