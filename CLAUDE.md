# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

This is **not** a software project — it is the workspace for a HackUPC 2026 hackathon team (Barcelona, April 24–26, 2026). The repo currently only contains research material under `resources/`:

- `resources/teamInfo/` — one file per teammate with their LinkedIn URL and a written summary of their background, skills, and hackathon track record.
- `resources/taskInfo/` — primary source material for the hackathon:
  - `hackUPCInfo.txt` — hacker guide (schedule, logistics, rules).
  - `HackUPC_2026_Opening_Ceremony_eng.txt` — full timestamped transcript of the opening ceremony (all sponsor pitches).
  - `HackUPCSkyscanner.pptx`, `JetBrains - Help the Developer HackUPC.pdf`, `Qualcomm - Slack Announcement.docx.pdf` — sponsor-specific briefs.
  - `challenges.md` — distilled, canonical list of all 10 sponsor challenges + MLH side-prizes + HackUPC general prizes. Prefer this over re-parsing the raw transcript.
  - `strategy.md` — the team's pick-a-challenge analysis and current recommendation (JetBrains "Help the Developer", stacking MLH prizes).

When the hackathon itself starts, the actual project code will live alongside `resources/` — likely in a new top-level directory. The live hacking window is **Fri 24 Apr 21:00 → Sun 26 Apr 09:00 local (UTC+2)**. The mandatory Devpost submission deadline is **Sun 26 Apr 09:15** — miss it and the team is disqualified.

## Team

Three-person team, full details in `resources/teamInfo/`:

- **Andrew Robertson** (Manchester CS, final year) — ex-Trade Desk SWE intern, Basanite founder (co-founded with Aditya), AI engineer at Outlier + DataAnnotation, ICHack26 winner.
- **Aditya Shah** (Manchester CS, final year) — CEO of Basanite (AI interviewer for technical roles), ex-Virgin Media O2 data analyst (BigQuery), 500+ hours of STEM tutoring — the team's communicator/demoer.
- **Krish Mathur** (Southampton CS, first year) — stealth-startup founder, ICHack26 co-winner with Andrew, MedTech hackathon winner, strong on Flask/Python/CV/Azure AI.

## How the team plays to win

`resources/taskInfo/strategy.md` is the current plan. Summary: target **JetBrains "Help the Developer"** as the primary challenge and opt in to every MLH side-prize (ElevenLabs, Gemma 4, MongoDB Atlas, GoDaddy domain, Solana) so the same project can win multiple tracks. The team already won Best ElevenLabs + runner-up JetBrains at ICHack26 with a multi-agent voice system (Guardian) using ElevenLabs + JetBrains Koog + RAG — this plan replays and refines that stack.

Do not suggest hardware-heavy challenges (Qualcomm Edge AI on Arduino UNO Q) — the team has zero embedded experience and the 36-hour window is too short to learn both hardware and ship a demoable product. Same for Tether Peers (niche P2P stack) and HP's industrial 3D-printer digital twin (no team experience in physics modelling).

Smadex "Creative Intelligence" is a genuine secondary option — Andrew's 4-month Trade Desk SWE internship gives the team real ad-tech domain knowledge (DSP / creative auctioning / performance metrics), and Aditya's BigQuery background fits the data-app shape. If the team pivots, this is the hedge.

## Working conventions for this repo

- **Treat `challenges.md` and `strategy.md` as the living source of truth.** If new info surfaces (e.g., JetBrains prizes revealed Saturday), update those files — don't just reply in chat.
- **Keep each teammate's background file in sync with reality.** If you learn something new about a teammate's skills, update their file under `resources/teamInfo/`.
- **Don't re-scrape LinkedIn, the live page, or the ceremony transcript unless explicitly asked.** The distilled summaries already capture what matters; re-scraping burns tool calls and context.
- **The ceremony transcript is very long** (~5900 lines, mostly noise + sponsor pitches). When extracting from it, prefer grepping for sponsor/company names over reading sequentially.
- **MCP tools available:** `chromeflow` (browser automation — use for live.hackupc.com, LinkedIn, Devpost, Arduino Project Hub). Prefer `get_page_text` over screenshots.

## Key links (from the hacker guide)

- Live page (timetable, activities, sponsor lineup): https://live.hackupc.com
- Devpost (submissions): https://hackupc-2026.devpost.com
- Slack (primary comms): hackupc2026.slack.com — `#announcements`, `#mentors`, per-sponsor channels (e.g. `#jetbrains`).
- MyHackUPC (hardware reservations): https://my.hackupc.com
- Venue: Edifici A5, Campus Nord UPC, Barcelona — buildings A3–A6. A3 is HackUPC judging + sleeping; A4 is sponsor judging; A5/A6 are hacking floors + cafeteria.

## Judging mechanics (easy to trip on)

- **You must demo twice** to be eligible for both HackUPC main prizes (+travel reimbursement) and any sponsor prize — once in A3 for HackUPC judges, once in A4 for each sponsor challenge you opted into.
- **No slides allowed.** Code demo only, 3 minutes max. PowerPoint will tank the score.
- **One project per team, but it can be submitted to multiple sponsor tracks.** Stack MLH side-prizes aggressively.
- **Qualcomm has a unique 3-step submission** (Devpost + public GitHub with MPL 2.0 license + Arduino Project Hub page named `[HackUPC2026] - <name>`). Irrelevant unless the team pivots to Edge AI.
