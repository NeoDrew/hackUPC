# Smadex Cooking — 3-minute demo script

**Live demo. No slides. 3 minutes total. 60 seconds per speaker** — Aditya, Drew, Krish.
**URL: https://smadex.cooking**
Persona: **Maya**, creative-strategy lead at the food-delivery advertiser **CraveLoop**.

> **Tone for all three: SELL. The kitchen metaphor (Smadex Cooking) and the line *"the aggregate is a comfort blanket; the slice is the diagnosis"* are the through-line. Technical depth is for Q&A — not for the demo. Q&A prep is at the bottom of this file.**

---

## Pre-flight (5 min before going on)

Open these tabs, in this order, on `smadex.cooking`:

1. `https://smadex.cooking/` — cockpit (CraveLoop campaigns view)
2. `https://smadex.cooking/actions` — Advisor inbox (the money shot)
3. `https://smadex.cooking/creatives/<HERO_ID>?from=advisor` — hero creative detail
4. `https://smadex.cooking/creatives/<HERO_ID>/twin` — twin
5. `https://smadex.cooking/creatives/<HERO_ID>/variant` — variant

**Pick `<HERO_ID>` 30s before going on.** Top **Refresh** card on `/actions`. At time of writing the top is **#500133** (US, CTR −78%, 88% concentrated).

Verify before going on:
- `/actions` shows ~"50 actions ready · \$11.0k/day at stake"
- Auto-scale banner: *"3 winners auto-scaled this week — +\$3.2k reallocated"*
- Hero says **"Hi Maya, here's your portfolio at CraveLoop"**

---

## ADITYA · 60s · The thesis + the queue

> **0:00 – 0:18 · The hook**

**SAY:** *"Performance marketers spend their day buried in country-by-OS breakouts on ten different dashboards. They pause an ad in the global view — only to realise it was the only thing working in Mexico. They scale a winner everywhere — only to watch it tank in Brazil because Android users hate the music."*

**SAY (the thesis, slow):** *"**The aggregate is a comfort blanket. The slice is the diagnosis.** That's what we built."*

**DO:** click into Tab 1 (`/`).

> **0:18 – 0:30 · Cockpit**

**SAY:** *"This is Maya, running creative for CraveLoop. Five campaigns. Smadex Cooking has already done some of the work — **three winners auto-scaled this week**, no decision needed."*

**DO:** point at auto-scale banner. Click **Action** in nav. Land on Tab 2.

> **0:30 – 0:50 · The money shot**

**SAY:** *"But this is what Maya's morning actually looks like. **Fifty actions ready for her. Eighteen hundred across the network. Eleven thousand dollars a day at stake — just here.**"*

**DO:** point at queue header. **Hold 2 seconds.**

**SAY (the punchline):** *"Each card is one decision in plain English. **'Pause in Brazil on Android. CTR dropped seventy-eight percent. ROAS at zero-point-four cohort median.'** Apply, snooze, dismiss. **The brief asked for clear actions over black-box complexity — this is what that looks like.**"*

**DO:** click `Apply` on the top Refresh card.

> **0:50 – 1:00 · Hand-off**

**SAY:** *"One click. Done. But should she trust us? Drew."*

---

## DREW · 60s · The proof

> **1:00 – 1:15 · The drill-in**

**DO:** open Tab 3 (the hero creative detail).

**SAY:** *"This is the creative behind that recommendation. Daily clicks fell **seventy-eight percent in two weeks.**"*

**DO:** point at the dashed `IF UNCHANGED` line.

**SAY:** *"That dashed line is what happens if she does nothing. **Two more weeks of revenue burning.**"*

**[BEAT — 1.5s of silence.]**

> **1:15 – 1:35 · The twin**

**DO:** click `Improve →` → Tab 4.

**SAY:** *"So Smadex finds the closest winner in her portfolio. Same audience, same format, same vertical — just doing better."*

**DO:** scroll to the diff table.

**SAY (read the diff):** *"The winner says **'Get offer'**. Hers says **'Claim reward'**. Tone is **urgent**, not **excited**. **And our AI explains why** — not by guessing. Every number it cites comes through a typed tool call into our real data. **It cannot fabricate a number.**"*

**DO:** highlight the Vision Insight card.

> **1:35 – 1:55 · The fix**

**DO:** click `Generate variant` → Tab 5.

**SAY:** *"One click. Smadex generates a new creative inheriting what's working. **Plus eighteen percent projected ROAS.** Apply…"*

**DO:** click `Apply this variant →`. Wait for green toast.

**SAY:** *"…queued. **Two clicks. Problem to fix.** Krish — what's special."*

---

## KRISH · 60s · Three lessons + the kitchen

> **2:00 – 2:35 · Three lessons**

**SAY (intro · 3s):** *"Three things we learned building this."*

**SAY (one · 11s):** *"**Slices beat totals.** A portfolio-average ROAS hides everything that matters. The same creative can be a five-x winner in the US and a zero-point-four-x dud in Brazil at the same time. So every action runs at the slice — creative by country by OS."*

**SAY (two · 11s):** *"**Tools beat guessing.** When we let the LLM read numbers off a prompt, it hallucinated. When we forced it through typed Python tools, every digit was right. **We didn't make the model smarter — we stopped asking it to memorise things it had no business knowing.**"*

**SAY (three · 10s):** *"**Compute the numbers, let the AI pick the words.** Python decides the recommendation and the dollar impact. Gemma writes the rationale. **Numbers stay exact. Copy stays warm. Nothing the marketer reads is something a language model decided was true.**"*

> **2:35 – 2:50 · The bridge**

**SAY:** *"The brief asked us to **bridge the Creative Director and the Data Scientist**. The twin page is that bridge — Director sees the visual diff, analyst sees the numbers behind it."*

> **2:50 – 3:00 · Close**

**SAY:** *"Smadex Cooking. The dataset goes in raw, our rules chop, our AI plates it up. **Less analysing. More cooking.** Thank you."*

---

## Directorial notes

- **Money beats** — hold 1.5–2 seconds in silence:
  - The thesis line ("the aggregate is a comfort blanket; the slice is the diagnosis")
  - The auto-scale banner ("3 winners auto-scaled, +\$3.2k")
  - `/actions` queue header (the **\$11k/day** stat)
  - The `IF UNCHANGED` dashed line
  - Krish's *"compute the numbers, let the AI pick the words"* line
- **Pace** — Aditya's hook is 18s; he needs to **slow down** for the comfort-blanket / diagnosis line. That's the line judges will quote.
- **Pre-pick the hero creative.** Refresh cards have the cleanest drill-down. Shift / Rotate / Pause cards skip the twin step.
- **Time-checks.** Aditya at `/actions` by 0:30; Drew at variant page by 1:55; Krish on the close at 2:50.
- **Backup.** If the assistant breaks, skip the Vision Insight beat. If smadex.cooking stalls, fall back to localhost:3000.

## Selling stats — don't drift

| Beat | Stat |
|---|---|
| Aditya · cockpit | **3 winners auto-scaled** |
| Aditya · queue | **50 for Maya · 1,800 across the network · \$11k/day** |
| Aditya · coverage | **86% of creatives have at least one recommendation** *(use only if running long; cut otherwise)* |
| Drew · fatigue | **CTR −78% in two weeks** |
| Drew · variant | **+18% projected ROAS · two clicks problem to fix** |
| Krish · principles | (no numbers — selling principles, not stats) |

## Brief-quote moments (verbatim from the PDF)

| Brief language | Where it lands |
|---|---|
| *"Clear actions over black-box complexity"* | Aditya's punchline at 0:48 |
| *"Bridge the Creative Director and the Data Scientist"* | Krish's bridge at 2:35 |

## Three lines to put on a wall

> *"The aggregate is a comfort blanket. The slice is the diagnosis."* — Aditya
> *"It cannot fabricate a number."* — Drew
> *"Compute the numbers, let the AI pick the words."* — Krish

If only one line sticks with each judge, those three are the candidates.

---

# Q&A prep — technical answers (NOT for the demo)

If a judge asks any of these in Q&A, here's the speaker and the line.

## ML / model questions → Krish

**Q: How does the fatigue model actually work?**
> *"Logistic regression on seven engineered time-series features — drop ratio, CTR variance, peak-to-last drawdown, pre/post-changepoint rate, log-impressions floor, days-active floor. Trained with a campaign-grouped train/test split so sister-creatives don't leak across the boundary. **ROC-AUC 0.93 on held-out campaigns. The dataset's pre-computed `ctr_decay_pct` baseline scores 0.87 on the same evaluation. Six points of AUC, with proper grouped cross-validation.**"*

**Q: Why logistic regression and not deep learning?**
> *"199 positive examples. Tree ensembles tied within 0.005 AUC on cross-validation. Logistic gives us calibrated probabilities and a transparent decision surface — better defended on n=1080."*

**Q: How is the health score computed?**
> *"Six dimensions surfaced side by side — ROAS, CTR, CVR, spend efficiency, fatigue verdict, cohort-relative rank. Composite zero-to-one-hundred but the dimensions stay visible. We deliberately don't fuse them into one number that hides the diagnosis."*

**Q: How is the predicted +18% ROAS computed?**
> *"An estimate from cohort attribute deltas — we look at how the winning attributes have historically lifted ROAS in the same (vertical, format) cohort. Honest framing: it's an observational projection, not an A/B-tested forecast. Real causal lift estimation is in the future-work bucket."*

## Recommendation engine questions → Aditya / Krish

**Q: Are the recommendations rules or ML?**
> *"Eight deterministic rules over the (creative × country × OS) slice — geographic prune, geographic scale, OS frequency cap, cross-market early warning, concentration risk, format-market mismatch, pattern transfer, reallocation. Deterministic for the action layer because dollar estimates are easier to defend than a black-box. The model layer underneath — fatigue classification, twin matching — is real ML."*

**Q: How are the dollar estimates computed?**
> *"Each rule projects from the trailing 14-day spend-response curve. The card text already calls these *observational projections, not experimental results.* In production we'd plug into Smadex's bid management API and run real geo experiments instead."*

## LLM / explainability questions → Drew

**Q: How does Vision Insight work?**
> *"Gemini 2.5 Flash for the chat assistant, Gemma 3 27B for natural-language polish on recommendations. We give Gemma the structured attribute diff between the fatigued creative and its twin, plus performance gaps. Every response is post-processed to strip database column names and refuse fabricated numbers."*

**Q: Are you doing real computer vision on the images?**
> *"The dataset's images are synthetically rendered from metadata. A pixel-level pipeline would re-extract attributes the generator already gave us. We treat the visual layer as a placeholder — production would consume real ad assets through Smadex's existing creative store."*

**Q: How does the chat assistant avoid hallucinating numbers?**
> *"Typed tool calls. Every metric the LLM cites goes through a Python function that hits the datastore. The model can't decide a number sounds plausible — it has to call a tool and get the real value. We added a key-rotation pool with exponential-backoff retry so free-tier 429s don't crash the demo."*

## Similarity questions → Drew / Krish

**Q: How does twin matching work?**
> *"For each fatigued creative, we find the highest-similarity top performer in the same (vertical, format) cohort. Cosine similarity on a 94-dimensional engineered feature vector — one-hot categorical attributes plus normalized numeric scores."*

## Architecture questions → Drew

**Q: How does this scale to thousands of advertisers?**
> *"In-memory pandas. The full Smadex dataset — 1,080 creatives, 36 advertisers, 192,000 daily fact rows — fits comfortably. Aggregations run sub-second. For real production at hundreds of advertisers and tens of millions of rows, we'd swap to ClickHouse or DuckDB; the application layer stays the same."*

**Q: Where does the data live?**
> *"FastAPI backend, Python 3.12, dataset loaded once into memory at startup. Frontend is Next.js 16 on Vercel. Backend on Render. Domain on Porkbun."*

## Generalization questions

**Q: How does this generalize to real ad-exchange data?**
> *"The dataset is synthetic — absolute numbers will move. The relative ordering of feature groups (engineered time-series > pre-computed decay metrics > cohort rank > static creative attributes) is what we expect to hold."*

## Team / process questions

**Q: How did you split the work?**
> *"Three separate ownership areas. The hardest part wasn't the code — it was carving the cockpit into ownable pieces and stitching them back together. Types drift, naming diverges. The lesson: front-load the split, agree shared conventions before anyone writes a component, treat integration as a first-class deliverable."*

**Q: What surprised you?**
> *"The real signal was in the country-by-OS slice, and we found it late. Our first pass built recommendations at the creative level. Mid-build we realised the per-country, per-OS slice was where the actionable insight was hiding. Same creative, winner on iOS in the US, dud on Android in Brazil. We had to shift the recommendation grain on the fly."*
