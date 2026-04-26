## Inspiration

Performance marketers spend their day buried in country-by-OS breakouts on ten different dashboards. They pause an ad in the global view, only to realise it was the only thing working in Mexico. They scale a winner everywhere, only to watch it tank in Brazil because Android users hate the music. The aggregate is a comfort blanket. The slice is the diagnosis.

Smadex Cooking is the kitchen. The dataset goes in raw, eight rules do the chopping, the AI plates it up as a daily action queue. You spend less time analysing and more time cooking. 🧑‍🍳

**Try it live:** [smadex.cooking](https://smadex.cooking)

## What it does

Smadex Cooking is a cockpit for anyone running mobile ads. It does three things, all on the same dataset of 1,080 creatives across 36 advertisers and 75 days.

* **Health KPI per creative.** A composite 0 to 100 score that fuses ROAS, CTR, CVR, spend efficiency, fatigue verdict, and cohort-relative rank. Not one number that hides the diagnosis, but six dimensions surfaced side by side.
* **Daily action queue at /actions.** A ranked list of 1,800 country-by-OS recommendations, written in plain English. Each card has the change ("pause in Brazil on Android"), the reason ("CTR dropped 78% week over week, ROAS at 0.4x cohort median"), the projected daily impact in dollars, and one tap to apply, snooze, or dismiss.
* **AI assistant.** Ask "why is creative 500376 underperforming?" and Gemini calls our typed tools to pull the slice metrics, identify the country where CTR collapsed, surface peer benchmarks, and offer a one-click pause for that geo only. No hallucinated numbers; every digit comes from the datastore.

The eight rules behind the queue are: geographic prune, geographic scale, OS frequency cap, cross-market early warning, concentration risk, format-market mismatch, pattern transfer, and reallocation. They all run over the per-(creative, country, OS) slice of every ad, which is where the actual money lives.

## How we built it

* **Backend.** Python 3.12 + FastAPI, dataset loaded once into memory at startup. A logistic regression classifier trained on hand-engineered changepoint features (drop ratio, peak-to-last drawdown, CTR coefficient of variation, pre and post-changepoint CTR deltas) decides the fatigue verdict. The eight action rules run over a precomputed (creative, country, OS) feature matrix with cohort baselines.
* **Frontend.** Next.js 16 with the App Router, deployed to Vercel at smadex.cooking. The layout is dense, neutral, and calm, modelled on real ad-tech tools like AppLovin MAX, Liftoff, and Moloco so anyone in the industry feels at home.
* **AI.** Google's Gemini 2.5 Flash for the chat assistant, with typed tool calls so every metric read goes through a Python function instead of a hallucinated guess. Gemma 3 27B rewrites our deterministic recommendation copy in marketer voice. We added a key-rotation pool with exponential-backoff retry so free-tier 429s don't crash the demo.
* **Deploy.** Frontend on Vercel, backend on Render, domain on Porkbun.

## Challenges we ran into

1. **The real signal was in the country and OS breakdown, and we found it late.** Our first pass built recommendations at the creative level. Mid-build we realised the per-country, per-OS slice was where the genuinely actionable insight was hiding. The same creative could be a winner on iOS in the US and a dud on Android in Brazil. We had to shift the recommendation grain on the fly, and it was the difference between generic advice and something a marketer would actually act on.

2. **Figuring out what "KPI" actually means in advertising.** We started by treating fatigue as the headline metric, then briefly chased an LLM-generated synthetic score. Both were wrong. Performance is a basket of ROAS, CTR, CVR, spend efficiency, fatigue, and cohort-relative behaviour, and collapsing it into a single number throws away the diagnosis. We reworked the cockpit to surface those dimensions side by side instead of fusing them.

3. **Splitting the dashboard cleanly across three of us.** Carving the cockpit into ownable pieces and stitching them back together was harder than the code itself. Types drifted, naming diverged, the same concept appeared in three places. The lesson: front-load the task split, agree shared types and conventions before anyone writes a component, and treat integration as a first-class deliverable rather than a leftover.

## Accomplishments that we're proud of

* The advisor analyses every (creative × country × OS) slice across all 1,080 creatives in the dataset and produces 1,800 ranked actions across all 36 advertisers. 86% of creatives surface at least one recommendation; the remaining 14% are clean and the system stays quiet.
* The fatigue classifier hits **0.93 ROC-AUC** on a held-out, campaign-grouped test split. The dataset's own pre-computed `ctr_decay_pct` baseline scores 0.87 on the same evaluation. So the model beats the dataset's shipped signal by 6 points of AUC, with proper grouped cross-validation (no campaign appears in both train and test).
* The chat assistant uses typed tool calls instead of prompt-stuffing. Every number it cites is the real number from the datastore, not something the model decided sounded plausible. It handles diagnose, recommend, confirm, and apply turns end to end.
* The interface looks and reads like a real ad-tech tool. Dense tables, Lucide icons only, a 6/8/10 px radius scale, accent colour reserved for the active state and the primary action. Marketers who've used MAX or Moloco recognise the layout instantly.

## Submission Challenge

We are entering this for the **Smadex Creative Intelligence for Mobile Advertising** challenge. The brief asked for a tool that answers, for a marketer, (1) which creatives work best, (2) which are repetitive or tired, (3) what to test next, with explainability and recommendations. Smadex Cooking covers four of those bullets directly:

* **Which work best:** Health KPI composite + cohort-relative rank, surfaced in the cockpit and on every creative card.
* **Which are tired:** Fatigue classifier with a benchmark beat (0.93 vs 0.87 ROC-AUC).
* **What to test next:** The 8-rule action queue at /actions, ranked by projected daily impact in dollars.
* **Recommendations with rationale:** Each card explains *why*, in marketer voice, polished by Gemma.

We also opted into the **MLH Gemma side-prize** (Gemma 3 27B handles every natural-language polish step on recommendations and assistant replies; the deterministic templates are the floor it can't drop below). The same project goes to **HackUPC general judging at A3** and **Smadex sponsor judging at A4** with one demo.

## What we learned

* **Slices beat totals.** A portfolio-average ROAS hides everything that matters. The same creative can be a 5x winner in the US and a 0.4x dud in Brazil at the same time. The aggregate is a comfort blanket; the slice is the diagnosis.
* **Tools beat guessing.** When we let the LLM read numbers off a prompt, it hallucinated confidently. When we forced it through typed tools that hit the real datastore, every digit was right. We didn't make the model smarter; we stopped asking it to memorise things it had no business knowing.
* **Compute the numbers, let the AI pick the words.** Deterministic Python decides the recommendation and the dollar impact. The LLM only writes the rationale around it. Numbers stay exact, copy stays warm, and nothing the marketer reads is something a language model decided was true.

## What's next for Smadex Cooking

* **Persist applied actions** so a marketer can see "you applied 8 of 12 recommendations this week" and the system can score itself over time.
* **Real causal lift estimates** with proper geo experiments instead of projections, so the dollar impact line on each card stops being a hedged estimate.
* **Plug the queue into Smadex's bid management API** so one tap of "apply" hits a live campaign instead of an in-memory state. That is the bullet that turns Smadex Cooking from a tool *next to* Smadex into a feature *inside* Smadex.
* **Bandit-driven exploration** of the attribute cube (theme, hook, dominant colour, motion score, has-discount-badge) once enough applied-action history exists to update priors. Same idea, different stove.

## A note on the dataset

The dataset's images are synthetically rendered from metadata, not real creative. We treat the visual layer as a placeholder. Production would consume real ad assets through Smadex's existing creative store. Everything else (CTR, CVR, ROAS, spend, conversions, fatigue labels, country mix, OS split) is real-shaped data, and that is what every model and rule in the cockpit operates on.
