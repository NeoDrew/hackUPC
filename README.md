# Smadex Cooking

Creative intelligence cockpit for mobile advertising. Built for the Smadex challenge at HackUPC 2026 (Barcelona, 24 to 26 April 2026).

**Live:** [smadex.cooking](https://smadex.cooking)
**Devpost:** [hackupc-2026.devpost.com](https://hackupc-2026.devpost.com)

> Performance marketers spend their day buried in country-by-OS breakouts on ten different dashboards. They pause an ad in the global view, only to realise it was the only thing working in Mexico. They scale a winner everywhere, only to watch it tank in Brazil because Android users hate the music. **The aggregate is a comfort blanket. The slice is the diagnosis.**

## What it is

A web app that ingests the Smadex dataset (1,080 creatives, 36 advertisers, 75 days, 192k daily rows sliced by country and OS) and turns it into three things:

1. **A health KPI per creative.** A six dimensional view (ROAS, CTR, CVR, spend efficiency, fatigue verdict, cohort relative rank) instead of one number that hides the diagnosis.
2. **A daily action queue.** 1,800 ranked recommendations over every (creative, country, OS) slice, written in plain English. Pause, scale, frequency cap, reallocate. Each card carries the change, the reason, the projected daily dollar impact, and one click apply.
3. **An AI assistant.** Ask "why is creative 500376 underperforming?" and Gemini calls typed Python tools to read real metrics from the in memory datastore. No hallucinated numbers.

## How it maps to the Smadex brief

The brief asked for at least two of five capabilities. We shipped all five.

| Capability | Implementation |
|---|---|
| Creative Performance Explorer | Composite Health KPI (six dimensions) plus cohort relative ranking. Surfaced on the cockpit (`/`) and on every creative detail page. |
| Creative Fatigue Detection | Logistic regression classifier on hand engineered changepoint features (drop ratio, peak to last drawdown, CTR coefficient of variation, pre and post changepoint CTR deltas). Tiered verdicts (clean, watch, fatigued) with a predicted fatigue day. |
| Explainability Layer | Per creative diagnosis with metric breakdown, peer benchmarks, and acronym tooltips for CTR, CVR, ROAS, IPM, CPI, CPM, KPI, ATT, DSP, MMP, MMM, LTV. |
| Recommendation Engine | Eight deterministic rules over the (creative, country, OS) feature matrix: geographic prune, geographic scale, OS frequency cap, cross market early warning, concentration risk, format market mismatch, pattern transfer, reallocation. Polished into marketer voice by Gemma 3 27B. |
| Creative Similarity / Clustering | Twin comparison surface (per creative) that pulls cohort matched peers and a Gemma generated vision insight. |

### Validated against ground truth

Fatigue classifier: **0.93 ROC AUC** on a held out, campaign grouped test split (no campaign appears in both train and test). The dataset's own pre computed `ctr_decay_pct` baseline scores 0.87 on the same evaluation. We beat the shipped signal by 6 points of AUC.

The advisor surfaces at least one recommendation on 86% of creatives. The remaining 14% are clean and the system stays quiet.

## Architecture

```
Next.js 16 cockpit (Vercel)            FastAPI service (Render)
┌──────────────────────────────┐       ┌─────────────────────────────┐
│ /              cockpit       │       │ in memory datastore         │
│ /actions       advisor queue │ HTTPS │ ├ advertisers / campaigns    │
│ /creatives/X   creative view │ ───── │ ├ creatives + metadata       │
│   ├ /twin      cohort match  │       │ └ daily country os stats     │
│   └ /variant   brief gen     │       │                              │
│ /explore       portfolio     │       │ services/                    │
│ /campaigns/X   campaign view │       │ ├ advisor (8 slice rules)    │
│ /m             phone view    │       │ ├ fatigue (LR + changepoint) │
│                              │       │ ├ campaign_health (KPI)      │
│ ChatLauncher (SSE)           │       │ └ queries (cohort, peers)    │
└──────────────────────────────┘       │                              │
                                       │ agents/                      │
                                       │ ├ orchestrator (Gemini 2.5)  │
                                       │ ├ variant_brief (Gemma)      │
                                       │ └ vision_insight (Gemma)     │
                                       │                              │
                                       │ models/                      │
                                       │ └ fatigue_classifier_v2      │
                                       └─────────────────────────────┘
                                                      │
                                                      ▼
                                       Google AI Studio
                                       (Gemini 2.5 Flash + Gemma 3 27B)
```

Data lives in memory. The service loads the seven Smadex CSVs once at startup, holds them as pandas frames, and serves the advertiser → campaign → creative hierarchy plus per creative daily time series. Static PNG assets are served under `/assets/`.

The chat orchestrator runs a typed tool loop: the LLM proposes a tool call, the backend runs it against the datastore, the result is fed back, the LLM either calls another tool or writes the final answer. Final answer streams to the client as SSE. A rotating key pool with exponential backoff retry keeps the demo alive on free tier 429s.

## Repo layout

```
hackUPC/
├── backend/                        FastAPI + uv + Python 3.12
│   ├── app/
│   │   ├── main.py                 ASGI entrypoint (CORS, routers, /assets, /healthz)
│   │   ├── config.py               REPO_ROOT, DATASET_ROOT, expected counts
│   │   ├── datastore.py            in memory load of all 7 CSVs
│   │   ├── schemas.py              pydantic models shared with the FE
│   │   ├── routes/                 portfolio, creatives, advertisers, campaigns,
│   │   │                           agent (chat SSE), actions, recommendations
│   │   ├── services/
│   │   │   ├── advisor.py          8 slice rule advisor
│   │   │   ├── fatigue.py          changepoint + LR classifier inference
│   │   │   ├── campaign_health.py  composite KPI scoring
│   │   │   ├── queries.py          cohort / peer / lookup helpers
│   │   │   ├── recommendation_*    deterministic copy + cache
│   │   │   ├── slice_cache.py      precomputed (creative, country, OS) features
│   │   │   └── windowed.py         rolling window aggregations
│   │   └── agents/
│   │       ├── orchestrator.py     Gemini 2.5 chat loop with typed tools
│   │       ├── variant_brief.py    Gemma copy generator
│   │       ├── vision_insight.py   Gemma image insight (twin page)
│   │       ├── _key_pool.py        rotating Gemini key pool
│   │       └── _llm_retry.py       exponential backoff + key scrub
│   ├── models/                     trained joblib classifiers
│   │   ├── fatigue_classifier_v1.joblib
│   │   └── fatigue_classifier_v2.joblib  (the one in production)
│   ├── scripts/train_fatigue.py    re-train from CSVs
│   └── pyproject.toml
│
├── frontend/                       Next.js 16 + React 19 + Tailwind 4 + TS
│   ├── src/app/
│   │   ├── page.tsx                cockpit (KPI strip, advisor banner, campaign grid)
│   │   ├── layout.tsx              top bar, advertiser scope, period scope, chat
│   │   ├── actions/                advisor inbox queue
│   │   ├── creatives/[creativeId]/ detail / twin / variant
│   │   ├── campaigns/[campaignId]/ campaign detail
│   │   ├── explore/                portfolio explorer
│   │   ├── m/                      phone view
│   │   ├── debug/                  internal dataset views
│   │   └── globals.css + advisor.css
│   ├── src/components/design/      ~50 design system components (Lucide only)
│   ├── src/lib/                    API client, scope cookies, formatters
│   └── package.json
│
├── research/                       supervised analyses backing the prod fatigue signal
│   ├── fatigue_kpi_research.ipynb  feature analysis + model selection + validation
│   ├── model_justification.md      headline numbers + methodology writeup
│   └── pyproject.toml
│
├── resources/
│   ├── smadex/                     dataset (CSVs + 1,080 PNGs) + briefs + notes
│   │   ├── Smadex_Creative_Intelligence_Dataset_FULL/   the dataset
│   │   ├── dataset_notes.md        engineering notes, schemas, gotchas
│   │   └── hackaton.md             official challenge brief
│   ├── taskInfo/
│   │   ├── strategy.md             living plan
│   │   ├── demo_script.md          3 minute live pitch (Aditya / Drew / Krish)
│   │   ├── demo_script.pdf         shareable copy
│   │   ├── data_findings.md        column by column data work
│   │   └── q1_health_metric_implementation.md
│   ├── uidesign/
│   │   ├── HOUSE_RULES.md          the UI rulebook (Lucide only, accent discipline,
│   │   │                           dense neutral by default, 6/8/10 px radius scale)
│   │   ├── architecture.svg/.png   shareable architecture diagram
│   │   ├── handoff.md              design handoff
│   │   ├── tokens.json             design tokens
│   │   └── smadex.css              reference CSS extract
│   ├── submission/
│   │   ├── about.md                Devpost long form
│   │   ├── team.md                 team writeup
│   │   ├── cheatsheet.md           judge prep
│   │   └── build_*.py              Devpost PDF builders
│   └── teamInfo/                   per teammate background
│
├── render.yaml                     Render Blueprint for the backend service
├── vercel.json                     Vercel multi service config (FE + BE proxy)
├── CLAUDE.md                       project instructions for Claude Code
└── README.md                       this file
```

## Quick start

### Prerequisites
- Python 3.12 (managed by [uv](https://docs.astral.sh/uv/))
- Node.js 20+ and [pnpm](https://pnpm.io/)
- A Google AI Studio API key (free tier is enough): [aistudio.google.com/apikey](https://aistudio.google.com/apikey)

### Backend (FastAPI on :8001)

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8001
```

Interactive docs: [http://localhost:8001/docs](http://localhost:8001/docs).
Health: [http://localhost:8001/healthz](http://localhost:8001/healthz).
Static assets: [http://localhost:8001/assets/creative_500001.png](http://localhost:8001/assets/creative_500001.png).

The first boot loads all seven CSVs into memory and asserts the expected counts (36 advertisers, 180 campaigns, 1,080 creatives, ~192k daily rows). It will refuse to start if anything is off.

### Frontend (Next.js on :3000)

```bash
cd frontend
pnpm install
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000). The frontend reads `NEXT_PUBLIC_API_BASE_URL` from `frontend/.env.local` (default `http://127.0.0.1:8001`).

### Regenerate API types

After backend schema changes, with the backend running:

```bash
cd frontend
pnpm gen:types
```

This regenerates `frontend/src/types/api.ts` from the live FastAPI OpenAPI document.

### Research notebook (optional)

```bash
cd research
uv sync
uv run jupyter lab
```

`fatigue_kpi_research.ipynb` is the full feature analysis, model selection, and grouped CV validation that produced `backend/models/fatigue_classifier_v2.joblib`.

## Environment variables

### `backend/.env` (gitignored)

| Variable | Purpose |
|---|---|
| `GEMINI_API_KEYS` | Comma separated list of Google AI Studio keys. The orchestrator rotates across them with exponential backoff retry, so free tier 429s do not crash the demo. |
| `GEMINI_API_KEY` | Single key fallback (used if `GEMINI_API_KEYS` is unset). |
| `VISION_INSIGHT_MODEL` | Optional override for the Gemma image model id. |
| `DATASET_ROOT` | Optional override of the dataset path (defaults to the in repo bundle). Used in deploy if the dataset lives on a Persistent Disk. |
| `FRONTEND_ORIGIN` | Production frontend origin for CORS (e.g. `https://smadex.cooking`). The default CORS regex already covers `*.vercel.app` previews and `localhost`. |

### `frontend/.env.local`

| Variable | Purpose |
|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | Backend origin. `http://127.0.0.1:8001` locally; the Render URL in Vercel previews and prod. |

If `GEMINI_API_KEY(S)` is missing or every key 429s in a row, the AI surfaces (chat, vision insight, variant brief) fall back to canned templates and stamp `is_stub: true` on the response. The UI then shows a `[preview]` chip so judges can still see the flow.

## Dataset

Vendored in `resources/smadex/Smadex_Creative_Intelligence_Dataset_FULL/`. ~18 MB of CSVs plus ~15 MB of PNGs.

| File | Rows | Notes |
|---|---|---|
| `advertisers.csv` | 36 | 6 verticals × 6 advertisers |
| `campaigns.csv` | 180 | exactly 5 per advertiser. `countries` is pipe separated, explode before joining |
| `creatives.csv` | 1,080 | 6 per campaign. ~20 hand labelled metadata columns (theme, hook_type, dominant_color, emotional_tone, motion_score, has_discount_badge, etc.) |
| `creative_summary.csv` | 1,080 | pre aggregated per creative (`overall_ctr`, `first_7d_ctr`, `last_7d_ctr`, `ctr_decay_pct`, `creative_status`, `fatigue_day`, `perf_score`) |
| `campaign_summary.csv` | 180 | pre aggregated per campaign |
| `creative_daily_country_os_stats.csv` | 192,315 | the only time series table. `(date, creative, country, os)` grain |
| `assets/creative_<id>.png` | 1,080 | synthetic renders from metadata. Caveat: CLIP partly clusters on rendering style |

Read `resources/smadex/dataset_notes.md` before touching the data. Key gotchas:

- **Portfolio is uniform by design.** Every advertiser has exactly 5 × 6 creatives. "Who is biggest" analyses are dead ends.
- **Ground truth labels exist** (`creative_status`, `fatigue_day`, `perf_score`). We compute our own signals and validate against them; we never filter on them and call that the answer.
- **Pre computed CTR decay is a baseline to beat**, not an output. Our classifier beats it by 6 ROC AUC points.
- **Slices, not totals.** The (creative × country × OS) grain is where every meaningful recommendation lives.

## Deploy

| Layer | Where | Notes |
|---|---|---|
| Frontend | Vercel | `pnpm build` from `frontend/`. `vercel.json` declares the multi service layout. |
| Backend | Render | `render.yaml` is a Render Blueprint. `uv sync --frozen` build, `uv run uvicorn` start, `/healthz` health check, free plan. |
| Domain | [smadex.cooking](https://smadex.cooking) on Porkbun | Apex `A → 216.150.1.1`, `CNAME www → 30e9567df3329599.vercel-dns-016.com`. |
| LLMs | Google AI Studio | Gemini 2.5 Flash for chat + tool calls, Gemma 3 27B for natural language polish. Free tier; rotating key pool. |

The Render free tier sleeps after 15 minutes of inactivity. Cold start adds ~30s on the first hit; warm requests are sub second.

## Tech stack

**Backend:** Python 3.12, FastAPI, uvicorn, pandas, numpy, scipy, scikit-learn, ruptures, httpx, pydantic v2, joblib.
**Frontend:** Next.js 16 (App Router, Turbopack), React 19, Tailwind 4, TypeScript 5, Recharts, Lucide icons.
**LLMs:** Google Gemini 2.5 Flash (chat orchestrator with typed tool calls), Google Gemma 3 27B (natural language polish on recommendations and variants).
**Tooling:** uv (Python deps), pnpm (Node deps), openapi-typescript (BE → FE type sync).
**Hosting:** Vercel (frontend), Render (backend), Porkbun (domain).

The fatigue classifier is a logistic regression on hand engineered changepoint features. We tried gradient boosted trees and they were marginally worse with much higher latency at inference; LR is the right complexity for the size of the labelled set and the changepoint features carry most of the signal.

## Working conventions

- **`resources/taskInfo/strategy.md`** is the living plan. Update it when decisions change instead of writing chat replies that go nowhere.
- **`resources/smadex/dataset_notes.md`** is the data reference. Update it the moment you discover a new gotcha.
- **`resources/uidesign/HOUSE_RULES.md`** is the UI rulebook. Lucide icons only (no emoji as chrome), accent colour reserved for active state and primary action, neutral by default controls, 6/8/10 px radius scale. The product is a trading cockpit for media buyers: operational, dense, calm; never cute or magical.
- **No em dashes** in user facing prose (Devpost, READMEs, commits). Periods, commas, semicolons, parens.

## Team

Three person team out of Manchester and Southampton.

- **Andrew Robertson** (Manchester CS, final year). Backend, AI orchestration, deploy, ad tech voice in the pitch. FastAPI + in memory datastore. The 8 rule slice advisor that produces the daily action queue. Chat orchestrator with typed tool calls. Gemma agents for variant briefs and vision insights. Rotating key pool with exponential backoff retry. Vercel and Render deploys, smadex.cooking pointed through Porkbun. Four months at The Trade Desk gave the creative metrics and DSP integration intuition that lets the pitch land as a Smadex internal feature, not a hackathon toy. Co-founder of Basanite.
- **Krish Mathur** (Southampton CS, first year). The math and the model. Fatigue classifier from changepoint feature engineering through to a held out, campaign grouped evaluation: 0.93 vs 0.87 ROC AUC over the dataset's own baseline. Tiered fatigue verdicts. Composite Health KPI scoring. Acronym tooltip layer that makes the cockpit legible to non marketers. ICHack26 winner pace applied to a 36 hour build.
- **Aditya Shah** (Manchester CS, final year). The pitch, the demo, and the verification net. Three minute story twice (HackUPC general at A3, Smadex sponsor at A4) without slides. Owns the checklist that catches "actually that is broken in production" before a judge does. CEO of Basanite, 500+ hours of STEM tutoring, 13 month BigQuery placement at Virgin Media O2.

## Hackathon context

Built at **HackUPC 2026**, Barcelona, 24 to 26 April 2026. The Smadex challenge brief asked for a creative intelligence tool covering at least two of five capabilities: explorer, fatigue, similarity, explainability, recommendations. We shipped all five. Same project went to HackUPC general judging at A3 and Smadex sponsor judging at A4, with one demo. We opted into the **MLH Gemma side prize** (Gemma 3 27B handles natural language polish across the app).

A note on the dataset: the images are synthetically rendered from metadata, not real creative. We treat the visual layer as a placeholder. Production would consume real ad assets through Smadex's existing creative store. Everything else (CTR, CVR, ROAS, spend, conversions, fatigue labels, country mix, OS split) is real shaped data, and that is what every model and rule operates on.
