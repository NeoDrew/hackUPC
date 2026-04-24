# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

This is the workspace for a three-person team at **HackUPC 2026** (Barcelona, 24–26 April 2026). The team has committed to the **Smadex "Creative Intelligence for Mobile Advertising"** challenge: build a web app that analyses a provided dataset of ad creatives and answers, for a marketer, (1) which creatives work best, (2) which are repetitive or tired, (3) what to test next, with explainability and recommendations.

The repo currently contains research material under `resources/`. Application code will live alongside `resources/` in new top-level directories (e.g. `backend/`, `frontend/`, `notebooks/`).

### `resources/smadex/` — **the live project material**
- **`dataset_notes.md`** — distilled engineering notes on the Smadex dataset. **Read this before touching the data.** Schemas, join graph, row counts, known quirks, gotchas, pre-processing pipeline.
- `hackaton.md` — official Smadex challenge brief (capabilities, evaluation criteria, bonus points).
- `HackUPC Smadex - Challenge.pdf`, `HackUPC Smadex - Intro.pdf` — sponsor slide decks.
- `Smadex_Creative_Intelligence_Dataset_FULL/` — **the dataset**: 7 CSVs + 1,080 synthetic PNG assets.
- `Smadex_Creative_Intelligence_Dataset_FULL.zip` — archive form.

### `resources/taskInfo/`
- **`strategy.md`** — the live plan. Why Smadex, per-capability technical approach (Bayesian ranking / temporal fatigue / CLIP + attribute clustering / SHAP explainability / Thompson bandit recommendations), tech stack, 36-hour phased timeline, roles, demo script. **Single most important file in the repo.**
- `challenges.md` — all 10 HackUPC sponsor challenges + MLH side-prizes + general prizes (reference only; we're committed to Smadex).
- `hackUPCInfo.txt` — hacker guide (schedule, logistics, rules).

Non-Smadex sponsor material (ceremony transcript, JetBrains / Qualcomm / Skyscanner / Mecalux briefs) has been removed from the repo — it's recoverable from git history if needed.

### `resources/teamInfo/`
One file per teammate with LinkedIn URL + background summary. Keep in sync if responsibilities shift.

## Team

- **Andrew Robertson** (Manchester CS, final year) — **ad-tech domain lead + primary ML builder**. 4 months SWE at The Trade Desk (a top-tier DSP) gives him real intuition for creative metrics, cohort adjustment, frequency capping, A/B testing. Co-founder of Basanite (AI interviewer). Owns Q1 (Bayesian ranking), Q3 (SHAP explainability + Thompson-sampling bandit), and the DSP-accurate pitch vocabulary.
- **Aditya Shah** (Manchester CS, final year) — **data + demo**. CEO of Basanite. 13-month BigQuery/data-analytics placement at Virgin Media O2. 500+ hours of STEM tutoring → the team's demo driver. Owns dataset ingestion, temporal fatigue analysis (Q2a), and the 3-minute judging pitch.
- **Krish Mathur** (Southampton CS, first year) — **CV + pipeline + frontend velocity**. ICHack26 winner, MedTech hackathon winner. Strong Flask/Python/CV/Azure. Owns Q2b visual clustering (CLIP → HDBSCAN → UMAP) and infra glue.

## The plan in one paragraph

FastAPI + Next.js web app with three tabs mapped to the brief's five capabilities. **Q1 (Explorer)** = Bayesian-shrunk, cohort-adjusted ranking with 95% credible intervals, validated against the dataset's pre-computed `perf_score`. **Q2a (Fatigue)** = fit per-creative daily CTR decay with significance testing and changepoint detection; report a confusion matrix against the ground-truth `creative_status` label rather than consuming it. **Q2b (Similarity)** = HDBSCAN + UMAP over a blended feature vector of hand-labelled metadata attributes plus PCA-reduced CLIP ViT-B/32 image embeddings. **Q3a (Explainability)** = LightGBM + SHAP per-creative attribute contributions. **Q3b (Recommendation)** = attribute-cube bandit with Thompson sampling / UCB, peer benchmarking against same-vertical advertisers, Gemma-4-templated natural-language rationales. MongoDB Atlas + GoDaddy domain to stack MLH side-prizes. See `resources/taskInfo/strategy.md` for the full plan.

## Critical dataset facts (so you don't walk into traps)

- **1,080 creatives** / **180 campaigns** / **36 advertisers** / **192k daily rows** / **75-day date range** / **10 countries × 2 OS**. Fits easily in pandas in-memory.
- **Portfolio is perfectly uniform** — every advertiser has exactly 5 campaigns × 6 creatives. Any "who's biggest" analysis is a dead end.
- **Ground-truth labels exist** — `creative_status`, `fatigue_day`, `perf_score`. **Do not filter on these directly and call that your answer** — judges will penalise. Instead, compute your own signal and validate against them.
- **Pre-computed columns exist** (`first_7d_ctr`, `last_7d_ctr`, `ctr_decay_pct`) — treat as baselines to beat, not as outputs.
- **Images are synthetic** — rendered from metadata. CLIP embeddings will partly cluster on rendering style; caveat in the demo.
- **Creative metadata is rich** (theme, hook_type, dominant_color, emotional_tone, motion_score, has_discount_badge, etc.) — use for the attribute cube directly; no need to re-extract from pixels.
- **`countries` in `campaigns.csv` is pipe-separated** — explode before joining.
- **`fatigue_day` is blank for non-fatigued creatives** — don't render NaN.

## Hard constraints

- **Devpost submission deadline: Sun 26 Apr 09:15 local (UTC+2).** Miss = disqualified. Target submitting by 08:00 Sunday.
- **Hacking ends Sun 09:00.** No code changes after.
- **Demo is twice, 3 minutes each, no slides allowed.** Once for HackUPC judges in A3 (mandatory for HackUPC general prize + travel reimbursement), once for Smadex in A4. Same project, same demo.
- **Opt into MLH prizes** (MongoDB Atlas, Gemma 4, GoDaddy) via Devpost. Free upside.
- **Brief requires ≥ 2 of 5 capabilities.** We're shipping all 5.

## Tech stack (target)

- Backend: Python 3.12 + FastAPI. `pandas`, `numpy`, `scipy`, `scikit-learn`, `lightgbm`, `shap`, `hdbscan`, `umap-learn`, `open-clip-torch` (CPU), optionally `ruptures`.
- Frontend: Next.js + TypeScript + Tailwind. `recharts` + `deck.gl` / `plotly`.
- Persistence: MongoDB Atlas (embeddings + cached aggregations + session state). **Opt-in for MLH prize.**
- LLM: Gemma 4 via Google AI Studio for Q3 rationales. **Opt-in for MLH prize.**
- Domain: GoDaddy free domain. **Opt-in for MLH prize.**
- Deploy: Vercel (frontend) + Render / Fly.io (backend).
- **Streamlit fallback:** if Next.js slips on Sunday morning, the brief accepts "a notebook with a strong interactive demo" — keep a Streamlit scratch version running in parallel.
- **Not using:** ElevenLabs (gimmicky here), Solana, hardware, JetBrains Koog.

## Deliberate non-goals

- Don't train custom models (except fast LightGBM for SHAP). CLIP zero-shot + classical stats is the correct toolkit for 36 hours.
- Don't force voice / multi-agent / Koog / Edge AI to collect side-prizes — Smadex judges will dock for unfocused scope.
- Don't consume the ground-truth `creative_status` or `perf_score` directly as output — validate against them instead.
- Don't do a fourth tab or a dashboard-of-dashboards. Three tabs, five capabilities, one flow.
- Don't write per-advertiser "most active" analyses — the portfolio is uniform by design.

## Working conventions

- **`resources/taskInfo/strategy.md` is the living plan.** Update it when decisions change — don't just reply in chat.
- **`resources/smadex/dataset_notes.md` is the data reference.** Update it the moment you discover a new gotcha.
- **Keep teammate files in sync with reality.** If skills or responsibilities shift, update `resources/teamInfo/*.txt`.
- **Don't re-scrape LinkedIn or the live page** without reason. Distilled summaries exist.

## Key links

- Live page: https://live.hackupc.com
- Devpost: https://hackupc-2026.devpost.com
- Slack: hackupc2026.slack.com (`#announcements`, `#mentors`, `#smadex`)
- MyHackUPC: https://my.hackupc.com
- Venue: Edifici A5, Campus Nord UPC. A3 = HackUPC judging + sleeping; A4 = sponsor judging; A5/A6 = hacking floors + cafeteria.
