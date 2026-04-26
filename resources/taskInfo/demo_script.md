# Smadex Creative Twin Copilot — 3-minute demo script

**Live demo, no slides. 3 minutes total. 60 seconds per speaker** — Aditya, Drew, Krish.
**URL: https://smadex.cooking**
Persona: **Maya**, creative-strategy lead at the food-delivery advertiser **CraveLoop**.

> **Tone for all three speakers: SELL the product, don't explain the model.** Technical depth is for Q&A. Every sentence should make the judges *want* to use what we built. The full Q&A prep is at the bottom of this file.

## Pre-flight (5 min before going on)

Open these tabs **on smadex.cooking**, in this order:

1. `https://smadex.cooking/` — cockpit (CraveLoop campaigns view)
2. `https://smadex.cooking/actions` — Advisor inbox (the money shot)
3. `https://smadex.cooking/creatives/<HERO_ID>?from=advisor` — hero creative detail
4. `https://smadex.cooking/creatives/<HERO_ID>/twin` — twin
5. `https://smadex.cooking/creatives/<HERO_ID>/variant` — variant

**Pick `<HERO_ID>` 30s before going on**: top **Refresh** card on `/actions`. At time of writing the top Refresh is **#500133** (US, CTR −78%, 88% concentrated).

Verify before going on:
- `/actions` shows ~"50 actions ready · \$11.0k/day at stake"
- `/` hero says **"Hi Maya, here's your portfolio at CraveLoop"**
- Auto-scale banner reads roughly *"Smadex auto-scaled 3 winners this week — +\$3.2k reallocated"*
- Bottom-right *Open assistant* visible

---

## ADITYA · 60s · The pitch

> 0:00 – 0:10 · **Hook**

**SAY:** *"Maya runs creative for CraveLoop. Thirty live ads, eight hundred thousand dollars of weekly spend, and one question every Monday: **what do I do today?** Her dashboard shows her a hundred numbers. **Smadex shows her one inbox.**"*

**DO:** click into Tab 1 (`/`).

> 0:10 – 0:22 · **Cockpit landing**

**SAY:** *"This is her portfolio. Five campaigns, ranked by health. Green is healthy, yellow needs watching, red is bleeding. **And Smadex has already done some of the work** — three winning ads got more budget this week without her even asking."*

**DO:** point at auto-scale banner. Click **Action** in nav. Land on Tab 2.

> 0:22 – 0:50 · **The Advisor — money shot**

**SAY:** *"This is what Maya's morning actually looks like. **Fifty actions ready. Eleven thousand dollars a day at stake.** Each one is a single decision, with a dollar value."*

**DO:** point at queue header. **Hold 2 seconds.**

**SAY (read ONE card aloud):** *"Top of the queue: '**Shift one hundred and fifteen dollars a day** out of a slice losing money — into one earning two-and-a-half times its spend.' One click. Done."*

**SAY (the punchline):** *"Every action here has a cited dollar value. Not 'medium urgency'. Not a five-star rating. **Dollars.** **The brief asked for clear actions over black-box complexity. This is what that looks like.**"*

**DO:** click `Apply` on the top Refresh card.

> 0:50 – 1:00 · **Hand-off**

**SAY:** *"Maya can act in one click. But she shouldn't have to trust us on faith — every recommendation is one click from the proof. Drew."*

---

## DREW · 60s · The proof

> 1:00 – 1:15 · **The drill-in**

**DO:** open Tab 3 (the hero creative detail).

**SAY:** *"This is the creative behind that recommendation. Daily clicks fell seventy-eight percent in two weeks."*

**DO:** point at the dashed `IF UNCHANGED` line on the fatigue chart.

**SAY:** *"That dashed line is what happens if she does nothing. **Two more weeks of revenue burning.**"*

**[BEAT — 1.5s of silence.]**

> 1:15 – 1:35 · **The twin**

**DO:** click `Improve →` → Tab 4.

**SAY:** *"So Smadex finds the closest winner in her portfolio. **Same audience, same format, same vertical** — just doing better."*

**DO:** scroll to diff table.

**SAY (read the diff):** *"The winner says **'Get offer'** — hers says **'Claim reward'**. The winner's tone is **urgent** — hers is **excited**. **And our AI explains why** — in plain English, grounded in real performance data. **It cannot make up numbers.**"*

**DO:** highlight the Vision Insight card.

> 1:35 – 1:55 · **The fix**

**DO:** click `Generate variant` → Tab 5.

**SAY:** *"One click. Smadex generates a new creative inheriting what's working. Predicted plus eighteen percent ROAS. She applies it…"*

**DO:** click `Apply this variant →`. Wait for green toast.

**SAY:** *"…and it's queued. **Two clicks. Problem to fix.** Krish — what makes this different from anything else."*

---

## KRISH · 60s · What's special

> 2:00 – 2:35 · **Three product principles**

**SAY (intro · 5s):** *"Three things we did differently."*

**SAY (one · 10s):** *"**One: every score is fair.** Banner ads compete against banners. A small fintech campaign can be a top performer next to a giant gaming one — because we never compare across categories."*

**SAY (two · 10s):** *"**Two: we don't ask Maya about decisions she shouldn't have to think about.** Top performers get more budget silently — those three winners Aditya pointed at were already done before she opened the app."*

**SAY (three · 10s):** *"**Three: every recommendation has a price tag.** Eleven thousand a day isn't a confidence score — it's the actual money on the table if she acts. **Marketers act on dollars, not stars.**"*

> 2:35 – 2:50 · **The bridge**

**SAY:** *"The brief asked us to **bridge the Creative Director and the Data Scientist**. The twin page is that bridge — the Director sees the visual diff, the analyst sees the numbers behind it. **One product. One decision flow.**"*

> 2:50 – 3:00 · **Close**

**SAY:** *"We didn't build a dashboard. **We built Maya's Monday morning.** Thank you."*

---

## Directorial notes

- **Money beats** — hold for 1.5–2 seconds:
  - The auto-scale banner ("3 winners auto-scaled, \$3.2k")
  - `/actions` queue header (the **\$11.0k/day** stat)
  - The `IF UNCHANGED` dashed line on the fatigue chart
  - Krish's *"every recommendation has a price tag"* line
- **Don't read every metric.** One number per beat.
- **Pre-pick the hero creative.** Refresh cards have the cleanest drill-down. Shift / Rotate / Pause cards skip the twin step.
- **Time-checks.** Aditya at `/actions` by 0:22; Drew at variant page by 1:55; Krish on the close at 2:50.
- **Backup.** If the assistant breaks, skip the Vision Insight beat — it's not load-bearing. If smadex.cooking stalls, fall back to localhost:3000.

## Numbers to memorize (selling stats — don't drift)

| Beat | Stat |
|---|---|
| Aditya · banner | **3 winners auto-scaled** |
| Aditya · Advisor | **\$11,000 a day** · **50 actions** |
| Drew · fatigue | **CTR −78% in two weeks** |
| Drew · variant | **+18% ROAS predicted** · **two clicks problem to fix** |
| Krish · principles | (no numbers — selling principles, not stats) |

## Brief-quote moments

The brief uses these phrases verbatim — quote them back at the judges:

| Brief language | Where in the script |
|---|---|
| *"Clear actions over black-box complexity"* | Aditya's Advisor punchline |
| *"Bridge the Creative Director and the Data Scientist"* | Krish's bridge moment |
| *"Build the next Creative Copilot for mobile advertisers"* | Implicit — our product literally is this |

---

# Q&A prep — the technical answers (ONLY for Q&A, NOT the demo)

If a judge asks any of these in Q&A, here's what each speaker says.

## ML / model questions → Krish

**Q: How does the fatigue model actually work?**
> *"Logistic regression on seven engineered time-series features — drop ratio, CTR variance, peak-to-last drawdown, pre/post-changepoint rate, log-impressions floor, days-active floor. Trained with a campaign-grouped train/test split so sister-creatives don't leak across the boundary. **ROC-AUC 0.93 on held-out campaigns**, beats the dataset's `ctr_decay_pct` baseline by 0.06."*

**Q: Why logistic regression and not deep learning?**
> *"199 positive examples. Tree ensembles tied within 0.005 AUC on cross-validation. Logistic gives us calibrated probabilities and a transparent decision surface — better defended on n=1080."*

**Q: How is the health score computed?**
> *"Six components — posterior strength, confidence, trend, cohort rank, efficiency, reliability. Always cohort-relative by vertical and format. Weights are tunable."*

**Q: How does the predicted +18% ROAS get computed?**
> *"It's an estimate from cohort attribute deltas — we look at how the winning attributes have historically lifted ROAS in the same (vertical, format) cohort. Honest framing: it's an observational projection, not an A/B-tested forecast."*

## Recommendation engine questions → Aditya / Krish

**Q: Are the recommendations rules or ML?**
> *"Eight deterministic rules over the (creative, country, OS) slice grain — Pause, Rotate, Scale, Shift, Refresh, Cap, Re-bid. We chose deterministic for the action layer because dollar estimates are easier to defend than a black-box. The model layer underneath — fatigue classification, twin matching — is ML."*

**Q: How are the dollar estimates computed?**
> *"Each rule projects from the trailing 14-day spend-response curve. For Shift cards: marginal ROAS of the source slice vs the target slice, multiplied by the proposed reallocation. The card text already calls these *observational projections, not experimental results.*"*

## LLM / explainability questions → Drew

**Q: How does Vision Insight work?**
> *"Gemma 4 via Google AI Studio. We pass it the structured attribute diff between the fatigued creative and its twin, plus performance gaps. We post-process every response to strip database column names and refuse fabricated numbers — it's grounded in the diff, not making things up."*

**Q: Are you doing real computer vision on the images?**
> *"The dataset's images are rendered from metadata. A pixel-level pipeline would re-extract attributes the generator already gave us. We use those attributes directly — 94 dimensions, L2-normalised, cosine for similarity. On a real ad-exchange dataset where pixels carry information the metadata doesn't, we'd add CLIP embeddings."*

## Similarity / clustering questions → Drew / Krish

**Q: How does twin matching work?**
> *"For each fatigued creative, we find the highest-similarity top performer in the same (vertical, format) cohort. Cosine similarity on a 94-dimensional engineered feature vector — one-hot categorical attributes plus normalized numeric scores."*

**Q: Why didn't you use HDBSCAN/UMAP for clustering?**
> *"For our 1-NN twin lookup, a linear scan was tied with hierarchical clustering on retrieval quality. We kept the simpler signal we could defend."*

## Architecture / scale questions → Drew

**Q: How does this scale to thousands of advertisers?**
> *"In-memory pandas. The full Smadex dataset — 1080 creatives across 36 advertisers, 192,000 daily fact rows — fits comfortably. Aggregations run sub-second. For real production at hundreds of advertisers and tens of millions of rows, we'd swap to a columnar store like ClickHouse or DuckDB; the application layer is the same."*

**Q: Where does the data live?**
> *"FastAPI backend reads CSVs into memory at startup, joins them once, exposes typed endpoints. Frontend is Next.js. Deployed at smadex.cooking on Render and Vercel."*

## Generalization questions

**Q: How does this generalize to real ad-exchange data?**
> *"Honest answer: the dataset is synthetic, so absolute numbers will move. The relative ordering of feature groups — engineered time-series > pre-computed decay metrics > cohort rank > static creative attributes — is what we expect to hold. That's documented in our research notebook."*

---

## Single sentence to remember

> *"We didn't build a dashboard. We built Maya's Monday morning."*

If anything goes wrong, end on this line.
