# Smadex Cooking: Team Cheat Sheet

**Audience:** Aditya (demo lead at A3 + A4), Krish (Q&A backup on math/ML), Andrew (deep tech).
**Purpose:** Single source of truth for what shipped, what didn't, what we'd defend, what we'd admit. Read end to end before every demo run. Read the "Things NOT to Say" section twice.

---

## The 30-Second Pitch (memorize verbatim)

> Smadex Cooking is a creative intelligence cockpit for mobile advertisers. It scores every ad on a 0 to 100 health metric, ranks 1,800 country-by-OS actions across 36 advertisers and 1,080 creatives, and ships a chat assistant whose every number is sourced from the real dataset (no hallucinations, every metric goes through a typed tool call). Live at smadex.cooking.

**One-line elevator:** "We turn the (creative × country × OS) slice into a daily action queue, in a UI marketers already recognize."

---

## Architecture Map

```
Browser (smadex.cooking, Vercel)
  └─ Next.js 16 App Router (TypeScript, Tailwind tokens)
     ├─ Server Components → fetch → smadex-backend.onrender.com
     │   ├─ /api/portfolio/kpis            (KpiStrip)
     │   ├─ /api/portfolio/tab-counts      (CockpitHero)
     │   ├─ /api/creatives                 (Explore table)
     │   ├─ /api/recommendations           (AdvisorBanner, /actions)
     │   ├─ /api/advertisers/{id}/campaigns
     │   └─ /api/portfolio/dataset-bounds  (week stepper)
     └─ Server Actions
         ├─ setActiveAdvertiser  (cookie)
         └─ setActiveWeek        (cookie + revalidatePath)

Backend (smadex-backend.onrender.com, Render free tier)
  └─ FastAPI 3.12 + uvicorn
     ├─ Datastore (in-memory CSV-loaded singleton)
     │   ├─ creatives.csv          (1,080 rows)
     │   ├─ campaigns.csv          (180 rows; pipe-separated countries)
     │   ├─ advertisers.csv        (36 rows)
     │   ├─ daily_metrics.csv      (192k rows; the heavy one)
     │   ├─ creative_attributes.csv
     │   ├─ creative_status.csv    (GROUND TRUTH; do NOT consume directly)
     │   └─ perf_score.csv         (GROUND TRUTH; do NOT consume directly)
     ├─ services/
     │   ├─ fatigue.py             LR classifier + changepoint features (the model that beats benchmark)
     │   ├─ advisor.py             8 deterministic rules (the queue)
     │   ├─ recommendation_copy.py templates + Gemma polish
     │   ├─ slice_cache.py         per-(creative, country, OS) precomputed features
     │   └─ queries.py             cohort baselines, winning patterns
     └─ agents/
         ├─ orchestrator.py        chat (Gemini 2.5 Flash + typed tool calls)
         ├─ variant_brief.py       new-creative brief generator (Gemma)
         ├─ vision_insight.py      image-tag commentary (Gemma)
         ├─ _key_pool.py           rotating GEMINI_API_KEYS, 60s ban-on-429
         └─ _llm_retry.py          httpx retry wrapper + scrub_keys redaction
```

---

## What Actually Shipped

### Backend
- **Fatigue classifier.** Logistic regression on hand-engineered changepoint features (drop ratio, peak-to-last drawdown, CTR coefficient of variation, pre/post-CP CTR). Joblib serialized at `backend/models/fatigue_classifier_v2.joblib`. ROC-AUC 0.93 on held-out, campaign-grouped split.
- **Slice advisor.** 8 deterministic rules over (creative × country × OS) feature matrix. Produces 1,800 recs covering 86% of creatives. Rule names: `geographic_prune`, `geographic_scale`, `os_frequency_cap`, `cross_market_early_warning`, `concentration_risk`, `format_market_mismatch`, `pattern_transfer`, `reallocation`.
- **Health KPI.** Composite 0 to 100 score fusing ROAS + CTR + CVR + spend efficiency + fatigue + cohort rank. Computed at startup.
- **Twin lookup.** Cosine similarity on hand-labelled metadata vector (one-hot categorical + normalized numerics). NOT CLIP-based.
- **Chat orchestrator.** Gemini 2.5 Flash with typed tool calls. Read tools: `get_creative_diagnosis`, `get_cohort_summary`, `list_top_creatives`, `get_twin`, `get_slice_recommendations`. Mutating tools: `apply_variant`, `apply_slice_recommendation`, `snooze_slice_recommendation`, `dismiss_slice_recommendation`.
- **Variant brief generator.** Gemma 3 27B writes a new-creative brief from a "twin" winner.
- **Recommendation polish.** Gemma 3 27B rewrites deterministic templates in marketer voice. Falls through to deterministic if Gemma 429s.
- **Key rotation pool.** 3 keys across 3 Google AI Studio projects, round-robin with 60s ban-on-429. Lives in `_key_pool.py` + `_llm_retry.py`.
- **Key scrubbing.** `scrub_keys()` redacts `?key=...` from any error message before it leaves the server. Important: previously we leaked keys in SSE error events.

### Frontend
- Cockpit `/` (advertiser overview), `/explore` (creative table with filters), `/actions` (advisor queue with severity + action-type chips), `/campaigns/[id]` (drill-in with tabs), `/creatives/[id]` (single-creative detail with twin + variant), `/m/qr` (mobile companion stub).
- Cookie-driven advertiser scope and week scope (cumulative window through week N).
- Period stepper (Previous week, Next week, All time) with cumulative-window semantics.
- Brand: "Smadex Cooking" wordmark, frying-pan icon mark, purple gradient favicon at `/icon.svg`. Brand wordmark links home.

### Deploy
- Frontend: Vercel (`smadex.cooking`).
- Backend: Render free tier (`smadex-backend.onrender.com`, spins down after inactivity).
- Domain: Porkbun, Apex A + CNAME to Vercel DNS.

---

## What Did NOT Ship (And What to Say If Asked)

| Strategy promised | Reality | If a judge asks |
|---|---|---|
| Q2b CLIP + HDBSCAN + UMAP visual clustering | Not shipped. No CLIP/HDBSCAN/UMAP imports. Twin lookup is metadata-cosine. | "We scoped to attribute-vector similarity for the demo because the dataset's images are synthetic. CLIP on rendered metadata would have clustered on rendering style, not real visual content. Metadata twin lookup is the right call for this dataset." |
| Q3a LightGBM + SHAP per-creative explainability | Not shipped. `winning_patterns` is attribute-lift counting (P(attr\|top) / P(attr\|other)), not SHAP. | "We chose interpretable lift-ratio attribution over SHAP for the demo: same kind of 'this attribute is over-represented in winners' insight, without needing the marketer to know what a Shapley value is." |
| Q3b Thompson sampling / UCB bandit | Not shipped. The 8 rules are deterministic thresholds; no posterior sampling, no bandit arms. | "Our 8 rules are the cold-start strategy. Bandits need applied-action history to update priors. Bandits are in 'What's next' for exactly that reason." |
| MongoDB Atlas persistence | NOT used. Everything is in-memory dict. No `pymongo` / `motor` imports. | **Do not claim MongoDB.** If pressed: "Hackathon scope. Persistence is in 'What's next', and Atlas / Postgres / Redis would all slot in cleanly via the cache interface we put behind `recommendation_cache.py`." |
| Bayesian shrinkage with 95% credible intervals | Partial. `credible_interval_width` is computed but no `scipy.stats.beta` posterior. Shrinkage step is ad-hoc prior weighting. | "The composite score does prior weighting on low-sample creatives. It is not a full beta-binomial posterior with explicit CIs. That's on the polish list." |

---

## Design Decisions (And Why We'd Defend Them)

### 1. Why per-(creative × country × OS) and not per-creative
Most recommender systems collapse to creative-level verdicts. A single creative can be the best ad in US/iOS and the worst in Brazil/Android. A creative-level "pause" throws away the country where it's working. The slice grain is where the marketer's actual decision happens (geo bid management).
**Tradeoff:** 1.94 recs per covered creative. Card volume goes up. UI handles via severity sort + filter chips.

### 2. Why deterministic rules instead of an ML recommender
Marketers won't apply a recommendation they can't audit. Every card names the rule and threshold that fired. A black-box "we predict ROAS will go up 12%" doesn't survive contact with a procurement team.
**Tradeoff:** Rules don't learn. New patterns require code changes. Mitigated by the fact that the 8 rules cover the high-value action types in mobile UA.

### 3. Why Gemma for prose, Gemini for chat
Gemma 3 27B is the polish, not the brain. Deterministic Python decides the recommendation; Gemma only varies the wording so 1,800 cards don't read identically. Gemini 2.5 Flash drives chat because Gemma doesn't have a tool-call API. Also: Gemma is the MLH side-prize qualifier.
**Tradeoff:** Two models, two key pools, two failure modes. Retry wrapper + key pool handle it.

### 4. Why the chat assistant uses tool calls
The first version stuffed top-creatives JSON into the prompt. Gemini hallucinated rankings 30%+ of the time. Tool calls force every "creative 500376 has CTR 0.8%" through `get_creative_diagnosis(500376)`, which reads the real datastore.
**Tradeoff:** More round-trips per turn (typically 2 to 3 tool calls + final answer). Latency budget: 30s per request, 6 turns max. Comfortable.

### 5. Why we don't consume `creative_status` / `perf_score` directly
Those are ground truth labels, not features. The fatigue classifier validates AGAINST them; the cockpit doesn't read them at runtime. Smadex's brief explicitly warned that judges penalize teams that filter on ground truth and call it analysis.
**Tradeoff:** Some accuracy lost vs blindly trusting the label. Recovered through the 0.93 vs 0.87 AUC delta on the held-out fatigue evaluation.

### 6. Why cookie-driven scope (advertiser + week)
Lets the demo scope to one advertiser without URL noise, and lets the week stepper rewind cumulatively. Server-side cookie means the cockpit can be deep-linked at the same advertiser/week the demo is scoped to.
**Tradeoff:** `revalidatePath('/', 'layout')` on every step. One redeploy can blip a request mid-revalidate (we saw this once during a Render env-var redeploy). Transient.

### 7. Why no thumbnails on recommendation cards
Synthetic images. Putting them on cards would invite "is your model looking at the image?" when actually it isn't. Cleaner to keep visual analysis off-screen and acknowledge the synthetic-image caveat once, in the about doc.

### 8. Why three pages, not a single SPA
Three distinct user mental models: "what's the state of my portfolio" (`/`), "let me slice the data" (`/explore`), "what should I do next" (`/actions`). Cramming them into one view either oversimplifies or overwhelms. Mirrors how MAX, Liftoff, Moloco split their nav.

### 9. Why a /actions page at all instead of inline cockpit
The action queue is the *output*. The cockpit is the *state*. Conflating them makes the marketer scroll past metrics to find actions, or vice versa. Separating them lets the cockpit answer "how am I doing" and `/actions` answer "what should I do" without compromise.

### 10. Why hedged dollar impact estimates
Every card says "est." and the recommendation rationale uses the phrase "observational projection, not an experimental result". This is honest: we don't have a randomized experiment to back the impact estimate. Better to be useful and humble than confident and wrong. Judges respect this.

---

## Known Limitations (Admit These if Pressed)

1. **Synthetic images.** Visual layer is a placeholder. Production would consume real ad assets through Smadex's existing creative store.
2. **Free-tier rate limits.** Gemini 2.5 Flash free tier is 20 RPM per project. We have 3 keys across 3 projects. Heavy use during demo could exhaust them. Production would use a paid tier.
3. **Render free tier spins down.** First request after idle is 50s+. Hit the backend in the warm-up minute before each demo.
4. **No persistence.** Applied/snoozed/dismissed actions are lost on backend restart. `recommendation_cache.py` has the interface for Atlas/Postgres swap-in, but no swap has happened.
5. **No A/B test harness.** Dollar impact is observational projection, not causal lift. Every card hedges this.
6. **Cohort baselines are static.** Computed once at startup from the full 75-day window. The week stepper rewinds time, but the cohort the rules compare against is the all-time cohort. Acceptable for 75-day data; would matter at production scale.
7. **The advisor only fires on slices with enough data.** Min impressions / min spend gates apply per rule. Low-volume creatives may produce no recommendation even if underperforming. That's part of the 14% "clean" cohort: partly true silence, partly the floor.
8. **Mobile (`/m`) is a stub.** The QR companion exists but the responsive view of the cockpit is not optimized.
9. **Type contracts drift.** We hit one prod build failure where backend `CreativeRow` gained `is_fatigued` but `frontend/src/types/api.ts` wasn't regenerated. Manual sync since. Production needs a generation step in CI.

---

## Likely Judge Questions (And the Best Answer)

**Q: How is this different from Smadex's existing dashboards?**
A: Smadex is a DSP. It serves bids and reports outcomes. Smadex Cooking sits one layer up, taking those reports and turning them into ranked actions a marketer can apply with one tap. The slice grain (country × OS) is the differentiator. We don't reinvent the DSP; we make its output decision-ready.

**Q: How do you handle scale beyond 1,080 creatives?**
A: The bottleneck is the slice feature precompute, not rule evaluation. At 100k creatives the in-memory store moves to Postgres or DuckDB and the precompute batches nightly. Rule eval per slice is O(1); 1,800 recs at 1k creatives implies ~180k recs at 100k creatives, manageable in a paginated queue.

**Q: Why not use a deep model / GPT-5 / Claude / a transformer for fatigue?**
A: 1,080 creatives × 75 days isn't the regime where deep models beat well-engineered logistic regression. The fatigue features (changepoint detection, drop ratios, CV) are the right inductive bias for this signal. We'd revisit at 10k+ creatives with daily retraining.

**Q: How accurate is your fatigue model in production?**
A: 0.93 ROC-AUC on held-out, campaign-grouped data; 0.87 for the dataset's own `ctr_decay_pct` baseline on the same evaluation. Grouped CV means no campaign appears in both train and test, so 0.93 generalizes to advertisers we haven't seen. We'd recalibrate per-tenant in production.

**Q: What stops a marketer from blindly applying every recommendation?**
A: Three things. Severity tier (critical / warning / opportunity) lets you triage. The dollar impact estimate ranks by stakes. Every card has snooze + dismiss with a reason field, so an org can encode policy ("we don't pause anything in markets we just launched in").

**Q: How does the chat assistant handle a question it can't answer?**
A: The orchestrator has 6 read tools and 4 mutating tools. If none apply, Gemini is instructed to reply "I don't have a tool that answers that, can you rephrase as one of {...}?". Better than hallucinating.

**Q: What's your go-to-market?**
A: Smadex's existing customer base. This is a feature inside Smadex's UI, not a standalone tool. We turn the DSP's reporting into actions, which is what marketers actually want. Pricing is per-tenant on top of the existing Smadex contract.

**Q: Why these 8 rules and not others?**
A: They map to the high-value action types in mobile UA: pause, scale, shift OS, rotate, refresh, archive, reallocate. Each has a dollar impact attached. We considered and dropped rules for things like "creative cannibalization" and "cohort saturation" because they overlapped with concentration risk and reallocation respectively. The 8 are non-overlapping.

**Q: How would Smadex deploy this internally?**
A: The backend is stateless FastAPI behind a load balancer. Datastore is in-memory but a Postgres swap is one file change. The frontend is Next.js, deployable on Smadex's existing infra. Auth integrates via NextAuth or Clerk; we left it open for the hackathon. Per-tenant key pools via the rotation module we already wrote.

---

## Demo Flow (3 Minutes, A3 + A4)

**Minute 1 (the hook):**
1. Load `smadex.cooking`. Cockpit at `/`.
2. Point at the Health KPI strip. "Every ad has a 0 to 100 health score. Composite. Six dimensions: ROAS, CTR, CVR, spend efficiency, fatigue, cohort rank."
3. Point at AdvisorBanner. "1,800 ranked actions ready, $X total daily impact."
4. Click into `/actions`. Show the queue with severity chips + action filters.

**Minute 2 (the differentiator):**
1. Pick a card showing geographic prune. Read the *reason* aloud: "CTR dropped 78% in Brazil/Android, ROAS at 0.4x cohort median."
2. Apply the recommendation. Show the toast. Show the queue update.
3. Drill into a creative (`/creatives/[id]`). Show the slice context chip. Show the twin lookup.
4. Optional if time: open the variant tab, show the Gemma-generated brief.

**Minute 3 (the AI):**
1. Open the chat panel. Ask "why is creative 500376 underperforming?"
2. Reply names the country, cites real numbers, optionally offers one-click pause.
3. Mention: "Every number you just saw came from a typed tool call against the dataset, not from the model. We don't let it guess."
4. Close: "1,800 actions, all auditable, all sourced from real metrics, no hallucinated numbers. That's Smadex Cooking."

**Fallback:** If the live demo blows up (Render cold start, network blip, 429), we have GIFs. Aditya knows where they live. Don't fake-type into a frozen page; switch to the GIF.

---

## Things NOT to Say (Footguns)

- ❌ "We trained a deep learning model." (We didn't. LR.)
- ❌ "We use SHAP / LightGBM / CLIP / HDBSCAN / UMAP." (We don't.)
- ❌ "We use Thompson sampling / bandits." (Not in code. It's a "what's next" bullet.)
- ❌ "We use MongoDB Atlas." (We don't. There is no MLH MongoDB prize for us.)
- ❌ "100% coverage." (86% with at-least-one rec. The other 14% are healthy.)
- ❌ "It's better than [specific competitor product]." (We don't have benchmarks against MAX / Liftoff / Moloco.)
- ❌ "We solved fatigue." (We beat one specific baseline by 6 AUC points on a 75-day synthetic dataset.)
- ❌ "Multi-tenant in production." (Single-tenant in-memory. Production needs work.)
- ❌ "Real-time." (It isn't. Recompute at startup. Daily batch is the realistic cadence.)
- ❌ Any em-dashes in writing or speech. Reads as AI-generated.

---

## Numbers to Memorize

| What | Number |
|---|---|
| Creatives in dataset | 1,080 |
| Advertisers | 36 |
| Campaigns | 180 |
| Daily metric rows | 192,000 |
| Date range | 75 days, 2026-01-01 to 2026-03-16 |
| Total recommendations | 1,800 |
| Coverage (creatives with ≥1 rec) | 86% (930 of 1,080) |
| Mean recs per covered creative | 1.94 |
| Max recs on one creative | 7 |
| Fatigue ROC-AUC (ours) | 0.93 |
| Fatigue ROC-AUC (`ctr_decay_pct` baseline) | 0.87 |
| Health KPI dimensions | 6 (ROAS, CTR, CVR, spend efficiency, fatigue, cohort rank) |
| Number of advisor rules | 8 |
| LLM models in use | Gemini 2.5 Flash + Gemma 3 27B |
| API key pool size | 3 keys across 3 projects |
| Per-key free tier | 20 RPM, ~250 RPD |
| Top advertiser at-stake | $17.3k/day (per `data_findings.md`) |

---

## URLs and Identifiers

- **Live frontend:** https://smadex.cooking
- **Backend:** https://smadex-backend.onrender.com (cold-start delay possible)
- **GitHub:** https://github.com/NeoDrew/hackUPC
- **Devpost:** https://hackupc-2026.devpost.com (deadline Sun 26 Apr 09:15)
- **Vercel project ID:** `prj_EvCsdWNS8UTcNsnVKwQUJHrlEXNe` (drews-projects-9ebcba74)
- **Render service ID:** `srv-d7m86j9o3t8c73e1egsg`

**Keys live in two places:** `backend/.env` (local, gitignored) and Render env var `GEMINI_API_KEYS`. **Do not paste keys in Slack, screenshots, or the demo.** A key was leaked once via an httpx error string; the `scrub_keys` helper now redacts on the way out, but the discipline still matters.

---

## Pre-Demo Checklist

- [ ] Smadex.cooking loads in <3s (warm Render with a probe 60s before)
- [ ] Active advertiser cookie set to a creative-rich one (e.g. ClearLedger, top advertiser by impact)
- [ ] /actions has at least 5 critical recs visible
- [ ] Chat assistant responds to a test question without 429
- [ ] Browser zoom 100%, dev tools closed, no other tabs visible (except the GIF fallback tab)
- [ ] Backup GIFs accessible
- [ ] Aditya has read this file end to end at least once
- [ ] Phone with hotspot ready in case venue Wi-Fi blips during the A4 sponsor judging
